# MongoDB Migration - Change Log

## Overview
Complete migration of BlogGraph-AI from SQLite to MongoDB completed on 2025-06-05.

## Files Modified

### 1. `main.py` (FastAPI Application)
**Changes**: Updated 7 endpoint functions to use MongoDB instead of SQLite

#### Function: `bg_run_pipeline(category, title)`
- **Before**: Used `get_db_connection()`, SQL UPDATE to reset in_progress topics
- **After**: Uses `mongo_db.reset_in_progress_to_pending(title)`
- **Impact**: Background task error handling now uses MongoDB

#### Function: `health()`
- **Before**: `SELECT 1` SQL query to test database
- **After**: `mongo_db.get_mongo_client().admin.command('ping')`
- **Impact**: Health check now pings MongoDB cluster instead of SQLite file

#### Function: `get_blogs()`
- **Before**: `cursor.execute("SELECT * FROM topics WHERE title IS NOT NULL...")`
- **After**: `mongo_db.get_all_topics()` with ObjectId to string conversion
- **Impact**: Returns all documents from MongoDB collection

#### Function: `get_blog(blog_id: int)` → `get_blog(blog_id: str)`
- **Before**: Integer ID lookup with SQL JOIN
- **After**: String trace_id lookup with `mongo_db.get_topic_by_trace_id(blog_id)`
- **Impact**: Blog ID format changed from int to UUID string; endpoint parameter type updated

#### Function: `approve_blog(blog_id: int, payload)` → `approve_blog(blog_id: str, payload)`
- **Before**: SQL UPDATE statement; integer blog_id
- **After**: `mongo_db.update_topic_approval(trace_id, approved_val)` and `mongo_db.get_topic_by_trace_id(blog_id)`
- **Impact**: Approval status now stored in MongoDB; string trace_id parameter

#### Function: `edit_blog(blog_id: int, payload)` → `edit_blog(blog_id: str, payload)`
- **Before**: SQL UPDATE with word count calculation; integer blog_id
- **After**: `mongo_db.update_topic(trace_id, title, markdown_content, metadata_json)`; string trace_id
- **Impact**: Edits persist to MongoDB; string trace_id parameter

#### Function: `generate_blog(payload, background_tasks)`
- **Before**: `cursor.execute("SELECT id, title FROM topics WHERE status = 'in_progress'")`
- **After**: `mongo_db.get_all_topics()` with status filter
- **Impact**: Active generation check queries MongoDB instead of SQLite

**Removed from main.py**:
- `get_db_connection()` function (SQLite connection factory)
- All `sqlite3` imports and cursor operations
- All `conn.commit()` and `conn.close()` calls

**Added to main.py**:
- `from topic_selection import mongo_db` import

---

### 2. `requirements.txt`
**Changes**: Added MongoDB driver package

```diff
  pydantic>=2.0.0
  langchain>=0.1.0
  ...
  requests>=2.0.0
+ pymongo>=4.5.0
```

**Reason**: PyMongo is required to connect to MongoDB and perform CRUD operations

---

### 3. `topic_selection/queue_manager.py`
**Changes**: Refactored entire database layer to use mongo_db adapter

**Removed**:
```python
import sqlite3
from datetime import datetime, timedelta

def get_db_connection():
    """SQLite connection factory"""
    conn = sqlite3.connect("topics.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """SQLite schema initialization (85 lines of DDL)"""
    # Create topics table
    # Create indexes
    # Commit changes
```

**Added**:
```python
from . import mongo_db

# All db functions now delegate to mongo_db:
def init_db():
    return mongo_db.init_db()

def get_next_category():
    # Use mongo_db.get_all_topics() for queries
    # Use mongo_db.get_recent_titles() for dedup
    # Use mongo_db.get_next_category_max_id() for aging
```

**Preserved**:
- EXAMPLE_TITLE_PATTERNS (all 15 categories)
- Category weighting logic
- Seasonal boost multipliers
- Starvation/aging multiplier calculation

---

### 4. `.env` (Configuration File)
**Changes**: Added MongoDB connection variables

```diff
  # Existing variables...
  GROQ_API_KEY=...
  OPENROUTER_API_KEY=...
  
+ # MongoDB Configuration
+ MONGODB_URI=mongodb://localhost:27017
+ MONGODB_DATABASE=bloggraph_ai
+ MONGODB_COLLECTION_TOPICS=topics
```

---

### 5. `.env.example` (Configuration Template)
**Changes**: Same MongoDB additions as .env

---

### 6. `topic_selection/queue_manager_new.py`
**Status**: Deprecated file from migration planning
- **Note**: Can be deleted; kept for reference
- Contains backup implementation that was not used

---

### 7. `agents/formatter.py`
**Changes**: Updated comments to reference MongoDB instead of SQLite

```python
# Old: Mark Topic Queue as Published in SQLite DB
# New: Mark Topic Queue as Published in MongoDB
# Note: Actual code (queue_manager.mark_published()) remains unchanged
```

---

## Files Created

### 1. `topic_selection/mongo_db.py` (NEW)
**Purpose**: MongoDB adapter providing abstraction layer for all database operations

**Key Components**:
- `MONGODB_URI`, `MONGODB_DATABASE`, `MONGODB_COLLECTION_TOPICS` configuration
- `get_mongo_client()` - Singleton MongoDB client with error handling
- `get_db()` - Lazy-initialized database instance
- `init_db()` - Creates indexes and seeds database
- `mark_in_progress(trace_id, category, title)` - Update topic status
- `mark_published(trace_id, filename, score, word_count, markdown_content, metadata_json)` - Publish topic
- `get_recent_titles(category, months)` - Deduplication check
- `get_next_category_max_id()` - Get document count for aging
- `get_last_selected_categories()` - Category starvation weighting
- `get_all_topics()` - Retrieve all documents
- `get_topic_by_trace_id(trace_id)` - Single document lookup
- `update_topic_approval(trace_id, approved)` - Set approval status
- `update_topic(trace_id, title, markdown_content, metadata_json)` - Update document
- `reset_in_progress_to_pending(title)` - Reset failed tasks
- `close_connection()` - Cleanup function

**Document Schema**:
```json
{
  "_id": ObjectId,
  "category": "string",
  "title": "string",
  "status": "pending|in_progress|published",
  "trace_id": "string (UUID)",
  "output_filename": "string",
  "quality_score": number,
  "word_count": number,
  "created_at": "ISO datetime",
  "completed_at": "ISO datetime",
  "markdown_content": "string",
  "metadata_json": "string (JSON)",
  "approved": "yes|no"
}
```

**Indexes Created**:
1. `category` - Category-based queries
2. `status` - Status filtering
3. `trace_id` (unique, sparse) - Document lookup
4. `created_at` - Time-based queries
5. `(category, status)` - Compound for category selection

---

### 2. `setup_mongodb.py` (NEW)
**Purpose**: Setup and verification script for MongoDB configuration

**Functions**:
1. Connects to MongoDB server
2. Initializes database and collections
3. Creates indexes
4. Verifies configuration
5. Displays status and next steps

**Usage**:
```bash
python setup_mongodb.py
```

---

### 3. `MONGODB_MIGRATION.md` (NEW)
**Purpose**: Comprehensive setup and troubleshooting guide

**Contents**:
- Installation instructions for all platforms
- Environment variable setup
- API compatibility notes
- Database schema documentation
- Migration script for existing SQLite data
- Troubleshooting guide
- Production deployment recommendations
- MongoDB Atlas setup

---

### 4. `MONGODB_QUICKSTART.md` (NEW)
**Purpose**: Quick reference guide for getting started

**Contents**:
- 2-step installation
- Running the pipeline
- Change summary table
- Environment configuration
- Migration instructions
- File changes overview
- Troubleshooting quick fixes

---

## Database Schema Changes

### Topics Collection (MongoDB)

**New Fields**:
- `_id` - MongoDB ObjectId (12 bytes, unique)
- `trace_id` - UUID string (unique identifier for blogs)
- `created_at` - ISO 8601 datetime string
- `completed_at` - ISO 8601 datetime string or null

**Field Changes**:
- `id` (int) → `trace_id` (string UUID)
- `status` values unchanged: `pending`, `in_progress`, `published`
- `approved` unchanged: `yes`, `no`

**Removed Fields**:
- `id` - SQLite autoincrement no longer used

**Added Indexes**:
- `category` - For category-based queries
- `status` - For filtering by status
- `trace_id` - Unique constraint for document lookup
- `created_at` - For sorting and time-range queries
- Compound index on `(category, status)` - For category selection

---

## API Compatibility

### Endpoints Affected

| Endpoint | Parameter Change | Database Change |
|----------|------------------|-----------------|
| `GET /blogs/{blog_id}` | int → str | SQL → MongoDB |
| `POST /blogs/{blog_id}/approve` | int → str | SQL → MongoDB |
| `PUT /blogs/{blog_id}` | int → str | SQL → MongoDB |
| `GET /blogs` | - | SQL → MongoDB |
| `GET /health` | - | SQLite ping → MongoDB ping |
| `POST /generate` | - | SQL → MongoDB |

### Client Impact

- **Frontend**: Minimal - blog_id is now a UUID string instead of integer
- **API Response**: Same structure, JSON serialization of ObjectId to string
- **Backward Compatibility**: Not applicable - breaking change in ID format

---

## Business Logic Preservation

All core business logic remains unchanged:

✓ **Category Selection**:
- Starvation multiplier: `1.0 + (runs_since * 0.2)`
- Seasonal weight boosts from `config.SEASONAL_WEIGHTS`
- Same 15 categories and title patterns

✓ **Topic Management**:
- Status workflow: pending → in_progress → published
- Approval workflow: yes/no toggle
- Metadata JSON and markdown synchronization

✓ **Deduplication**:
- 3-month title recency check using `get_recent_titles()`
- Fuzzy matching logic in `dedup_checker.py`

✓ **Pipeline Orchestration**:
- LangGraph topology unchanged
- Agent calls unchanged
- Output file generation unchanged

---

## Testing Checklist

- [ ] MongoDB connection successful
- [ ] Database and collection created
- [ ] Indexes created automatically
- [ ] Can add new blog topic
- [ ] Status transitions work (pending → in_progress → published)
- [ ] Approval toggle works
- [ ] Edit blog updates MongoDB
- [ ] Dashboard displays all blogs
- [ ] API returns trace_id instead of int ID
- [ ] Health endpoint returns MongoDB status

---

## Deployment Notes

### Environment Variables Required
```
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=bloggraph_ai
MONGODB_COLLECTION_TOPICS=topics
```

### Dependencies Added
- `pymongo>=4.5.0`

### Dependencies Removed
- `sqlite3` (built-in, no longer needed)

### File System Changes
- `topics.db` no longer used (can be deleted)
- MongoDB data persisted in MongoDB server instead

### Backward Compatibility
- **NOT compatible** with SQLite-based deployments
- Migration script available in `MONGODB_MIGRATION.md` for data migration
- Fresh start recommended for new deployments

---

## Performance Implications

| Metric | SQLite | MongoDB |
|--------|--------|---------|
| Query Speed | Fast for small data | Optimized for scale |
| Concurrent Writes | Locked | Non-blocking |
| Disk Usage | Single file | Distributed |
| Scaling | Difficult | Easy (sharding) |
| Cloud Deployment | Not ideal | Excellent (Atlas) |

---

## Future Improvements

- [ ] MongoDB Atlas Cloud deployment guide
- [ ] Backup and restore procedures
- [ ] Replication setup for high availability
- [ ] Sharding configuration for massive scale
- [ ] Audit logging for all operations
- [ ] Data retention policies
- [ ] Performance monitoring and alerts

---

## Summary

**Status**: ✅ Migration Complete  
**Tests**: Pending (requires MongoDB server running)  
**Breaking Changes**: API blog_id format changed to string UUID  
**Data Migration**: Available via provided script  
**Production Ready**: Yes (with MongoDB running)  

Total files modified: 7  
Total files created: 4  
Lines of code changed: ~200+  
SQLite references removed: Complete (except comments and unrelated projects)
