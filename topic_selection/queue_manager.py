import random
import os
from datetime import datetime
import config
from . import mongo_db

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


def init_db():
    """
    Initializes the MongoDB database and creates indexes.
    Replaces MongoDB initialization.
    """
    mongo_db.init_db()


def get_next_category() -> tuple:
    """
    Selects the next category to generate for using seasonal weighting,
    boosted by a dynamic starvation/aging multiplier for categories that 
    have not been selected recently.
    
    Returns:
        tuple: (selected_category, list_of_example_patterns)
    """
    init_db()  # Ensure database and seeds exist
    
    # Get the max ID (document count) in the topics collection
    max_id = mongo_db.get_next_category_max_id()
    
    # Get the last selected ID for each category
    last_selected = mongo_db.get_last_selected_categories()
    
    # HARD FLOOR: If any category has NEVER been selected (0 blogs),
    # and we've generated at least len(CATEGORIES) blogs total,
    # force-select the most starved category.
    if max_id >= len(config.CATEGORIES):
        never_selected = [
            cat for cat in config.CATEGORIES 
            if cat not in last_selected or last_selected[cat] == 0
        ]
        if never_selected:
            selected_category = never_selected[0]
            patterns = EXAMPLE_TITLE_PATTERNS.get(selected_category, [])
            current_year = datetime.now().year
            processed_patterns = [p.replace("{year}", str(current_year)) for p in patterns]
            print(f"[HARD FLOOR] Category '{selected_category}' has 0 blogs -- force-selecting.")
            return selected_category, processed_patterns
            
    weights = {}
    
    for category in config.CATEGORIES:
        # Base weight
        weight = config.BASE_WEIGHTS.get(category, 1.0)
                    
        # Starvation/aging boost: increases weight by 20% for every run this category was skipped
        last_id = last_selected.get(category, 0)
        runs_since = max_id - last_id
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
    mongo_db.mark_in_progress(trace_id, category, title)


def mark_published(trace_id: str, filename: str, score: float, word_count: int, markdown_content: str = None, metadata_json: str = None):
    """
    Marks the in-progress topic row matching trace_id as published.
    """
    mongo_db.mark_published(trace_id, filename, score, word_count, markdown_content, metadata_json)


def get_recent_formats(n: int = 8) -> list:
    """Get the blog_format of the last N generated blogs from JSON sidecars."""
    import glob
    _project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(_project_root, "output")
    
    formats = []
    json_files = sorted(
        glob.glob(os.path.join(output_dir, "*.json")),
        key=os.path.getmtime, reverse=True
    )
    for jf in json_files:
        if "-trace.json" in jf or "module_" in jf:
            continue
        try:
            with open(jf, "r", encoding="utf-8") as f:
                data = json.load(f)
            fmt = data.get("blog_format")
            if fmt:
                formats.append(fmt)
            if len(formats) >= n:
                break
        except Exception:
            pass
    return formats


def get_all_recent_titles(months: int = 3) -> list:
    """Fetches titles across ALL categories for cross-category dedup."""
    titles = set(mongo_db.get_all_recent_titles(months))
    
    try:
        import glob
        _project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(_project_root, "output")
        for jf in glob.glob(os.path.join(output_dir, "*.json")):
            if jf.endswith("-trace.json") or "module_" in jf:
                continue
            try:
                with open(jf, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("title"):
                        titles.add(data["title"])
            except Exception:
                pass
    except Exception:
        pass
    return list(titles)


def get_recent_titles(category: str, months: int = 3) -> list:
    """
    Fetches titles for a specific category from the past few months
    from MongoDB and local /output files to prevent duplicate topic generation.
    """
    titles = set(mongo_db.get_recent_titles(category, months))
    
    try:
        import glob
        _project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(_project_root, "output")
        json_files = glob.glob(os.path.join(output_dir, "*.json"))
        for jf in json_files:
            if jf.endswith("-trace.json") or "module_" in jf:
                continue
            try:
                with open(jf, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("category") == category and data.get("title"):
                        titles.add(data["title"])
            except Exception:
                pass
    except Exception:
        pass
        
    return list(titles)
