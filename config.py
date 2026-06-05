import os
from dotenv import load_dotenv

# Load environmental variables from .env if present
load_dotenv()

# LLM Provider: "nim", "groq", or "ollama"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "nim").lower()

# Model tier mapping per provider
MODEL_TIERS = {
    "nim": {
        "small": "meta/llama-3.1-8b-instruct",
        "medium": "meta/llama-3.1-70b-instruct",
        "large": "meta/llama-3.3-70b-instruct",
    },
    "groq": {
        "small": "llama-3.1-8b-instant",
        "medium": "llama-3.3-70b-versatile",
        "large": "llama-3.3-70b-versatile",
    },
    "ollama": {
        "small": "llama3.1:8b",
        "medium": "llama3.1:70b",
        "large": "llama3.1:70b",
    },
    "openrouter": {
        "small": "meta-llama/llama-3.1-8b-instruct",
        "medium": "meta-llama/llama-3.3-70b-instruct",
        "large": "meta-llama/llama-3.3-70b-instruct",
    }
}

# API configuration
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "") or os.getenv("NIM_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")

# Token budgets per node
TOKEN_BUDGETS = {
    "intake": {"input": 500, "output": 300},
    "planner": {"input": 2000, "output": 1200},
    "writer": {"input": 2500, "output": 700},
    "hallucination_detector": {"input": 5000, "output": 600},
    "quality_node": {"input": 5000, "output": 500},
    "rewriter": {"input": 3000, "output": 700},
    "seo_auditor": {"input": 4000, "output": 400},
}

# Quality gate settings
QUALITY_GATE_THRESHOLD = 7.0

# Retry caps
RETRY_CAPS = {
    "title_dedup": 3,
    "hallucination_rewriter": 2,
    "quality_rewriter": 2,
    "seo_patcher": 2,
}

# Retrieval depth limits (unioned for all categories)
RETRIEVAL_ITERATION_CAPS = {
    "standard": 8
}

# Categories definition
CATEGORIES = [
    "Job Role and Career Trends",
    "Resume Writing",
    "Placement Roadmaps",
    "Interview Question Collections",
    "DSA and Coding",
    "Comparison Articles",
    "AI Technology",
    "Developer Technology"
]

# Base weights for each category to scale their selection probability (default is 1.0)
BASE_WEIGHTS = {
    "DSA and Coding": 0.2,
    "Interview Question Collections": 0.2,
}

# Retrieval depth per category (all categories get standard equal retrieval depth)
RETRIEVAL_DEPTHS = {
    "Job Role and Career Trends": "standard",
    "Resume Writing": "standard",
    "Placement Roadmaps": "standard",
    "Interview Question Collections": "standard",
    "DSA and Coding": "standard",
    "Comparison Articles": "standard",
    "AI Technology": "standard",
    "Developer Technology": "standard",
}

# Word count minimums per category
WORD_COUNT_MINIMUMS = {
    "Placement Roadmaps": 2200,
    "DSA and Coding": 1800,
    "Interview Question Collections": 1800,
    "Job Role and Career Trends": 1600,
    "Resume Writing": 1600,
    "Comparison Articles": 1600,
    "AI Technology": 2000,
    "Developer Technology": 2000,
}

# Scraper timeout (in seconds)
SCRAPER_TIMEOUT = 10.0

# Prompt caching
PROMPT_CACHE_ENABLED = LLM_PROVIDER in ["nim", "groq"]

# Prompt versioning
PROMPT_VERSION = 1

# Seasonal weights (August through December boost)
# Mapping month range (start_month, end_month) inclusive -> {category: multiplier}
SEASONAL_WEIGHTS = {
    (8, 12): {}
}

# Image Generation Pipeline Settings
IMAGE_ENABLED = True
IMAGE_MODEL = "google/gemini-3.1-flash-image-preview"
IMAGE_BUDGET = {
    "short": 3,   # < 1200 words
    "medium": 3,  # 1200 - 2000 words
    "long": 3     # > 2000 words
}
