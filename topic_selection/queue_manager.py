import sqlite3
import random
import os
from datetime import datetime
import config

DB_PATH = "topics.db"

# Sample title patterns to serve as reference styling for LLM title generation
EXAMPLE_TITLE_PATTERNS = {
    "Job Role and Career Trends": [
        "What Does an AI Engineer Actually Do in {year}?",
        "Skills Required to Become a Cloud DevOps Engineer",
        "iOS Developer vs Android Developer — Career Choice for Freshers",
        "Backend vs Frontend Developer — Which Career Should You Choose?",
        "Cyber Security Analyst Career Path & Salary in India",
        "Top Career Options for CSE Students Beyond SDE",
        "What is an Embedded Systems Engineer? Salary, Skills & Scope",
        "AI Engineer Salary in India — Fresher to Experienced Breakdown",
        "Are Layoffs Affecting Cloud & SRE Roles? Current Hiring Reality",
        "DevOps vs Data Engineering — Which Career Path Is Better?",
        "SWE Intern vs SDE 1 — Expectations, Responsibilities, and Daily Life",
        "How to Find Off-Campus Internships in India: Sites, Cold Emails & Strategies"
    ],
    "Resume Writing": [
        "ATS-Friendly Resume Format for Freshers — Free Template Guide",
        "How to Describe AWS and Cloud Projects on a Resume",
        "Best Web Dev Projects to Add to Your Resume in {year}",
        "How to Write a Strong Data Analyst Resume Without Experience",
        "Resume vs CV — What Tech Freshers Should Actually Use",
        "LinkedIn Profile Tips for Cybersecurity Aspirants",
        "How Recruiters Scan Mobile App Developer Resumes",
        "Formatting GitHub Projects on Your Tech Resume",
        "Best Resume Format for Product-Based Company Placements",
        "Portfolio Websites for Frontend Developers: Best Practices",
        "How to Write a Tech Resume for Internship Applications (With Examples)"
    ],
    "Placement Roadmaps": [
        "3-Month DSA Roadmap for SDE Placement Preparation",
        "Complete DevOps & Cloud Engineering Roadmap for Beginners",
        "Cybersecurity Roadmap: From Networking Basics to Certified Analyst",
        "Roadmap to Crack Product-Based Companies from Tier 3 Colleges",
        "Step-by-Step Data Analyst & SQL Roadmap for Freshers",
        "Android Developer Roadmap: Native Kotlin and Modern Libraries",
        "System Design Roadmap for SDE 1 and Freshers",
        "Biggest Mistakes Students Make During Placements",
        "What Actually Matters More — DSA, Projects, or CGPA?",
        "Complete QA and Automation Testing Roadmap",
        "Ultimate Internship Preparation Guide: Timeline, DSA, and Projects"
    ],
    "Interview Question Collections": [
        "Top DBMS & SQL Interview Questions for Freshers",
        "Most Asked OOPs Interview Questions with Answers",
        "Top HR Interview Questions Every Tech Student Must Prepare",
        "React & JavaScript Interview Questions for Frontend Roles",
        "Linux Commands and Shell Scripting Interview Questions",
        "Essential Computer Networks & Security Questions for SRE Roles",
        "SQL Interview Questions Asked in Service Companies",
        "Top Behavioral Interview Questions for Placements",
        "iOS Developer Interview Questions (Swift & UIKit)",
        "Core Java and Collections Framework Questions for Interviews"
    ],
    "DSA and Coding": [
        "Top 50 Arrays Questions for SDE Preparation",
        "Dynamic Programming for Interviews — Beginner to Advanced",
        "Blind 75 LeetCode Questions — Complete Beginner Guide",
        "30-Day Competitive Coding Preparation Plan",
        "TCS NQT Aptitude Pattern Explained with Examples",
        "Graph and Tree Algorithms in Python and Java",
        "C++ STL vs Java Collections for Interview Coding",
        "Top Sorting & Searching Algorithms Explained with Code"
    ],
    "Comparison Articles": [
        "SDE vs DevOps vs Data Analyst — Which Tech Role to Pick?",
        "Service Companies vs Product Companies — What Should You Choose?",
        "DSA vs Development — What Matters More for Placements?",
        "AI Engineer vs Cloud Engineer — Career Comparison {year}",
        "Frontend vs Backend Development — Which Career Path Is Better?",
        "On-Campus vs Off-Campus Placements — Which Is Easier?",
        "Java vs Go for Microservices — Which Should You Learn First?",
        "Startup vs MNC Jobs for Freshers — Pros & Cons",
        "Relational (SQL) vs Non-Relational (NoSQL) Databases for Placements",
        "AI Mock Interviews vs Human Mock Interviews — Which Helps More?"
    ],
    "AI Technology": [
        "How Retrieval-Augmented Generation (RAG) Actually Works in Production",
        "What is Prompt Engineering? Techniques, Best Practices, and Use Cases",
        "Fine-Tuning vs RAG: When to Choose Which for Large Language Models",
        "Understanding Transformers: The Architecture Behind Modern GenAI",
        "How Vector Databases Work: Similarity Search Explained Simply",
        "A Beginner's Guide to Machine Learning: Supervised vs Unsupervised Learning",
        "Building Your First LLM Agent: Frameworks, Tools, and Best Practices",
        "Deep Learning Projects that Will Make Your Portfolio Stand Out",
        "Feature Engineering for Machine Learning: Practical Python Techniques",
        "What is Data-Centric AI and Why is it the Future of Model Training?",
        "AI Model Serving: Deploying Models at Scale with Triton and FastAPI",
        "Demystifying the Attention Mechanism: What is an Attention Head?",
        "What is Fine-Tuning? A Practical Guide to Customizing Pre-trained Models",
        "Top 10 Machine Learning Algorithms Every SDE Candidate Should Know",
        "Top CNN Pre-trained Models for Computer Vision: ResNet, VGG, and YOLO",
        "Attention Is All You Need: A Friendly Walkthrough of the Transformer Paper",
        "Introduction to Natural Language Processing (NLP): From Tokenization to Embeddings",
        "What is Parameter-Efficient Fine-Tuning (PEFT)? LoRA and QLoRA Explained"
    ],
    "Developer Technology": [
        "Docker and Containerization Basics for College Students",
        "What is an API? The Complete Beginner's Guide to Web Services",
        "How Frontend and Backend Connection Actually Works under the Hood",
        "Top React Hooks Every Modern Web Developer Must Master",
        "What is a CI/CD Pipeline? Streamlining Your Tech Deployments",
        "Understanding REST APIs vs GraphQL vs gRPC: When to Use Which",
        "Understanding Blockchain Basics: How Blocks, Hashes, and Consensus Work",
        "Solana vs Ethereum: A Technical Comparison of Smart Contract Architectures",
        "What is the OWASP Top 10? Understanding the Most Critical Web Vulnerabilities",
        "How SQL Injection Works: Examples, Impact, and Mitigation Strategies",
        "Understanding Database Normalization: 1NF, 2NF, 3NF, and BCNF Explained",
        "ACID Properties in DBMS: How Databases Guarantee Transaction Reliability",
        "Introduction to Database Sharding and Replication for System Design",
        "How Git Version Control Works Behind the Scenes: A Visual Guide",
        "Understanding HTTPS and SSL/TLS: How Web Security Works"
    ]
}


def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Initializes the SQLite database and seeds the categories table with
    pending queue records. Also handles schema migrations dynamically.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create the topics table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            title TEXT,
            status TEXT NOT NULL CHECK(status IN ('pending', 'in_progress', 'published')),
            output_filename TEXT,
            quality_score REAL,
            word_count INTEGER,
            trace_id TEXT,
            created_at TEXT NOT NULL,
            completed_at TEXT,
            markdown_content TEXT,
            metadata_json TEXT,
            approved TEXT DEFAULT 'no' CHECK(approved IN ('yes', 'no'))
        )
    """)
    conn.commit()

    # Safe dynamic column migrations for existing databases
    for col_name, col_def in [
        ("markdown_content", "TEXT"),
        ("metadata_json", "TEXT"),
        ("approved", "TEXT DEFAULT 'no' CHECK(approved IN ('yes', 'no'))")
    ]:
        try:
            cursor.execute(f"ALTER TABLE topics ADD COLUMN {col_name} {col_def}")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists

    # Check if we have seeded categories. If not, seed one row per category.
    cursor.execute("SELECT COUNT(*) FROM topics")
    count = cursor.fetchone()[0]
    if count == 0:
        now_str = datetime.now().isoformat()
        for category in config.CATEGORIES:
            cursor.execute(
                "INSERT INTO topics (category, title, status, created_at) VALUES (?, NULL, 'pending', ?)",
                (category, now_str)
            )
        conn.commit()
    conn.close()


def get_next_category() -> tuple:
    """
    Selects the next category to generate for using seasonal weighting,
    boosted by a dynamic starvation/aging multiplier for categories that 
    have not been selected recently.
    
    Returns:
        tuple: (selected_category, list_of_example_patterns)
    """
    init_db()  # Ensure database and seeds exist
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get the max ID in the topics table to determine current run progress
    cursor.execute("SELECT MAX(id) FROM topics")
    max_id_row = cursor.fetchone()
    max_id = max_id_row[0] if max_id_row and max_id_row[0] is not None else 0
    
    # Get the last selected ID for each category (status: in_progress or published)
    cursor.execute(
        "SELECT category, MAX(id) as last_id FROM topics "
        "WHERE status IN ('in_progress', 'published') "
        "GROUP BY category"
    )
    last_selected = {row['category']: row['last_id'] for row in cursor.fetchall()}
    conn.close()
    
    current_month = datetime.now().month
    weights = {}
    
    for category in config.CATEGORIES:
        # Base weight
        weight = getattr(config, "BASE_WEIGHTS", {}).get(category, 1.0)
        
        # Apply seasonal boosts if active
        for month_range, boosts in config.SEASONAL_WEIGHTS.items():
            if month_range[0] <= current_month <= month_range[1]:
                if category in boosts:
                    weight *= boosts[category]
                    
        # Apply starvation/aging boost:
        # D = number of rows created since this category was last selected.
        # If never selected, runs_since is equal to max_id (so its weight continues to age).
        last_id = last_selected.get(category, 0)
        runs_since = max_id - last_id
        
        # Starvation age multiplier: increases category weight by 20% for every run it has been skipped
        age_multiplier = 1.0 + (runs_since * 0.2)
        weight *= age_multiplier
        
        weights[category] = weight

    # Choose category randomly weighted by their dynamically adjusted values
    categories_list = list(weights.keys())
    weights_list = list(weights.values())
    selected_category = random.choices(categories_list, weights=weights_list, k=1)[0]
    
    # Fetch title patterns
    patterns = EXAMPLE_TITLE_PATTERNS.get(selected_category, [])
    # Replace {year} with current year
    current_year = datetime.now().year
    processed_patterns = [p.replace("{year}", str(current_year)) for p in patterns]
    
    return selected_category, processed_patterns


def mark_in_progress(trace_id: str, category: str, title: str):
    """
    Transitions a pending category record to in_progress and records the generated title.
    If no pending record exists, inserts a new in-progress record.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    
    # Try to find a pending row for this category
    cursor.execute(
        "SELECT id FROM topics WHERE category = ? AND status = 'pending' LIMIT 1",
        (category,)
    )
    row = cursor.fetchone()
    
    if row:
        cursor.execute(
            """
            UPDATE topics 
            SET title = ?, status = 'in_progress', trace_id = ?, created_at = ?
            WHERE id = ?
            """,
            (title, trace_id, now_str, row['id'])
        )
    else:
        # If no pending slot exists, insert a new record
        cursor.execute(
            """
            INSERT INTO topics (category, title, status, trace_id, created_at)
            VALUES (?, ?, 'in_progress', ?, ?)
            """,
            (category, title, trace_id, now_str)
        )
    conn.commit()
    conn.close()


def mark_published(trace_id: str, filename: str, score: float, word_count: int, markdown_content: str = None, metadata_json: str = None):
    """
    Marks the in-progress topic row matching trace_id as published.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    
    cursor.execute(
        """
        UPDATE topics
        SET status = 'published', output_filename = ?, quality_score = ?, word_count = ?, completed_at = ?, markdown_content = ?, metadata_json = ?
        WHERE trace_id = ? AND status = 'in_progress'
        """,
        (filename, score, word_count, now_str, markdown_content, metadata_json, trace_id)
    )
    conn.commit()
    conn.close()


def get_recent_titles(category: str, months: int = 3) -> list:
    """
    Fetches titles for a specific category from the past few months
    that are published or in progress, to prevent duplicate topic generations
    while ignoring older or unrelated topics.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT title FROM topics WHERE status IN ('published', 'in_progress') "
        f"AND title IS NOT NULL "
        f"AND category = ? "
        f"AND created_at >= datetime('now', '-{months} month')",
        (category,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [row['title'] for row in rows]
