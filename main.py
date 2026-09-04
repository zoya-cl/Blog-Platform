from fastapi.staticfiles import StaticFiles
"""
FastAPI REST Server for BlogGraph-AI.
Exposes endpoints for viewing, generating, editing, approving, and managing blogs.
"""

import os
import re
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

# Static files mount for generated images
images_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "images")
os.makedirs(images_dir, exist_ok=True)
app.mount("/images", StaticFiles(directory=images_dir), name="images")


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

def slugify(text: str) -> str:
    if not text:
        return ""
    s = text.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[-\s]+", "-", s)
    return s

def get_output_dir() -> str:
    _project_root = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(_project_root, "output")
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def find_files_by_slug(slug: str):
    out_dir = get_output_dir()
    
    # 1. Direct match
    md_path = os.path.join(out_dir, f"{slug}.md")
    json_path = os.path.join(out_dir, f"{slug}.json")
    if os.path.exists(md_path) and os.path.exists(json_path):
        return md_path, json_path

    # 2. Direct match with '-post' suffix
    md_post_path = os.path.join(out_dir, f"{slug}-post.md")
    json_post_path = os.path.join(out_dir, f"{slug}-post.json")
    if os.path.exists(md_post_path) and os.path.exists(json_post_path):
        return md_post_path, json_post_path
        
    # 3. Search matching json by internal metadata properties
    for jf in glob.glob(os.path.join(out_dir, "*.json")):
        if jf.endswith("-trace.json") or "module_" in jf:
            continue
        try:
            with open(jf, "r", encoding="utf-8") as f:
                data = json.load(f)
                file_slug = data.get("slug")
                file_title = slugify(data.get("title", ""))
                file_topic = slugify(data.get("topic", ""))
                
                if file_slug == slug or file_title == slug or file_topic == slug:
                    md_f = jf.replace(".json", ".md")
                    return md_f, jf
        except Exception:
            pass
            
    return None, None


def sections_to_markdown(sections: list) -> str:
    """
    Reconstructs rich markdown content from Fulcrum structured sections,
    emitting COMPONENT: and IMAGE: blocks so BlogRenderer mounts full interactive React widgets.
    """
    if not sections:
        return ""
    md_parts = []
    for sec in sections:
        heading = sec.get("heading")
        if heading:
            md_parts.append(f"## {heading}\n")
        body = sec.get("body", [])
        for block in body:
            btype = block.get("type")
            if btype == "paragraph":
                text = block.get("text", "")
                if text:
                    md_parts.append(text + "\n")
            elif btype == "heading":
                level = "#" * block.get("level", 3)
                md_parts.append(f"{level} {block.get('text', '')}\n")
            elif btype == "quiz":
                props_json = json.dumps(block)
                md_parts.append(f"\n\nCOMPONENT:\nType: quiz\nProps: {props_json}\n\n")
            elif btype == "comparison_widget":
                props_json = json.dumps(block)
                md_parts.append(f"\n\nCOMPONENT:\nType: comparison_widget\nProps: {props_json}\n\n")
            elif btype in ["table", "data_table"]:
                props_json = json.dumps(block)
                md_parts.append(f"\n\nCOMPONENT:\nType: table\nProps: {props_json}\n\n")
            elif btype == "code_block":
                props_json = json.dumps(block)
                md_parts.append(f"\n\nCOMPONENT:\nType: code_block\nProps: {props_json}\n\n")
            elif btype == "roadmap":
                props_json = json.dumps(block)
                md_parts.append(f"\n\nCOMPONENT:\nType: roadmap\nProps: {props_json}\n\n")
            elif btype == "image":
                src = block.get("src") or block.get("url") or ""
                alt = block.get("alt") or block.get("caption") or "Blog Illustration"
                if src:
                    md_parts.append(f"\n\nIMAGE:\nsrc: {src}\nalt: {alt}\n\n")
            elif btype == "callout":
                text = block.get("text", "")
                md_parts.append(f"> {text}\n")
            elif btype == "list":
                for item in block.get("items", []):
                    md_parts.append(f"- {item}")
                md_parts.append("")
    return "\n\n".join(md_parts)

def find_mongo_doc_by_slug(collection, slug: str):
    """Robustly retrieves a MongoDB document matching slug, filename, title, or topic."""
    cursor = list(collection.find({}))
    for d in cursor:
        d_slug = d.get("slug") or ""
        d_title_slug = slugify(d.get("title") or "")
        d_topic_slug = slugify(d.get("topic") or "")
        d_file_slug = slugify((d.get("output_filename") or "").replace(".md", ""))
        
        if slug in [d_slug, d_title_slug, d_topic_slug, d_file_slug] or str(d.get("_id")) == slug:
            d["_id"] = str(d["_id"])
            return d
            
    return None

def build_mongo_delete_query(slug: str):
    """Builds an OR query to match MongoDB doc for deletion."""
    return {
        "$or": [
            {"slug": slug},
            {"output_filename": f"{slug}.md"},
            {"output_filename": slug},
            {"title": slug},
            {"topic": slug}
        ]
    }

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
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0)
):
    """
    List blogs directly from MongoDB 'blogs' collection as the single source of truth.
    Local file scanning is disabled to ensure exact database parity without duplicates.
    """
    try:
        db = mongo_db.get_db()
        collection = db["blogs"]
        
        query = {}
        if category:
            query["category"] = category
        if status:
            query["status"] = status
        if approved:
            query["approved"] = approved
            
        mongo_docs = list(collection.find(query).sort("created_at", -1).skip(skip).limit(limit))
        
        processed_blogs = []
        for doc in mongo_docs:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])

            slug = doc.get("slug") or slugify(doc.get("title") or "")
            if not slug:
                continue
                
            doc["slug"] = slug
            doc["output_filename"] = f"{slug}.md"
            doc["approved"] = doc.get("approved", "no")
            doc["quality_score"] = float(doc.get("quality_score") or 0.0)
            doc["word_count"] = int(doc.get("word_count") or 0)
            doc["created_at"] = doc.get("created_at") or doc.get("date") or ""
            doc["category"] = doc.get("category", "General")
            processed_blogs.append(doc)

        return {
            "total": collection.count_documents(query),
            "skip": skip,
            "limit": limit,
            "blogs": processed_blogs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query error: {e}")

@app.get("/api/blogs/{slug}")
def get_blog(slug: str):
    """
    Fetch a single blog directly from MongoDB 'blogs' collection.
    Falls back gracefully to 'topics' or local files if necessary.
    """
    db = mongo_db.get_db()
    
    # 1. Look up in 'blogs' collection
    doc = db["blogs"].find_one({"slug": slug})
    if not doc:
        # Try matching by title slug regex
        doc = db["blogs"].find_one({"title": {"$regex": f"^{re.escape(slug)}", "$options": "i"}})
        
    # 2. Fallback to topics collection
    if not doc:
        topics_col = db[mongo_db.MONGODB_COLLECTION_TOPICS]
        doc = find_mongo_doc_by_slug(topics_col, slug)

    md_path, json_path = find_files_by_slug(slug)
    
    if not doc and not md_path:
        raise HTTPException(status_code=404, detail=f"Blog with slug '{slug}' not found.")

    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])

    markdown_content = ""
    metadata = {}

    if doc:
        markdown_content = doc.get("markdown_content") or ""
        if not markdown_content and doc.get("sections"):
            markdown_content = sections_to_markdown(doc.get("sections", []))
            
        for k, v in doc.items():
            if k != "_id":
                metadata[k] = v
        metadata["blog_format"] = doc
        
    if md_path and os.path.exists(md_path) and not markdown_content:
        try:
            with open(md_path, "r", encoding="utf-8") as f:
                markdown_content = f.read()
        except Exception:
            pass

    if json_path and os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                file_meta = json.load(f)
                for k, v in file_meta.items():
                    if k not in metadata:
                        metadata[k] = v
        except Exception:
            pass

    final_title = (doc.get("title") if doc else None) or metadata.get("title") or slug
    final_category = (doc.get("category") if doc else None) or metadata.get("category") or "General"
    final_approved = (doc.get("approved") if doc else None) or metadata.get("approved") or "no"
    final_status = (doc.get("status") if doc else None) or "published"
    final_score = float((doc.get("quality_score") if doc else None) or metadata.get("quality_score") or 0.0)
    final_word_count = int((doc.get("word_count") if doc else None) or metadata.get("word_count") or 0)

    return {
        "slug": slug,
        "title": final_title,
        "category": final_category,
        "approved": final_approved,
        "status": final_status,
        "quality_score": final_score,
        "word_count": final_word_count,
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
            
    # Apply edits
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
    metadata["slug"] = slug
    
    out_dir = get_output_dir()
    new_md_path = md_path or os.path.join(out_dir, f"{slug}.md")
    new_json_path = json_path or os.path.join(out_dir, f"{slug}.json")
    
    with open(new_json_path, "w", encoding="utf-8") as jf:
        json.dump(metadata, jf, indent=2)
        
    with open(new_md_path, "w", encoding="utf-8") as mf:
        mf.write(markdown_content)
        
    # Sync to MongoDB
    try:
        db = mongo_db.get_db()
        collection = db[mongo_db.MONGODB_COLLECTION_TOPICS]
        
        doc = find_mongo_doc_by_slug(collection, slug)
        if doc and "_id" in doc:
            from bson import ObjectId
            collection.update_one(
                {"_id": ObjectId(doc["_id"]) if isinstance(doc["_id"], str) else doc["_id"]},
                {"$set": {
                    "title": metadata.get("title", slug),
                    "category": metadata.get("category", ""),
                    "word_count": word_count,
                    "markdown_content": markdown_content,
                    "metadata_json": json.dumps(metadata),
                    "updated_at": datetime.now().isoformat()
                }}
            )
        else:
            mongo_db.insert_published_blog({
                "slug": slug,
                "title": metadata.get("title", slug),
                "category": metadata.get("category", ""),
                "status": "published",
                "output_filename": f"{slug}.md",
                "markdown_content": markdown_content,
                "metadata": metadata
            })
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
        # Update in blogs collection
        db["blogs"].update_one(
            {"slug": slug},
            {"$set": {"approved": body.approved, "updated_at": datetime.now().isoformat()}}
        )
        # Also update in topics collection if present
        collection = db[mongo_db.MONGODB_COLLECTION_TOPICS]
        doc = find_mongo_doc_by_slug(collection, slug)
        if doc and "_id" in doc:
            from bson import ObjectId
            collection.update_one(
                {"_id": ObjectId(doc["_id"]) if isinstance(doc["_id"], str) else doc["_id"]},
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
    DELETE API: Permanently deletes a blog from both MongoDB and local filesystem.
    """
    md_path, json_path = find_files_by_slug(slug)
    
    deleted_files = []
    if md_path and os.path.exists(md_path):
        try:
            os.remove(md_path)
            deleted_files.append(md_path)
        except Exception as e:
            print(f"[Warning] Error deleting md file {md_path}: {e}")

    if json_path and os.path.exists(json_path):
        try:
            os.remove(json_path)
            deleted_files.append(json_path)
        except Exception as e:
            print(f"[Warning] Error deleting json file {json_path}: {e}")
            
    db_deleted_count = 0
    try:
        db = mongo_db.get_db()
        collection = db[mongo_db.MONGODB_COLLECTION_TOPICS]
        
        # Find all documents where slug matches ID, slug, title, topic, or filename
        cursor = list(collection.find({}))
        for d in cursor:
            d_id_str = str(d.get("_id", ""))
            d_slug = d.get("slug") or ""
            d_title_slug = slugify(d.get("title") or "")
            d_topic_slug = slugify(d.get("topic") or "")
            d_file_slug = slugify((d.get("output_filename") or "").replace(".md", ""))
            
            if slug in [d_slug, d_title_slug, d_topic_slug, d_file_slug, d_id_str]:
                del_res = collection.delete_one({"_id": d["_id"]})
                db_deleted_count += del_res.deleted_count
        
        # Also delete from 'blogs' collection
        b_del = db["blogs"].delete_many({"slug": slug})
        db_deleted_count += b_del.deleted_count
    except Exception as e:
        print(f"[Warning] MongoDB deletion error: {e}")
        
    return {
        "status": "success",
        "slug": slug,
        "deleted_files": deleted_files,
        "db_deleted": db_deleted_count > 0,
        "db_deleted_count": db_deleted_count
    }

