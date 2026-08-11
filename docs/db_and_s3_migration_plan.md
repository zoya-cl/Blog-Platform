# BlogGraph-AI: Database and S3 Migration Plan

This document provides a detailed technical specification for migrating the BlogGraph-AI database from SQLite to either PostgreSQL or MongoDB, and migrating local image storage to AWS S3. 

---

## 1. Environment Configurations (`.env`)

Add the following environment variables to coordinate the remote database and S3 clients:

```ini
# --- S3 Configuration ---
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=ap-south-1
S3_BUCKET_NAME=your-bloggraph-assets-bucket

# --- For Option A: PostgreSQL ---
DB_PROVIDER=postgres
DB_HOST=your-rds-host.amazonaws.com
DB_PORT=5432
DB_NAME=bloggraph
DB_USER=postgres
DB_PASSWORD=your_secure_password

# --- For Option B: MongoDB ---
DB_PROVIDER=mongodb
MONGODB_URI=mongodb+srv://user:password@your-cluster.mongodb.net/bloggraph?retryWrites=true&w=majority
```

---

## 2. Phase 1: Database Migration

SQLite database connections are established in only two places:
1.  `main.py` (FastAPI router database calls)
2.  `topic_selection/queue_manager.py` (starvation aging and queue manager)

### Option A: Relational Database Migration (PostgreSQL / AWS RDS)

#### 1. Connection Configurations
Modify `get_db_connection()` in both `main.py` and `topic_selection/queue_manager.py` to connect via PostgreSQL.

```python
import os
import psycopg2
from psycopg2.extras import RealDictCursor

def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "bloggraph"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
        connect_timeout=10
    )
    # Enable dict cursor to return column-name indexed results similar to sqlite3.Row
    conn.cursor_factory = RealDictCursor
    return conn
```

#### 2. SQL Schema Creation (`queue_manager.py`)
Update the `init_db()` schema definition inside `topic_selection/queue_manager.py` to match PostgreSQL syntax:

```sql
CREATE TABLE IF NOT EXISTS topics (
    id SERIAL PRIMARY KEY,
    category VARCHAR(255) NOT NULL,
    title VARCHAR(500),
    status VARCHAR(50) NOT NULL CHECK(status IN ('pending', 'in_progress', 'published')),
    output_filename VARCHAR(500),
    quality_score REAL,
    word_count INTEGER,
    trace_id VARCHAR(100),
    created_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    markdown_content TEXT,
    metadata_json TEXT,
    approved VARCHAR(10) DEFAULT 'no' CHECK(approved IN ('yes', 'no'))
);
```

#### 3. Dialect Updates
*   **Parameterized Queries**: Change parameter placeholders from `?` (SQLite) to `%s` (PostgreSQL).
    *   *Example:* `cursor.execute("SELECT * FROM topics WHERE id = %s", (blog_id,))`
*   **Time Queries**: Adjust date math inside `get_recent_titles()` inside `queue_manager.py`:
    ```python
    # SQLite: created_at >= datetime('now', '-3 month')
    # PostgreSQL:
    cursor.execute(
        "SELECT title FROM topics WHERE status IN ('published', 'in_progress') "
        "AND title IS NOT NULL AND category = %s "
        "AND created_at >= NOW() - INTERVAL '%s month'",
        (category, months)
    )
    ```

---

### Option B: Document NoSQL Database Migration (MongoDB)

If migrating to MongoDB, relational SQL operations must be rewritten to utilize collection document mutations.

#### 1. Connection Configurations
Install `pymongo` and create a shared Mongo database client in `main.py` and `topic_selection/queue_manager.py`:

```python
import os
from pymongo import MongoClient

def get_db_client():
    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    client = MongoClient(uri)
    db = client.get_database() # Selected from connection string database
    return db
```

#### 2. Query Rewriting Specifications

##### List Queue (in `main.py`)
```python
# SQLite: SELECT * FROM topics WHERE title IS NOT NULL ORDER BY created_at DESC
# MongoDB:
db = get_db_client()
blogs = list(db.topics.find({"title": {"$ne": None}}).sort("created_at", -1))
# Convert ObjectId to string for JSON serialization
for b in blogs:
    b["id"] = str(b.pop("_id"))
```

##### Toggle Approval State (in `main.py`)
```python
# SQLite: UPDATE topics SET approved = ? WHERE id = ?
# MongoDB:
from bson import ObjectId
db.topics.update_one({"_id": ObjectId(blog_id)}, {"$set": {"approved": approved_val}})
```

##### Starvation Selection Check (`get_next_category` in `queue_manager.py`)
```python
# SQLite: SELECT MAX(id) FROM topics
# MongoDB:
max_doc = db.topics.find_one(sort=[("created_at", -1)])
# Starvation aging loop lookup:
last_selected = {}
for category in CATEGORIES:
    last_doc = db.topics.find_one(
        {"category": category, "status": {"$in": ["in_progress", "published"]}},
        sort=[("created_at", -1)]
    )
    # Calculate runs_since using timestamp differences or document order metrics
```

---

## 3. Phase 2: Image Storage Migration (AWS S3)

To move image storage from local filesystems to S3, modify the image generator task in **`agents/image_generator.py`**.

### 1. Uploading Images to S3 (`agents/image_generator.py`)
Replace the local filesystem write calls (`write_bytes()`) with the AWS SDK (`boto3`) S3 upload client:

```python
import os
import boto3
from botocore.exceptions import ClientError

def upload_image_to_s3(image_bytes: bytes, bucket_name: str, object_name: str) -> str:
    """
    Uploads image bytes to S3 and returns the public absolute URL.
    """
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION", "ap-south-1")
    )
    
    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=object_name,
            Body=image_bytes,
            ContentType="image/png"
        )
        region = os.getenv("AWS_REGION", "ap-south-1")
        url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{object_name}"
        return url
    except ClientError as e:
        print(f"[ERROR] Failed to upload image to S3: {e}")
        return ""
```

### 2. Integration into `image_generator_node`
Inside `image_generator_node(state)`:
1.  Extract `bucket_name` from configuration env variables.
2.  Generate S3 object key target: `object_key = f"{slug}/images/img_{idx}.png"`.
3.  Upload decoded base64 bytes to S3:
    ```python
    s3_url = upload_image_to_s3(base64.b64decode(data), bucket_name, object_key)
    ```
4.  Store `s3_url` in both `relative_path` and `generated_images`.
5.  Inject the absolute `s3_url` markdown directly into the section text:
    ```python
    image_md = f"\n\n![{purpose}]({s3_url})\n\n"
    ```

### 3. Visual Rendering verification (Zero Frontend Code Changes)
Because S3 URLs start with `http://` or `https://`, the dashboard viewer's JS regex in **`main.py`** naturally bypasses them:
```javascript
md = md.replace(/!\\[(.*?)\\]\\((.*?)\\)/g, (match, alt, src) => {
    if (src.startsWith('http') || src.startsWith('/')) {
        return `![${alt}](${src})`; // S3 URL is returned exactly as-is
    }
    return `![${alt}](/output/${src})`;
});
```
This guarantees image rendering in the Admin Dashboard is functional immediately without updating client code.
