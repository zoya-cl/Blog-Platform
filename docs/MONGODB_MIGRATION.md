# MongoDB Migration Guide

This document describes the migration from SQLite to MongoDB for the BlogGraph-AI pipeline.

## Overview

The BlogGraph-AI pipeline has been migrated from SQLite (`topics.db`) to MongoDB for better scalability, flexibility, and cloud-readiness.

## Setup Instructions

### 1. Install MongoDB

**On Windows (Using MongoDB Community Edition):**

```powershell
# Using Chocolatey
choco install mongodb-community

# Or download from https://www.mongodb.com/try/download/community
# and follow the installer
```

**On macOS:**

```bash
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb-community
```

**On Linux (Ubuntu/Debian):**

```bash
sudo apt-get install -y mongodb
sudo systemctl start mongodb
```

**Or use Docker:**

```bash
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

### 2. Update Environment Variables

Edit the `.env` file in the project root and add MongoDB configuration:

```env
# MongoDB Configuration
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=bloggraph_ai
MONGODB_COLLECTION_TOPICS=topics
```

**For Remote MongoDB (e.g., MongoDB Atlas):**

```env
MONGODB_URI=mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/
MONGODB_DATABASE=bloggraph_ai
MONGODB_COLLECTION_TOPICS=topics
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

This includes the new `pymongo>=4.5.0` dependency.

### 4. Run the Pipeline

The pipeline will automatically initialize MongoDB and create necessary collections with indexes on first run:

```bash
python run.py
```

Or start the web UI:

```bash
python main.py
```

## Database Schema

### MongoDB Collection: `topics`

The `topics` collection stores blog generation metadata:

```json
{
  "_id": ObjectId(),
  "category": "Job Role and Career Trends",
  "title": "What Does an AI Engineer Actually Do in 2026?",
  "status": "published",  // pending, in_progress, published
  "trace_id": "uuid-string",
  "output_filename": "what-does-ai-engineer-do.md",
  "quality_score": 8.5,
  "word_count": 2850,
  "created_at": "2026-06-05T14:30:00.123456",
  "completed_at": "2026-06-05T15:45:00.123456",
  "markdown_content": "# Blog post content...",
  "metadata_json": "{\"title\": \"...\", \"slug\": \"...\", ...}",
  "approved": "yes"  // yes, no
}
```

### Indexes

The following indexes are automatically created for performance:

- `category` - For category-based queries
- `status` - For status filtering
- `trace_id` (unique, sparse) - For document lookup
- `created_at` - For time-based queries
- Compound index on `(category, status)` - For weighted category selection

## API Compatibility

The FastAPI endpoints remain identical, but now query MongoDB instead of SQLite:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check (includes MongoDB connection status) |
| `/blogs` | GET | List all blogs |
| `/blogs/{blog_id}` | GET | Get specific blog by trace_id |
| `/blogs/{blog_id}/approve` | POST | Approve/unapprove blog |
| `/blogs/{blog_id}` | PUT | Edit blog title/content/metadata |
| `/generate` | POST | Trigger pipeline |
| `/dashboard` | GET | Admin dashboard SPA |

## Migration from SQLite

If you have existing SQLite data, you can migrate it using this Python script:

```python
import sqlite3
import json
from datetime import datetime
from topic_selection.mongo_db import get_db, init_db

# Initialize MongoDB
init_db()

# Connect to SQLite
sqlite_conn = sqlite3.connect("topics.db")
sqlite_conn.row_factory = sqlite3.Row
cursor = sqlite_conn.cursor()

# Get all topics from SQLite
cursor.execute("SELECT * FROM topics")
rows = cursor.fetchall()

# Prepare MongoDB collection
db = get_db()
collection = db["topics"]

# Migrate each document
for row in rows:
    doc = {
        "category": row["category"],
        "title": row["title"],
        "status": row["status"],
        "output_filename": row["output_filename"],
        "quality_score": row["quality_score"],
        "word_count": row["word_count"],
        "trace_id": row["trace_id"],
        "created_at": row["created_at"],
        "completed_at": row["completed_at"],
        "markdown_content": row["markdown_content"],
        "metadata_json": row["metadata_json"],
        "approved": row["approved"] or "no"
    }
    
    # Insert if not exists (using trace_id as unique identifier)
    if doc["trace_id"]:
        collection.update_one(
            {"trace_id": doc["trace_id"]},
            {"$set": doc},
            upsert=True
        )
    else:
        collection.insert_one(doc)

sqlite_conn.close()
print("✓ Migration complete!")
```

## MongoDB Functions Reference

All database operations are abstracted in `topic_selection/mongo_db.py`:

### Connection Management

```python
from topic_selection import mongo_db

# Get MongoDB connection
client = mongo_db.get_mongo_client()

# Get database instance
db = mongo_db.get_db()

# Close connection
mongo_db.close_connection()
```

### Common Operations

```python
# Initialize database with indexes
mongo_db.init_db()

# Get all topics
mongo_db.get_all_topics()

# Get topic by trace_id
mongo_db.get_topic_by_trace_id(trace_id)

# Mark topic as in progress
mongo_db.mark_in_progress(trace_id, category, title)

# Mark topic as published
mongo_db.mark_published(trace_id, filename, score, word_count, markdown_content, metadata_json)

# Get recent titles for deduplication
mongo_db.get_recent_titles(category, months=3)

# Update topic approval status
mongo_db.update_topic_approval(trace_id, approved)

# Update topic (title, markdown, metadata)
mongo_db.update_topic(trace_id, title, markdown_content, metadata_json)

# Reset in-progress topic to pending
mongo_db.reset_in_progress_to_pending(title)
```

## Troubleshooting

### MongoDB Connection Issues

**Error: "Failed to connect to MongoDB"**

1. Ensure MongoDB server is running:
   ```bash
   # Check if MongoDB is running
   ps aux | grep mongod  # Linux/Mac
   tasklist | findstr mongod  # Windows
   ```

2. Verify connection URI in `.env`:
   ```env
   MONGODB_URI=mongodb://localhost:27017
   ```

3. Test connection manually:
   ```python
   from pymongo import MongoClient
   client = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=5000)
   client.admin.command('ping')  # Should print {'ok': 1.0}
   ```

### Database Connection Pool

If you experience connection timeout issues, adjust the connection URI:

```env
MONGODB_URI=mongodb://localhost:27017/?serverSelectionTimeoutMS=10000&connectTimeoutMS=10000
```

### Performance

For production deployments, consider:

- **Connection Pooling**: Set `maxPoolSize` in URI
- **Indexing**: Verify indexes are created on first init
- **Replication**: Use MongoDB Atlas for automatic replication

```env
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/?maxPoolSize=50&minPoolSize=10
```

## Differences from SQLite

| Aspect | SQLite | MongoDB |
|--------|--------|---------|
| Data Type | SQL Tables | JSON Documents |
| Query Language | SQL | MongoDB Query Language |
| ID Field | Autoincrement integer | ObjectId (12-byte unique) |
| Date Format | ISO 8601 String | ISODate or String |
| Null Handling | NULL | null or missing field |
| Transactions | ACID on tables | ACID on documents |
| Scalability | Single file | Distributed |

## For Local Development

If you want to run MongoDB locally without installation, use Docker:

```bash
# Start MongoDB container
docker run -d -p 27017:27017 --name blog-mongo mongo:latest

# View logs
docker logs blog-mongo

# Stop container
docker stop blog-mongo

# Remove container
docker rm blog-mongo
```

## For Production Deployment

Use MongoDB Atlas (managed cloud service):

1. Create account at https://www.mongodb.com/cloud/atlas
2. Create a free cluster
3. Get connection string from Atlas dashboard
4. Update `.env` with connection string:
   ```env
   MONGODB_URI=mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```

## Summary

The migration to MongoDB provides:

✅ **Scalability** - Horizontal scaling and sharding support  
✅ **Flexibility** - Schema-less JSON documents  
✅ **Performance** - Optimized indexing and queries  
✅ **Cloud-Ready** - Native support for MongoDB Atlas  
✅ **Reliability** - Automatic replication and failover  

The API remains 100% compatible, so no frontend changes are needed!
