import os
from dotenv import load_dotenv

# Load environmental variables from .env if present
load_dotenv()

LLM_PROVIDER = "openrouter"

MODEL_TIERS = {
    "openrouter": {
        "small": "deepseek/deepseek-v4-flash",
        "medium": "deepseek/deepseek-v4-flash",
        "large": "meta-llama/llama-4-scout",
    }
}

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "")

QUALITY_GATE_THRESHOLD = 7.5

BANNED_PHRASES = [
    "In today's fast-paced world",
    "In today's rapidly evolving",
    "In today's competitive job market",
    "In today's hiring landscape",
    "At this point, you should have",
    "By following these best practices",
    "It's important to note that",
    "In conclusion",
    "Let's dive in",
    "Without further ado",
    "In this comprehensive guide",
    "As we all know",
    "It goes without saying",
    "At the end of the day",
    "The bottom line is",
    "In the ever-changing landscape",
    "Stay ahead of the curve",
    "Take your skills to the next level",
    "Happy coding",
    "So what are you waiting for",
    "It's worth noting that",
    "In the realm of",
    "Leveraging the power of",
    "Unlock your potential",
    "Game-changer",
    "Dive deep into",
    "Crucial role",
    "Delve into",
    "Testament to",
    "Beacon of",
    "Fostering a culture of"
]
QUALITY_EARLY_EXIT_THRESHOLD = 8.5

RETRY_CAPS = {
    "title_dedup": 3,
    "quality_rewriter": 1,
}

CATEGORIES = [
    "Job Role and Career Trends",
    "Resume Writing",
    "Placement Roadmaps",
    "Comparison Articles",
    "AI Technology",
    "Developer Technology"
]

BASE_WEIGHTS = {
    "Job Role and Career Trends": 1.0,
    "Resume Writing": 1.0,
    "Placement Roadmaps": 1.0,
    "Comparison Articles": 1.0,
    "AI Technology": 1.0,
    "Developer Technology": 1.0
}

WORD_COUNT_MINIMUMS = {
    "Job Role and Career Trends": 1600,
    "Resume Writing": 1600,
    "Placement Roadmaps": 1800,
    "Comparison Articles": 1800,
    "AI Technology": 1800,
    "Developer Technology": 1800
}

PROMPT_VERSION = 1

BLOG_FORMATS = {
    "deep_dive": {
        "description": "Long-form technical analysis with prose-heavy sections",
        "section_range": (5, 7),
        "word_range": (2000, 2600),
    },
    "listicle": {
        "description": "Numbered items with short intros — 'Top N' style",
        "section_range": (4, 6),
        "word_range": (1600, 2200),
    },
    "step_by_step": {
        "description": "Sequential tutorial or roadmap with numbered steps",
        "section_range": (5, 8),
        "word_range": (2000, 2600),
    },
    "comparison": {
        "description": "Side-by-side analysis with a verdict section",
        "section_range": (4, 6),
        "word_range": (1800, 2400),
    },
    "qa_interview": {
        "description": "Question-answer pairs for interview prep",
        "section_range": (4, 5),
        "word_range": (1800, 2200),
    },
    "myth_buster": {
        "description": "Myth vs Reality format — debunks misconceptions",
        "section_range": (4, 6),
        "word_range": (1600, 2000),
    },
}

WRITING_PERSONAS = {
    "authoritative_expert": "Write as a seasoned industry expert. Use precise technical terminology, cite specifics, and present definitive analysis. Confident declarative tone.",
    "helpful_mentor": "Write as a supportive senior guiding a junior. Use analogies, define jargon on first use, and add encouraging 'here's the key insight' moments.",
    "analytical_reviewer": "Write as a neutral technical reviewer. Present both sides fairly, use data-driven comparisons, and defer to evidence over opinion.",
    "practical_coach": "Write as a hands-on coding coach. Use directive voice ('Do X. Then Y. Avoid Z.'), include concrete steps, and focus on what to DO not just what to KNOW.",
    "storyteller": "Write as an engaging technical narrator. Open with real-world scenarios or engineering incidents, use compelling prose, and ground concepts in practical engineering stories.",
    "skeptical_engineer": "Write as a critical senior staff engineer. Question hype, focus on edge cases, operational overhead, failure modes, and real production trade-offs.",
    "data_journalist": "Write as a data-focused tech analyst. Emphasize metrics, benchmarks, survey statistics, and objective quantitative comparisons."
}




# Image Generation Settings
IMAGE_API_URL = os.getenv("IMAGE_API_URL", "")  # Empty string activates stub mode
IMAGE_API_KEY = os.getenv("IMAGE_API_KEY", "")
IMAGE_COUNT_PER_BLOG = 3  # 2-3 section images + 1 thumbnail
IMAGE_STYLES = ["technical_diagram", "conceptual_illustration", "data_visualization", "hero_banner"]
