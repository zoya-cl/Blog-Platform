import os
import sqlite3
import json
import uuid
import uvicorn
from datetime import datetime
from threading import Thread, enumerate as thread_enumerate
from typing import Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException, Body
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
from topic_selection import queue_manager, title_generator, dedup_checker
from run import run_pipeline_for_topic

app = FastAPI(title="BlogGraph-AI Admin Portal", version="2.0.0")

# Ensure output directory exists
os.makedirs("output", exist_ok=True)

# Mount output folder to serve markdown files and images
app.mount("/output", StaticFiles(directory="output"), name="output")

# Ensure database is initialized with updated schema
queue_manager.init_db()


class GenerateRequest(BaseModel):
    category: Optional[str] = None
    title: Optional[str] = None


class ApproveRequest(BaseModel):
    approved: str


class EditRequest(BaseModel):
    title: str
    markdown_content: str
    metadata_json: str


def get_db_connection():
    conn = sqlite3.connect("topics.db", timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def bg_run_pipeline(category: str, title: str):
    """Background task to execute the full BlogGraph-AI pipeline."""
    try:
        print(f"[FastAPI Background Task] Starting run for: '{title}' in '{category}'")
        run_pipeline_for_topic(category=category, title=title)
        print(f"[FastAPI Background Task] Generation complete for: '{title}'")
    except Exception as e:
        print(f"[FastAPI Background Task] Pipeline execution failed: {e}")
        # Transition back to pending or log status so dashboard can stop spinning
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE topics SET status = 'pending', title = NULL WHERE title = ? AND status = 'in_progress'",
                (title,)
            )
            conn.commit()
            conn.close()
        except Exception as db_err:
            print(f"Error resetting database after failed task: {db_err}")


@app.get("/health")
def health():
    """Simple health check endpoint."""
    db_ok = False
    try:
        conn = get_db_connection()
        conn.execute("SELECT 1")
        conn.close()
        db_ok = True
    except Exception:
        pass
        
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database_connected": db_ok,
        "active_generation_tasks": len([t for t in thread_enumerate() if t.name and t.name.startswith("blog-gen-")]),
    }


@app.get("/blogs")
def get_blogs():
    """Retrieve all blogs inside the topics table."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM topics WHERE title IS NOT NULL ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/blogs/{blog_id}")
def get_blog(blog_id: int):
    """Retrieve a single blog by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM topics WHERE id = ?", (blog_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Blog not found")
    return dict(row)


@app.post("/blogs/{blog_id}/approve")
def approve_blog(blog_id: int, payload: ApproveRequest):
    """Set or toggle the approval status of a blog."""
    approved_val = payload.approved.lower()
    if approved_val not in ["yes", "no"]:
        raise HTTPException(status_code=400, detail="Approved must be 'yes' or 'no'")
        
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT metadata_json, output_filename FROM topics WHERE id = ?", (blog_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Blog not found")
        
    meta_str, output_filename = row
    
    # 1. Update database fields
    cursor.execute("UPDATE topics SET approved = ? WHERE id = ?", (approved_val, blog_id))
    conn.commit()
    
    # 2. Sync metadata JSON value in DB and physical sidecar file
    if meta_str:
        try:
            meta = json.loads(meta_str)
            meta["approved"] = approved_val
            new_meta_str = json.dumps(meta, indent=2)
            cursor.execute("UPDATE topics SET metadata_json = ? WHERE id = ?", (new_meta_str, blog_id))
            conn.commit()
            
            if output_filename:
                base_name = os.path.splitext(output_filename)[0]
                json_path = os.path.join("output", f"{base_name}.json")
                if os.path.exists(json_path):
                    with open(json_path, "w", encoding="utf-8") as jf:
                        jf.write(new_meta_str)
        except Exception as e:
            print(f"Error syncing approval in metadata JSON: {e}")
            
    conn.close()
    return {"status": "success", "id": blog_id, "approved": approved_val}


@app.put("/blogs/{blog_id}")
def edit_blog(blog_id: int, payload: EditRequest):
    """Edit title, markdown content, and metadata JSON for a blog."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT output_filename FROM topics WHERE id = ?", (blog_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Blog not found")
        
    output_filename = row[0]
    word_count = len(payload.markdown_content.split())
    
    # Update DB
    cursor.execute(
        """
        UPDATE topics
        SET title = ?, markdown_content = ?, metadata_json = ?, word_count = ?
        WHERE id = ?
        """,
        (payload.title, payload.markdown_content, payload.metadata_json, word_count, blog_id)
    )
    conn.commit()
    conn.close()
    
    # Sync with physical files on disk
    if output_filename:
        base_name = os.path.splitext(output_filename)[0]
        md_path = os.path.join("output", f"{base_name}.md")
        json_path = os.path.join("output", f"{base_name}.json")
        
        try:
            # Write updated markdown
            with open(md_path, "w", encoding="utf-8") as mf:
                mf.write(payload.markdown_content)
                
            # Write updated JSON
            meta = json.loads(payload.metadata_json)
            with open(json_path, "w", encoding="utf-8") as jf:
                json.dump(meta, jf, indent=2)
        except Exception as e:
            print(f"Error saving updated files to disk: {e}")
            
    return {"status": "success", "message": "Blog updated successfully"}


@app.post("/generate")
def generate_blog(payload: GenerateRequest, background_tasks: BackgroundTasks):
    """Trigger the BlogGraph-AI pipeline in a background task."""
    # Check if there is already an active run in progress
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title FROM topics WHERE status = 'in_progress'")
    active_row = cursor.fetchone()
    conn.close()
    
    if active_row:
        raise HTTPException(
            status_code=400,
            detail=f"Another generation task is currently running: '{active_row['title']}'"
        )
        
    category = payload.category
    title = payload.title
    
    # 1. Resolve category
    patterns = []
    if not category:
        # Auto-select category (seasonal weighted + aging)
        category, patterns = queue_manager.get_next_category()
    else:
        if category not in config.CATEGORIES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category '{category}'. Must be one of: {', '.join(config.CATEGORIES)}"
            )
        patterns = queue_manager.EXAMPLE_TITLE_PATTERNS.get(category, [])
        
    # 2. Resolve title
    if not title:
        # Auto-generate a unique title for the category using LLM with deduplication
        current_year = datetime.now().year
        processed_patterns = [p.replace("{year}", str(current_year)) for p in patterns]
        existing_titles = queue_manager.get_recent_titles(category, months=3)
        
        retry_cap = config.RETRY_CAPS.get("title_dedup", 3)
        approved_title = None
        rejected_titles = []
        
        for attempt in range(1, retry_cap + 1):
            try:
                candidate_title = title_generator.generate_blog_title(category, processed_patterns, existing_titles, rejected_titles)
                if dedup_checker.is_title_unique(candidate_title, existing_titles, category):
                    approved_title = candidate_title
                    break
                else:
                    rejected_titles.append(candidate_title)
            except Exception as e:
                print(f"Error during title generation attempt {attempt}: {e}")
                
        if not approved_title:
            # Fallback title if all attempts fail or error occurs
            approved_title = f"Latest Trends and Insights in {category} {current_year}"
            
        title = approved_title
        
    # Start thread
    t = Thread(target=bg_run_pipeline, args=(category, title), name=f"blog-gen-{uuid.uuid4().hex[:6]}")
    t.daemon = True
    t.start()
    
    return {
        "status": "started",
        "category": category,
        "title": title,
        "message": f"Generation started in the background. Topic: '{title}'"
    }


@app.get("/dashboard", response_class=HTMLResponse)
def get_dashboard():
    """Render the dark glassmorphic HTML Admin Dashboard SPA."""
    categories_json = json.dumps(config.CATEGORIES)
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BlogGraph-AI Admin Portal</title>
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <!-- FontAwesome Icons -->
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <!-- Marked.js Markdown Parser -->
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        :root {{
            --bg-color: #0f172a;
            --panel-bg: rgba(30, 41, 59, 0.45);
            --panel-border: rgba(255, 255, 255, 0.08);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --primary: #6366f1;
            --primary-glow: rgba(99, 102, 241, 0.3);
            --secondary: #a855f7;
            --accent: #06b6d4;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --font-display: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
            --font-body: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            background: radial-gradient(circle at top right, rgba(168, 85, 247, 0.15), transparent 40%),
                        radial-gradient(circle at bottom left, rgba(99, 102, 241, 0.15), transparent 45%),
                        var(--bg-color);
            background-color: var(--bg-color);
            color: var(--text-main);
            font-family: var(--font-body);
            min-height: 100vh;
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}

        .container {{
            width: 100%;
            max-width: 1400px;
            margin: 0 auto;
        }}

        /* Header Layout */
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 30px;
            background: var(--panel-bg);
            border: 1px solid var(--panel-border);
            backdrop-filter: blur(16px);
            border-radius: 16px;
            margin-bottom: 24px;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
        }}

        .logo-section {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .logo-section i {{
            font-size: 2rem;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .logo-section h1 {{
            font-family: var(--font-display);
            font-weight: 800;
            font-size: 1.5rem;
            letter-spacing: -0.5px;
            background: linear-gradient(to right, #ffffff, #cbd5e1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .logo-section span {{
            font-size: 0.75rem;
            font-weight: 600;
            color: var(--accent);
            text-transform: uppercase;
            letter-spacing: 2px;
            border: 1px solid rgba(6, 182, 212, 0.3);
            padding: 2px 8px;
            border-radius: 9999px;
            background: rgba(6, 182, 212, 0.05);
        }}

        .server-status {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.85rem;
            color: var(--text-muted);
            padding: 6px 14px;
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--panel-border);
        }}

        .status-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: var(--success);
            box-shadow: 0 0 10px var(--success);
            animation: pulse 2s infinite;
        }}

        /* Metrics Summary cards */
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 20px;
            margin-bottom: 24px;
        }}

        .metric-card {{
            background: var(--panel-bg);
            border: 1px solid var(--panel-border);
            backdrop-filter: blur(12px);
            border-radius: 16px;
            padding: 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 4px 20px 0 rgba(0, 0, 0, 0.15);
            position: relative;
            overflow: hidden;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }}

        .metric-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 4px;
            background: linear-gradient(90deg, var(--primary), var(--secondary));
            opacity: 0.6;
        }}

        .metric-card:hover {{
            transform: translateY(-4px);
            border-color: rgba(99, 102, 241, 0.25);
            box-shadow: 0 8px 30px var(--primary-glow);
        }}

        .metric-info h3 {{
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-muted);
            margin-bottom: 8px;
        }}

        .metric-info p {{
            font-family: var(--font-display);
            font-size: 2.25rem;
            font-weight: 700;
            color: #ffffff;
            line-height: 1;
        }}

        .metric-icon {{
            width: 50px;
            height: 50px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--panel-border);
            color: var(--primary);
        }}

        .metric-card:nth-child(2) .metric-icon {{ color: var(--success); }}
        .metric-card:nth-child(3) .metric-icon {{ color: var(--warning); }}
        .metric-card:nth-child(4) .metric-icon {{ color: var(--accent); }}

        /* Main Workspace layout */
        .workspace {{
            display: grid;
            grid-template-columns: 320px 1fr;
            gap: 24px;
            margin-bottom: 40px;
        }}

        /* Left Side Generation Panel */
        .control-panel {{
            background: var(--panel-bg);
            border: 1px solid var(--panel-border);
            backdrop-filter: blur(12px);
            border-radius: 16px;
            padding: 24px;
            height: fit-content;
            box-shadow: 0 4px 20px 0 rgba(0, 0, 0, 0.15);
        }}

        .panel-title {{
            font-family: var(--font-display);
            font-size: 1.15rem;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .panel-title i {{
            color: var(--primary);
        }}

        .form-group {{
            margin-bottom: 20px;
        }}

        .form-group label {{
            display: block;
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-bottom: 8px;
            font-weight: 500;
        }}

        .form-control {{
            width: 100%;
            padding: 12px 16px;
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid var(--panel-border);
            border-radius: 10px;
            color: #ffffff;
            font-family: var(--font-body);
            font-size: 0.9rem;
            transition: all 0.2s ease;
        }}

        .form-control:focus {{
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15);
        }}

        select.form-control {{
            appearance: none;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394a3b8'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'/%3E%3C/svg%3E");
            background-repeat: no-repeat;
            background-position: right 16px center;
            background-size: 16px;
            padding-right: 40px;
        }}

        .btn {{
            width: 100%;
            padding: 14px 20px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border: none;
            border-radius: 10px;
            color: #ffffff;
            font-family: var(--font-display);
            font-weight: 600;
            font-size: 0.95rem;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.35);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }}

        .btn:hover {{
            box-shadow: 0 6px 20px rgba(99, 102, 241, 0.5);
            transform: translateY(-1px);
        }}

        .btn:active {{
            transform: translateY(1px);
        }}

        .btn:disabled {{
            background: rgba(255, 255, 255, 0.05);
            color: var(--text-muted);
            border: 1px solid var(--panel-border);
            cursor: not-allowed;
            box-shadow: none;
        }}

        /* Right Side Data Panel */
        .data-panel {{
            background: var(--panel-bg);
            border: 1px solid var(--panel-border);
            backdrop-filter: blur(12px);
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 4px 20px 0 rgba(0, 0, 0, 0.15);
            display: flex;
            flex-direction: column;
            min-height: 500px;
        }}

        /* Table Design */
        .table-wrapper {{
            width: 100%;
            overflow-x: auto;
            margin-top: 10px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }}

        th {{
            padding: 16px;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-muted);
            font-weight: 600;
            border-bottom: 1px solid var(--panel-border);
        }}

        td {{
            padding: 18px 16px;
            font-size: 0.9rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.03);
            vertical-align: middle;
        }}

        tr:hover td {{
            background: rgba(255, 255, 255, 0.015);
        }}

        .blog-title-cell {{
            font-weight: 500;
            color: #ffffff;
            max-width: 320px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        /* Glowing Badges */
        .badge {{
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}

        .badge-pending {{
            background: rgba(245, 158, 11, 0.1);
            color: var(--warning);
            border: 1px solid rgba(245, 158, 11, 0.2);
        }}

        .badge-progress {{
            background: rgba(99, 102, 241, 0.1);
            color: var(--primary);
            border: 1px solid rgba(99, 102, 241, 0.25);
            animation: pulse-border 1.5s infinite;
        }}

        .badge-published {{
            background: rgba(16, 185, 129, 0.1);
            color: var(--success);
            border: 1px solid rgba(16, 185, 129, 0.2);
        }}

        .badge-yes {{
            background: rgba(16, 185, 129, 0.15);
            color: var(--success);
            border: 1px solid rgba(16, 185, 129, 0.3);
            cursor: pointer;
        }}

        .badge-no {{
            background: rgba(239, 68, 68, 0.15);
            color: var(--danger);
            border: 1px solid rgba(239, 68, 68, 0.3);
            cursor: pointer;
        }}

        .action-group {{
            display: flex;
            gap: 8px;
        }}

        .btn-icon {{
            width: 34px;
            height: 34px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            border: 1px solid var(--panel-border);
            background: rgba(255, 255, 255, 0.03);
            color: var(--text-main);
            cursor: pointer;
            transition: all 0.2s ease;
        }}

        .btn-icon:hover {{
            background: var(--primary);
            border-color: var(--primary);
            color: #ffffff;
            box-shadow: 0 0 8px var(--primary-glow);
        }}

        .btn-icon.btn-danger-hover:hover {{
            background: var(--danger);
            border-color: var(--danger);
        }}

        /* Full Overlay Modals */
        .modal-overlay {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(15, 23, 42, 0.85);
            backdrop-filter: blur(8px);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 100;
            padding: 40px;
        }}

        .modal-container {{
            width: 100%;
            max-width: 1100px;
            max-height: 90vh;
            background: #1e293b;
            border: 1px solid var(--panel-border);
            border-radius: 20px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            animation: zoom-in 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
        }}

        .modal-header {{
            padding: 24px;
            border-bottom: 1px solid var(--panel-border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: rgba(15, 23, 42, 0.2);
        }}

        .modal-header h2 {{
            font-family: var(--font-display);
            font-weight: 700;
            font-size: 1.25rem;
            color: #ffffff;
        }}

        .modal-close {{
            background: none;
            border: none;
            color: var(--text-muted);
            font-size: 1.25rem;
            cursor: pointer;
            transition: color 0.2s ease;
        }}

        .modal-close:hover {{
            color: #ffffff;
        }}

        .modal-body {{
            padding: 24px;
            overflow-y: auto;
            flex: 1;
            display: grid;
            grid-template-columns: 1fr;
            gap: 20px;
        }}

        /* Specific View Layout (split pane) */
        .view-layout {{
            display: grid;
            grid-template-columns: 1fr 340px;
            gap: 24px;
            height: 100%;
            overflow: hidden;
        }}

        .markdown-pane {{
            background: rgba(15, 23, 42, 0.4);
            border: 1px solid var(--panel-border);
            border-radius: 12px;
            padding: 30px;
            overflow-y: auto;
            color: #cbd5e1;
            line-height: 1.8;
            font-size: 0.95rem;
        }}

        .markdown-pane h1, .markdown-pane h2, .markdown-pane h3 {{
            font-family: var(--font-display);
            color: #ffffff;
            margin-top: 30px;
            margin-bottom: 16px;
        }}

        .markdown-pane h1 {{ font-size: 1.75rem; border-bottom: 1px solid var(--panel-border); padding-bottom: 10px; }}
        .markdown-pane h2 {{ font-size: 1.4rem; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 6px; }}
        .markdown-pane h3 {{ font-size: 1.15rem; }}

        .markdown-pane p {{
            margin-bottom: 20px;
        }}

        .markdown-pane code {{
            font-family: Consolas, monospace;
            background: rgba(255, 255, 255, 0.08);
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.85em;
            color: var(--accent);
        }}

        .markdown-pane pre {{
            background: #0f172a;
            padding: 20px;
            border-radius: 8px;
            overflow-x: auto;
            margin-bottom: 20px;
            border: 1px solid var(--panel-border);
        }}

        .markdown-pane pre code {{
            background: none;
            padding: 0;
            color: #e2e8f0;
        }}

        .markdown-pane img {{
            max-width: 100%;
            border-radius: 10px;
            margin: 20px auto;
            display: block;
            border: 2px dashed rgba(255, 255, 255, 0.1);
            box-shadow: 0 8px 30px rgba(0,0,0,0.3);
        }}

        .side-meta-pane {{
            background: rgba(15, 23, 42, 0.2);
            border: 1px solid var(--panel-border);
            border-radius: 12px;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 15px;
            overflow-y: auto;
        }}

        .meta-title {{
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-muted);
            margin-bottom: 4px;
        }}

        .meta-val {{
            font-size: 0.9rem;
            color: #ffffff;
            font-weight: 500;
        }}

        /* Edit Layout */
        .edit-layout {{
            display: flex;
            flex-direction: column;
            gap: 20px;
        }}

        .edit-layout textarea.form-control {{
            resize: vertical;
            min-height: 400px;
            font-family: Consolas, monospace;
            font-size: 0.85rem;
            line-height: 1.5;
            background: #0f172a;
        }}

        .modal-footer {{
            padding: 20px 24px;
            border-top: 1px solid var(--panel-border);
            display: flex;
            justify-content: flex-end;
            gap: 12px;
            background: rgba(15, 23, 42, 0.2);
        }}

        /* Spinner / Loading Overlays */
        .loading-wrapper {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 40px;
            color: var(--text-muted);
            gap: 16px;
        }}

        .spinner {{
            width: 40px;
            height: 40px;
            border: 4px solid rgba(255, 255, 255, 0.05);
            border-top-color: var(--primary);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }}

        /* Animations */
        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}

        @keyframes pulse {{
            0%, 100% {{ opacity: 0.6; box-shadow: 0 0 6px var(--success); }}
            50% {{ opacity: 1; box-shadow: 0 0 16px var(--success); }}
        }}

        @keyframes pulse-border {{
            0%, 100% {{ border-color: rgba(99, 102, 241, 0.25); }}
            50% {{ border-color: rgba(99, 102, 241, 0.8); }}
        }}

        @keyframes zoom-in {{
            from {{ transform: scale(0.95); opacity: 0; }}
            to {{ transform: scale(1); opacity: 1; }}
        }}

        /* Responsive layout */
        @media (max-width: 1024px) {{
            .workspace {{
                grid-template-columns: 1fr;
            }}
            .view-layout {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header>
            <div class="logo-section">
                <i class="fa-solid fa-circle-nodes"></i>
                <h1>BlogGraph-AI</h1>
                <span>Admin</span>
            </div>
            <div class="server-status">
                <div class="status-dot"></div>
                <span>Server Online</span>
            </div>
        </header>

        <!-- Summary Metrics -->
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-info">
                    <h3>Total Blogs</h3>
                    <p id="metric-total">0</p>
                </div>
                <div class="metric-icon">
                    <i class="fa-solid fa-file-invoice"></i>
                </div>
            </div>
            <div class="metric-card">
                <div class="metric-info">
                    <h3>Approved</h3>
                    <p id="metric-approved">0</p>
                </div>
                <div class="metric-icon">
                    <i class="fa-solid fa-circle-check"></i>
                </div>
            </div>
            <div class="metric-card">
                <div class="metric-info">
                    <h3>Pending Review</h3>
                    <p id="metric-pending">0</p>
                </div>
                <div class="metric-icon">
                    <i class="fa-solid fa-clock-rotate-left"></i>
                </div>
            </div>
            <div class="metric-card">
                <div class="metric-info">
                    <h3>Active Tasks</h3>
                    <p id="metric-tasks">0</p>
                </div>
                <div class="metric-icon">
                    <i class="fa-solid fa-spinner"></i>
                </div>
            </div>
        </div>

        <!-- Main Workspace -->
        <div class="workspace">
            <!-- Left Side controls -->
            <div class="control-panel">
                <div class="panel-title">
                    <i class="fa-solid fa-wand-magic-sparkles"></i>
                    <h2>Generate Blog</h2>
                </div>
                <form id="gen-form">
                    <div class="form-group">
                        <label for="gen-category">Select Category</label>
                        <select id="gen-category" class="form-control"></select>
                    </div>
                    <div class="form-group">
                        <label for="gen-title">Propose Customized Title (Optional)</label>
                        <input type="text" id="gen-title" class="form-control" placeholder="Leave empty for auto-generation...">
                    </div>
                    <button type="submit" id="gen-submit-btn" class="btn">
                        <i class="fa-solid fa-bolt"></i> Run Pipeline
                    </button>
                </form>
            </div>

            <!-- Right Side Blogs list -->
            <div class="data-panel">
                <div class="panel-title" style="margin-bottom: 10px;">
                    <i class="fa-solid fa-database"></i>
                    <h2>Blogs Queue & Database</h2>
                </div>
                
                <div class="table-wrapper">
                    <table>
                        <thead>
                            <tr>
                                <th>Blog Title / Category</th>
                                <th>Word Count</th>
                                <th>Quality Score</th>
                                <th>Status</th>
                                <th>Approved</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="blogs-table-body">
                            <!-- Populated dynamically -->
                            <tr>
                                <td colspan="6">
                                    <div class="loading-wrapper">
                                        <div class="spinner"></div>
                                        <span>Loading blogs from database...</span>
                                    </div>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <!-- View Modal -->
    <div id="view-modal" class="modal-overlay">
        <div class="modal-container">
            <div class="modal-header">
                <h2 id="view-modal-title">View Blog Details</h2>
                <button class="modal-close" onclick="closeModal('view-modal')"><i class="fa-solid fa-xmark"></i></button>
            </div>
            <div class="modal-body">
                <div class="view-layout">
                    <!-- Markdown Reader Pane -->
                    <div id="view-markdown-content" class="markdown-pane">
                        <!-- Rendered HTML Markdown goes here -->
                    </div>
                    <!-- Metadata Side Pane -->
                    <div class="side-meta-pane">
                        <div>
                            <div class="meta-title">Trace ID</div>
                            <div id="view-meta-trace" class="meta-val">-</div>
                        </div>
                        <div>
                            <div class="meta-title">Category</div>
                            <div id="view-meta-category" class="meta-val">-</div>
                        </div>
                        <div>
                            <div class="meta-title">Slug / Output Filename</div>
                            <div id="view-meta-filename" class="meta-val">-</div>
                        </div>
                        <div>
                            <div class="meta-title">Word Count</div>
                            <div id="view-meta-words" class="meta-val">-</div>
                        </div>
                        <div>
                            <div class="meta-title">Quality Score</div>
                            <div id="view-meta-score" class="meta-val">-</div>
                        </div>
                        <div>
                            <div class="meta-title">Created At</div>
                            <div id="view-meta-created" class="meta-val">-</div>
                        </div>
                        <div>
                            <div class="meta-title">Completed At</div>
                            <div id="view-meta-completed" class="meta-val">-</div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn" style="width: auto; background: var(--panel-border); color: #ffffff;" onclick="closeModal('view-modal')">Close</button>
            </div>
        </div>
    </div>

    <!-- Edit Modal -->
    <div id="edit-modal" class="modal-overlay">
        <div class="modal-container">
            <div class="modal-header">
                <h2>Edit Blog</h2>
                <button class="modal-close" onclick="closeModal('edit-modal')"><i class="fa-solid fa-xmark"></i></button>
            </div>
            <div class="modal-body">
                <div class="edit-layout">
                    <input type="hidden" id="edit-blog-id">
                    <div class="form-group">
                        <label for="edit-title">Blog Title</label>
                        <input type="text" id="edit-title" class="form-control" required>
                    </div>
                    <div class="form-group">
                        <label for="edit-content">Markdown Content</label>
                        <textarea id="edit-content" class="form-control" required></textarea>
                    </div>
                    <div class="form-group">
                        <label for="edit-metadata">Metadata JSON Sidecar</label>
                        <textarea id="edit-metadata" class="form-control" style="min-height: 120px; font-family: monospace; font-size: 0.8rem;" required></textarea>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn" style="width: auto; background: var(--panel-border); color: #ffffff; border: 1px solid var(--panel-border);" onclick="closeModal('edit-modal')">Cancel</button>
                <button class="btn" style="width: auto;" onclick="saveBlogEdit()">Save Changes</button>
            </div>
        </div>
    </div>

    <!-- Scripting -->
    <script>
        const categories = {categories_json};
        let blogsList = [];
        let isPolling = false;
        let pollTimer = null;

        // Initialize UI
        document.addEventListener('DOMContentLoaded', () => {{
            populateCategories();
            loadBlogs();
            
            // Handle generation submission
            document.getElementById('gen-form').addEventListener('submit', triggerGeneration);
        }});

        function populateCategories() {{
            const selectEl = document.getElementById('gen-category');
            selectEl.innerHTML = '<option value="">-- Auto-Select Category (Seasonal Weighted) --</option>' + 
                                 categories.map(cat => `<option value="${{cat}}">${{cat}}</option>`).join('');
        }}

        async function loadBlogs() {{
            try {{
                const res = await fetch('/blogs');
                blogsList = await res.json();
                renderBlogsTable();
                updateMetrics();
                
                // If any blog is in_progress, start polling status changes
                const hasActive = blogsList.some(b => b.status === 'in_progress');
                if (hasActive && !isPolling) {{
                    startPolling();
                }} else if (!hasActive && isPolling) {{
                    stopPolling();
                }}
            }} catch (err) {{
                console.error("Failed to load blogs:", err);
            }}
        }}

        function updateMetrics() {{
            const total = blogsList.length;
            const approved = blogsList.filter(b => b.approved === 'yes').length;
            const pending = blogsList.filter(b => b.status === 'published' && b.approved === 'no').length;
            const active = blogsList.filter(b => b.status === 'in_progress').length;
            
            document.getElementById('metric-total').innerText = total;
            document.getElementById('metric-approved').innerText = approved;
            document.getElementById('metric-pending').innerText = pending;
            document.getElementById('metric-tasks').innerText = active;
            
            // Disable button if generation task is active
            const submitBtn = document.getElementById('gen-submit-btn');
            if (active > 0) {{
                submitBtn.disabled = true;
                submitBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Generating...`;
            }} else {{
                submitBtn.disabled = false;
                submitBtn.innerHTML = `<i class="fa-solid fa-bolt"></i> Run Pipeline`;
            }}
        }}

        function renderBlogsTable() {{
            const tbody = document.getElementById('blogs-table-body');
            if (blogsList.length === 0) {{
                tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No blogs found. Seed the SQLite queue to begin!</td></tr>`;
                return;
            }}
            
            tbody.innerHTML = blogsList.map(blog => {{
                let statusClass = 'badge-pending';
                if (blog.status === 'in_progress') statusClass = 'badge-progress';
                if (blog.status === 'published') statusClass = 'badge-published';
                
                let approveClass = blog.approved === 'yes' ? 'badge-yes' : 'badge-no';
                let scoreText = blog.quality_score ? blog.quality_score.toFixed(1) : '-';
                
                // Replace null or empty categories
                let titleText = blog.title || `<span style="color: var(--text-muted); font-style: italic;">Auto-Selecting Title for Category...</span>`;
                
                return `
                    <tr>
                        <td>
                            <div class="blog-title-cell" title="${{blog.title || ''}}">${{titleText}}</div>
                            <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px;">${{blog.category}}</div>
                        </td>
                        <td>${{blog.word_count || 0}}</td>
                        <td><i class="fa-solid fa-star" style="color: var(--warning); margin-right: 4px; font-size: 0.8rem;"></i>${{scoreText}}</td>
                        <td><span class="badge ${{statusClass}}">${{blog.status === 'in_progress' ? '<i class="fa-solid fa-spinner fa-spin"></i>' : ''}} ${{blog.status}}</span></td>
                        <td>
                            <span class="badge ${{approveClass}}" onclick="toggleApproval(${{blog.id}}, '${{blog.approved}}')">
                                ${{blog.approved === 'yes' ? '<i class="fa-solid fa-check-double"></i> Yes' : '<i class="fa-solid fa-x"></i> No'}}
                            </span>
                        </td>
                        <td>
                            <div class="action-group">
                                <button class="btn-icon" title="View Blog" onclick="viewBlog(${{blog.id}})" ${{!blog.markdown_content ? 'disabled' : ''}}>
                                    <i class="fa-solid fa-eye"></i>
                                </button>
                                <button class="btn-icon" title="Edit Blog" onclick="editBlog(${{blog.id}})" ${{!blog.markdown_content ? 'disabled' : ''}}>
                                    <i class="fa-solid fa-pen-to-square"></i>
                                </button>
                            </div>
                        </td>
                    </tr>
                `;
            }}).join('');
        }}

        async function toggleApproval(id, currentVal) {{
            const newVal = currentVal === 'yes' ? 'no' : 'yes';
            try {{
                const res = await fetch(`/blogs/${{id}}/approve`, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ approved: newVal }})
                }});
                if (res.ok) {{
                    loadBlogs();
                }} else {{
                    const data = await res.json();
                    alert("Approval toggle failed: " + data.detail);
                }}
            }} catch (err) {{
                console.error("Error setting approval status:", err);
            }}
        }}

        async function triggerGeneration(e) {{
            e.preventDefault();
            const category = document.getElementById('gen-category').value;
            const title = document.getElementById('gen-title').value;
            
            try {{
                const res = await fetch('/generate', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ category, title }})
                }});
                
                const data = await res.json();
                if (res.ok) {{
                    alert(data.message);
                    document.getElementById('gen-title').value = '';
                    loadBlogs();
                }} else {{
                    alert("Error: " + data.detail);
                }}
            }} catch (err) {{
                console.error("Error triggering generation:", err);
            }}
        }}

        async function viewBlog(id) {{
            try {{
                const res = await fetch(`/blogs/${{id}}`);
                const blog = await res.json();
                
                document.getElementById('view-modal-title').innerText = blog.title || 'Blog Details';
                document.getElementById('view-meta-trace').innerText = blog.trace_id || '-';
                document.getElementById('view-meta-category').innerText = blog.category || '-';
                document.getElementById('view-meta-filename').innerText = blog.output_filename || '-';
                document.getElementById('view-meta-words').innerText = blog.word_count || '0';
                document.getElementById('view-meta-score').innerText = blog.quality_score ? blog.quality_score.toFixed(1) + '/10' : '-';
                document.getElementById('view-meta-created').innerText = blog.created_at || '-';
                document.getElementById('view-meta-completed').innerText = blog.completed_at || '-';
                
                // Set Markdown content rendering (translating relative image paths to static endpoints)
                let md = blog.markdown_content || '';
                
                // Rewrite relative image references from 'slug/images/img_N.png' to '/output/slug/images/img_N.png'
                md = md.replace(/!\\[(.*?)\\]\\((.*?)\\)/g, (match, alt, src) => {{
                    if (src.startsWith('http') || src.startsWith('/')) {{
                        return `![${{alt}}](${{src}})`;
                    }}
                    return `![${{alt}}](/output/${{src}})`;
                }});
                
                document.getElementById('view-markdown-content').innerHTML = marked.parse(md);
                openModal('view-modal');
            }} catch (err) {{
                console.error("Error viewing blog:", err);
            }}
        }}

        async function editBlog(id) {{
            try {{
                const res = await fetch(`/blogs/${{id}}`);
                const blog = await res.json();
                
                document.getElementById('edit-blog-id').value = blog.id;
                document.getElementById('edit-title').value = blog.title || '';
                document.getElementById('edit-content').value = blog.markdown_content || '';
                document.getElementById('edit-metadata').value = blog.metadata_json || '{{}}';
                
                openModal('edit-modal');
            }} catch (err) {{
                console.error("Error opening edit modal:", err);
            }}
        }}

        async function saveBlogEdit() {{
            const id = document.getElementById('edit-blog-id').value;
            const title = document.getElementById('edit-title').value;
            const markdown_content = document.getElementById('edit-content').value;
            const metadata_json = document.getElementById('edit-metadata').value;
            
            // Simple JSON validation check
            try {{
                JSON.parse(metadata_json);
            }} catch (e) {{
                alert("Invalid Metadata JSON format! Please fix and retry.");
                return;
            }}
            
            try {{
                const res = await fetch(`/blogs/${{id}}`, {{
                    method: 'PUT',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ title, markdown_content, metadata_json }})
                }});
                
                if (res.ok) {{
                    closeModal('edit-modal');
                    loadBlogs();
                }} else {{
                    const data = await res.json();
                    alert("Edit failed: " + data.detail);
                }}
            }} catch (err) {{
                console.error("Error saving blog edit:", err);
            }}
        }}

        function openModal(modalId) {{
            document.getElementById(modalId).style.display = 'flex';
        }}

        function closeModal(modalId) {{
            document.getElementById(modalId).style.display = 'none';
        }}

        function startPolling() {{
            isPolling = true;
            pollTimer = setInterval(loadBlogs, 3000); // Poll status every 3 seconds
        }}

        function stopPolling() {{
            isPolling = false;
            clearInterval(pollTimer);
        }}
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
