"""
MongoDB adapter for BlogGraph-AI.
Replaces SQLite database with MongoDB for scalability and flexibility.
"""

import os
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure
from dotenv import load_dotenv

load_dotenv()

# MongoDB Configuration
MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE")
MONGODB_COLLECTION_TOPICS = os.getenv("MONGODB_COLLECTION_TOPICS")

# Global MongoDB client
_client = None
_db = None


def get_mongo_client():
    """Get or create MongoDB client."""
    global _client
    if _client is None:
        try:
            _client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
            # Verify connection
            _client.admin.command('ping')
            print(f"✓ Connected to MongoDB at {MONGODB_URI}")
        except (ServerSelectionTimeoutError, ConnectionFailure) as e:
            print(f"✗ Failed to connect to MongoDB: {e}")
            raise
    return _client


def get_db():
    """Get MongoDB database instance."""
    global _db
    if _db is None:
        client = get_mongo_client()
        _db = client[MONGODB_DATABASE]
    return _db


def close_connection():
    """Close MongoDB connection."""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
        print("✓ MongoDB connection closed")


def init_db():
    """
    Initialize MongoDB database and create indexes for the topics collection.
    Creates collection if it doesn't exist and sets up necessary indexes.
    """
    try:
        db = get_db()
        collection = db[MONGODB_COLLECTION_TOPICS]
        
        # Create indexes for optimal query performance
        collection.create_index("category")
        collection.create_index("status")
        collection.create_index("trace_id", unique=True, sparse=True)
        collection.create_index("created_at")
        collection.create_index([("category", 1), ("status", 1)])
        
        print(f"✓ MongoDB collection '{MONGODB_COLLECTION_TOPICS}' initialized with indexes")
        
        # Check if we have seeded categories. If not, seed one record per category.
        count = collection.count_documents({})
        if count == 0:
            import config
            now_str = datetime.now().isoformat()
            docs_to_insert = []
            for category in config.CATEGORIES:
                docs_to_insert.append({
                    "category": category,
                    "title": None,
                    "status": "pending",
                    "output_filename": None,
                    "quality_score": None,
                    "word_count": None,
                    "trace_id": None,
                    "created_at": now_str,
                    "completed_at": None,
                    "markdown_content": None,
                    "metadata_json": None,
                    "approved": "no"
                })
            collection.insert_many(docs_to_insert)
            print(f"✓ Seeded {len(docs_to_insert)} initial category records")
            
    except Exception as e:
        print(f"✗ Error initializing MongoDB: {e}")
        raise


def get_next_category_max_id() -> int:
    """Get the maximum document count to determine progress."""
    try:
        db = get_db()
        collection = db[MONGODB_COLLECTION_TOPICS]
        count = collection.count_documents({})
        return count
    except Exception as e:
        print(f"✗ Error getting max ID: {e}")
        return 0


def get_last_selected_categories() -> dict:
    """Get the last selected ID for each category (in_progress or published)."""
    try:
        db = get_db()
        collection = db[MONGODB_COLLECTION_TOPICS]
        
        # Use aggregation pipeline to group by category and get the max _id (which auto-increments conceptually)
        pipeline = [
            {"$match": {"status": {"$in": ["in_progress", "published"]}}},
            {"$group": {
                "_id": "$category",
                "count": {"$sum": 1}  # Count documents per category
            }},
            {"$project": {"category": "$_id", "count": 1, "_id": 0}}
        ]
        
        results = list(collection.aggregate(pipeline))
        return {item["category"]: item["count"] for item in results}
        
    except Exception as e:
        print(f"✗ Error getting last selected categories: {e}")
        return {}


def mark_in_progress(trace_id: str, category: str, title: str):
    """
    Transition a pending category record to in_progress and record the generated title.
    If no pending record exists, insert a new in-progress record.
    """
    try:
        db = get_db()
        collection = db[MONGODB_COLLECTION_TOPICS]
        now_str = datetime.now().isoformat()
        
        # Try to find a pending row for this category
        pending_doc = collection.find_one({"category": category, "status": "pending"})
        
        if pending_doc:
            collection.update_one(
                {"_id": pending_doc["_id"]},
                {"$set": {
                    "title": title,
                    "status": "in_progress",
                    "trace_id": trace_id,
                    "created_at": now_str
                }}
            )
        else:
            # If no pending slot exists, insert a new record
            collection.insert_one({
                "category": category,
                "title": title,
                "status": "in_progress",
                "trace_id": trace_id,
                "created_at": now_str,
                "output_filename": None,
                "quality_score": None,
                "word_count": None,
                "completed_at": None,
                "markdown_content": None,
                "metadata_json": None,
                "approved": "no"
            })
            
    except Exception as e:
        print(f"✗ Error marking document in progress: {e}")
        raise


def mark_published(trace_id: str, filename: str, score: float, word_count: int, 
                   markdown_content: str = None, metadata_json: str = None):
    """
    Mark the in-progress topic record matching trace_id as published.
    """
    try:
        db = get_db()
        collection = db[MONGODB_COLLECTION_TOPICS]
        now_str = datetime.now().isoformat()
        
        collection.update_one(
            {"trace_id": trace_id, "status": "in_progress"},
            {"$set": {
                "status": "published",
                "output_filename": filename,
                "quality_score": score,
                "word_count": word_count,
                "completed_at": now_str,
                "markdown_content": markdown_content,
                "metadata_json": metadata_json
            }}
        )
        
    except Exception as e:
        print(f"✗ Error marking document published: {e}")
        raise


def get_recent_titles(category: str, months: int = 3) -> list:
    """
    Fetch titles for a specific category from the past few months
    that are published or in progress, to prevent duplicate topic generation.
    """
    try:
        db = get_db()
        collection = db[MONGODB_COLLECTION_TOPICS]
        
        # Calculate the date threshold
        from datetime import timedelta
        cutoff_date = (datetime.now() - timedelta(days=months*30)).isoformat()
        
        docs = collection.find({
            "category": category,
            "status": {"$in": ["published", "in_progress"]},
            "title": {"$ne": None},
            "created_at": {"$gte": cutoff_date}
        })
        
        return [doc["title"] for doc in docs]
        
    except Exception as e:
        print(f"✗ Error getting recent titles: {e}")
        return []


def update_topic_approval(trace_id: str, approved: str):
    """Update approval status for a topic."""
    try:
        db = get_db()
        collection = db[MONGODB_COLLECTION_TOPICS]
        
        collection.update_one(
            {"trace_id": trace_id},
            {"$set": {"approved": approved}}
        )
        
    except Exception as e:
        print(f"✗ Error updating topic approval: {e}")
        raise


def get_all_topics():
    """Get all topics ordered by creation date (newest first)."""
    try:
        db = get_db()
        collection = db[MONGODB_COLLECTION_TOPICS]
        
        docs = collection.find({"title": {"$ne": None}}).sort("created_at", -1)
        
        # Convert MongoDB documents to dict-like objects (remove _id if needed)
        return [doc for doc in docs]
        
    except Exception as e:
        print(f"✗ Error fetching all topics: {e}")
        return []


def get_topic_by_trace_id(trace_id: str):
    """Get a specific topic by trace_id."""
    try:
        db = get_db()
        collection = db[MONGODB_COLLECTION_TOPICS]
        
        return collection.find_one({"trace_id": trace_id})
        
    except Exception as e:
        print(f"✗ Error fetching topic by trace_id: {e}")
        return None


def update_topic(trace_id: str, title: str = None, markdown_content: str = None, 
                 metadata_json: str = None):
    """Update topic with new title, markdown, and metadata."""
    try:
        db = get_db()
        collection = db[MONGODB_COLLECTION_TOPICS]
        
        update_data = {}
        if title is not None:
            update_data["title"] = title
        if markdown_content is not None:
            update_data["markdown_content"] = markdown_content
        if metadata_json is not None:
            update_data["metadata_json"] = metadata_json
            
        collection.update_one(
            {"trace_id": trace_id},
            {"$set": update_data}
        )
        
    except Exception as e:
        print(f"✗ Error updating topic: {e}")
        raise


def reset_in_progress_to_pending(title: str):
    """Reset an in-progress topic back to pending if pipeline fails."""
    try:
        db = get_db()
        collection = db[MONGODB_COLLECTION_TOPICS]
        
        collection.update_one(
            {"title": title, "status": "in_progress"},
            {"$set": {
                "status": "pending",
                "title": None,
                "trace_id": None
            }}
        )
        
    except Exception as e:
        print(f"✗ Error resetting topic to pending: {e}")
        raise
