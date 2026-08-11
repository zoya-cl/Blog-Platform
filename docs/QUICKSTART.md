# 🚀 BlogGraph-AI — Quickstart Guide

This guide covers how to set up the environment, run the **FastAPI REST API**, execute the **Modular Test Suite**, and run the **CLI Pipeline**.

---

## 📋 Prerequisites & Setup

### 1. Environment & Dependencies
Ensure Python 3.10+ is installed. Activate your virtual environment and install dependencies:

```bash
# Activate virtual environment (.venv)
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# Install required dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables (`.env`)
Create or update your `.env` file in the project root:

```env
OPENROUTER_API_KEY=your_openrouter_api_key
TAVILY_API_KEY=your_tavily_api_key

# MongoDB Configuration
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=bloggraph_ai
MONGODB_COLLECTION_TOPICS=topics
```

### 3. Ensure Local MongoDB is Running
Make sure MongoDB is running on port `27017` (e.g. via MongoDB Community Edition or Docker):

```bash
mongod
# OR check connection with MongoDB Compass at: mongodb://localhost:27017
```

---

## ⚡ 1. Running the FastAPI REST Server

The REST API exposes full CRUD and AI generation background tasks.

### Launch the Server
```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

- **API Base URL**: `http://127.0.0.1:8000`
- **Interactive Swagger Documentation**: [`http://127.0.0.1:8000/docs`](http://127.0.0.1:8000/docs)

---

### API Usage Examples

#### 🔹 List All Blogs
```bash
curl -X GET "http://127.0.0.1:8000/api/blogs?limit=10&skip=0"
```

#### 🔹 Fetch Single Blog (Markdown + Metadata)
```bash
curl -X GET "http://127.0.0.1:8000/api/blogs/kubernetes-vs-docker-swarm-the-2026-container-orchestration-showdown"
```

#### 🔹 Edit Blog Markdown / Metadata
```bash
curl -X PUT "http://127.0.0.1:8000/api/blogs/kubernetes-vs-docker-swarm-the-2026-container-orchestration-showdown" \
     -H "Content-Type: application/json" \
     -d '{
       "title": "Kubernetes vs Docker Swarm: 2026 Ultimate Guide",
       "focus_keyword": "Kubernetes vs Docker Swarm 2026",
       "markdown_content": "# Updated Markdown Content Here..."
     }'
```

#### 🔹 Approve / Reject a Blog
```bash
curl -X PUT "http://127.0.0.1:8000/api/blogs/kubernetes-vs-docker-swarm-the-2026-container-orchestration-showdown/approve" \
     -H "Content-Type: application/json" \
     -d '{"approved": "yes"}'
```

#### 🔹 Trigger AI Blog Generation (Background Task)
```bash
curl -X POST "http://127.0.0.1:8000/api/blogs/generate" \
     -H "Content-Type: application/json" \
     -d '{
       "category": "Developer Technology",
       "topic": "Rust vs Go in 2026 High-Performance Services"
     }'
```

#### 🔹 Delete a Blog
```bash
curl -X DELETE "http://127.0.0.1:8000/api/blogs/kubernetes-vs-docker-swarm-the-2026-container-orchestration-showdown"
```

---

## 🧪 2. Running the Modular Test Suite (`test_modules.py`)

The modular test suite allows you to run and inspect each phase of the AI engine independently or execute the complete end-to-end flow with the automated Quality Gate retry loop.

### Run Interactive Test Menu
```bash
python test_modules.py
```

### Direct Menu Choices
- `0`: Run ALL modules end-to-end (Title → Search/Plan → Write/Assemble → Quality Gate/Publish)
- `1`: Run **Module 1** (Title Generator & RapidFuzz Dedup)
- `2`: Run **Module 2** (Tavily Search & Intake Planner Node)
- `3`: Run **Module 3** (Async Parallel Writer & Assembler + Auto-FAQ)
- `4`: Run **Module 4** (Quality Grader, Retry Rewriter Loop & Publisher)

### Direct CLI Shortcuts
```bash
# Run all modules end-to-end
python test_modules.py all

# Run specific module directly (e.g. Quality Check)
python test_modules.py 4
```

> **Artifact Outputs**: All intermediate JSON traces and final markdown previews are auto-saved to:
> `output/module_outputs/`

---

## 🖥️ 3. Running the CLI Runner (`run.py`)

To generate a single blog post directly from the command line without starting the API server:

```bash
python run.py
```

- Prompts for category and topic selection.
- Outputs final `.md` post and `.json` metadata sidecar to `/output/`.
- Automatically persists the published document into MongoDB.

---

## 🎨 4. Frontend UI Usage (Coming Soon)

*(Reserved section for upcoming React / Next.js Dashboard integration)*
