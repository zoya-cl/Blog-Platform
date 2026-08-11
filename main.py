"""
FastAPI REST Server for BlogGraph-AI.
Exposes endpoints for viewing, generating, editing, approving, and managing blogs.
"""

import os
import json
import glob
import uuid
import asyncio
from typing import List, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import config
from topic_selection import mongo_db, queue_manager
from agents.formatter import sanitize_title

app = FastAPI(
    title="BlogGraph-AI Engine API",
    description="REST API for automated technical blog generation, audit, editing, and approval workflow.",
    version="1.0.0"
)

# Enable CORS for frontend integration (React, Next.js, Vite, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------
# Request & Response Schemas
# -------------------------------------------------------------

class BlogUpdateRequest(BaseModel):
    title: Optional[str] = None
    markdown_content: Optional[str] = None
    meta_description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    focus_keyword: Optional[str] = None

class ApprovalRequest(BaseModel):
    approved: str = Field(..., description="'yes' or 'no'")

class GenerationRequest(BaseModel):
    category: Optional[str] = Field(None, description="Optional target category")
    topic: Optional[str] = Field(None, description="Optional specific title or topic")

# -------------------------------------------------------------
# Helpers
# -------------------------------------------------------------

def get_output_dir() -> str:
    _project_root = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(_project_root, "output")
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def find_files_by_slug(slug: str):
    out_dir = get_output_dir()
    md_path = os.path.join(out_dir, f"{slug}.md")
    json_path = os.path.join(out_dir, f"{slug}.json")
    
    if os.path.exists(md_path) and os.path.exists(json_path):
        return md_path, json_path
        
    # Search for matching json by slug key if filename doesn't match directly
    for jf in glob.glob(os.path.join(out_dir, "*.json")):
        if jf.endswith("-trace.json") or "module_" in jf:
            continue
        try:
            with open(jf, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("slug") == slug:
                    md_f = jf.replace(".json", ".md")
                    return md_f, jf
        except Exception:
            pass
            
    return None, None

def run_pipeline_task(category: str = None, topic: str = None):
    """Background task runner for blog generation."""
    try:
        from run import run_pipeline_for_topic
        import random
        selected_category = category or random.choice(config.CATEGORIES)
        selected_title = topic or f"Modern {selected_category} Best Practices in 2026"
        print(f"[API Background Task] Generating blog for: '{selected_title}' [{selected_category}]...")
        run_pipeline_for_topic(selected_category, selected_title)
        print("[API Background Task] Pipeline generation completed successfully.")
    except Exception as e:
        print(f"[API Background Task Error] Pipeline execution failed: {e}")

# -------------------------------------------------------------
# API Endpoints
# -------------------------------------------------------------

@app.on_event("startup")
def startup_db_init():
    """Initialize MongoDB indexes and seed categories on startup."""
    try:
        queue_manager.init_db()
    except Exception as e:
        print(f"[Warning] Startup DB initialization issue: {e}")

@app.get("/")
def root():
    return {
        "status": "online",
        "service": "BlogGraph-AI Engine API",
        "version": "1.0.0",
        "docs_url": "/docs"
    }

@app.get("/api/blogs")
def list_blogs(
    category: Optional[str] = Query(None, description="Filter by category"),
    status: Optional[str] = Query(None, description="Filter by status: 'published', 'in_progress', 'pending'"),
    approved: Optional[str] = Query(None, description="Filter by approval status: 'yes' or 'no'"),
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0)
):
    """
    List all blog topics from MongoDB and local storage.
    """
    try:
        db = mongo_db.get_db()
        collection = db[mongo_db.MONGODB_COLLECTION_TOPICS]
        
        query = {}
        if category:
            query["category"] = category
        if status:
            query["status"] = status
        if approved:
            query["approved"] = approved
            
        docs = list(collection.find(query, {"_id": 0}).skip(skip).limit(limit))
        total_count = collection.count_documents(query)
        
        return {
            "total": total_count,
            "skip": skip,
            "limit": limit,
            "blogs": docs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query error: {e}")

@app.get("/api/blogs/{slug}")
def get_blog(slug: str):
    """
    Fetch a single blog's full markdown content and metadata.
    """
    md_path, json_path = find_files_by_slug(slug)
    
    # Try fetching from MongoDB first
    db_doc = None
    try:
        db = mongo_db.get_db()
        collection = db[mongo_db.MONGODB_COLLECTION_TOPICS]
        db_doc = collection.find_one({"$or": [{"slug": slug}, {"output_filename": f"{slug}.md"}]}, {"_id": 0})
    except Exception:
        pass
        
    markdown_content = ""
    metadata = {}
    
    if md_path and os.path.exists(md_path):
        with open(md_path, "r", encoding="utf-8") as f:
            markdown_content = f.read()
            
    if json_path and os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
            
    if not markdown_content and db_doc:
        markdown_content = db_doc.get("markdown_content", "")
        if db_doc.get("metadata_json"):
            try:
                metadata = json.loads(db_doc["metadata_json"])
            except Exception:
                pass
                
    if not markdown_content and not db_doc:
        raise HTTPException(status_code=404, detail=f"Blog with slug '{slug}' not found.")
        
    return {
        "slug": slug,
        "title": metadata.get("title", db_doc.get("title") if db_doc else slug),
        "category": metadata.get("category", db_doc.get("category") if db_doc else ""),
        "approved": metadata.get("approved", db_doc.get("approved", "no") if db_doc else "no"),
        "status": db_doc.get("status", "published") if db_doc else "published",
        "quality_score": metadata.get("quality_score", db_doc.get("quality_score", 0.0) if db_doc else 0.0),
        "word_count": metadata.get("word_count", db_doc.get("word_count", 0) if db_doc else 0),
        "metadata": metadata,
        "markdown_content": markdown_content
    }

@app.put("/api/blogs/{slug}")
def edit_blog(slug: str, body: BlogUpdateRequest):
    """
    EDIT API: Updates blog title, markdown content, category, tags, or focus keyword.
    Persists changes to both local filesystem (.md / .json) and MongoDB.
    """
    md_path, json_path = find_files_by_slug(slug)
    
    metadata = {}
    if json_path and os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
            
    # Apply edits to metadata
    if body.title:
        metadata["title"] = body.title
    if body.category:
        metadata["category"] = body.category
    if body.meta_description:
        metadata["meta_description"] = body.meta_description
    if body.tags is not None:
        metadata["tags"] = body.tags
    if body.focus_keyword:
        metadata["focus_keyword"] = body.focus_keyword
        
    markdown_content = body.markdown_content
    if markdown_content is None and md_path and os.path.exists(md_path):
        with open(md_path, "r", encoding="utf-8") as f:
            markdown_content = f.read()
            
    if markdown_content is None:
        raise HTTPException(status_code=400, detail="Must provide markdown_content to update.")
        
    word_count = len(markdown_content.split())
    metadata["word_count"] = word_count
    
    # Save updated files to disk if path exists or create them
    out_dir = get_output_dir()
    new_md_path = md_path or os.path.join(out_dir, f"{slug}.md")
    new_json_path = json_path or os.path.join(out_dir, f"{slug}.json")
    
    with open(new_json_path, "w", encoding="utf-8") as jf:
        json.dump(metadata, jf, indent=2)
        
    with open(new_md_path, "w", encoding="utf-8") as mf:
        mf.write(markdown_content)
        
    # Sync update to MongoDB
    try:
        db = mongo_db.get_db()
        collection = db[mongo_db.MONGODB_COLLECTION_TOPICS]
        
        collection.update_one(
            {"$or": [{"slug": slug}, {"output_filename": f"{slug}.md"}]},
            {"$set": {
                "title": metadata.get("title", slug),
                "category": metadata.get("category", ""),
                "word_count": word_count,
                "markdown_content": markdown_content,
                "metadata_json": json.dumps(metadata),
                "updated_at": datetime.now().isoformat()
            }}
        )
    except Exception as e:
        print(f"[Warning] Failed to update MongoDB on edit: {e}")
        
    return {
        "status": "success",
        "message": f"Blog '{slug}' updated successfully.",
        "word_count": word_count,
        "metadata": metadata
    }

@app.put("/api/blogs/{slug}/approve")
def approve_blog(slug: str, body: ApprovalRequest):
    """
    APPROVAL API: Approves or rejects a generated blog ('yes' or 'no').
    """
    if body.approved not in ["yes", "no"]:
        raise HTTPException(status_code=400, detail="Approval state must be 'yes' or 'no'.")
        
    md_path, json_path = find_files_by_slug(slug)
    
    if json_path and os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        meta["approved"] = body.approved
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
            
    try:
        db = mongo_db.get_db()
        collection = db[mongo_db.MONGODB_COLLECTION_TOPICS]
        collection.update_one(
            {"$or": [{"slug": slug}, {"output_filename": f"{slug}.md"}]},
            {"$set": {"approved": body.approved}}
        )
    except Exception as e:
        print(f"[Warning] MongoDB approval update error: {e}")
        
    return {
        "status": "success",
        "slug": slug,
        "approved": body.approved
    }

@app.post("/api/blogs/generate")
def generate_blog(body: GenerationRequest, background_tasks: BackgroundTasks):
    """
    GENERATE API: Triggers the blog generation pipeline asynchronously.
    """
    task_id = str(uuid.uuid4())[:8]
    background_tasks.add_task(run_pipeline_task, body.category, body.topic)
    
    return {
        "status": "initiated",
        "job_id": task_id,
        "category": body.category or "random",
        "topic": body.topic or "auto-generated",
        "message": "Blog generation started in the background."
    }

@app.delete("/api/blogs/{slug}")
def delete_blog(slug: str):
    """
    DELETE API: Deletes a blog from MongoDB and local storage.
    """
    md_path, json_path = find_files_by_slug(slug)
    
    deleted_files = []
    if md_path and os.path.exists(md_path):
        os.remove(md_path)
        deleted_files.append(md_path)
    if json_path and os.path.exists(json_path):
        os.remove(json_path)
        deleted_files.append(json_path)
        
    try:
        db = mongo_db.get_db()
        collection = db[mongo_db.MONGODB_COLLECTION_TOPICS]
        res = collection.delete_one({"$or": [{"slug": slug}, {"output_filename": f"{slug}.md"}]})
        db_deleted = res.deleted_count > 0
    except Exception:
        db_deleted = False
        
    return {
        "status": "success",
        "slug": slug,
        "deleted_files": deleted_files,
        "db_deleted": db_deleted
    }
