import re
from rapidfuzz import fuzz

STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "about", "above", "after", "along", "amid", "among", "as", "at", 
    "by", "for", "from", "in", "into", "like", "of", "off", "on", "onto", "out", "over", "through", "to", 
    "under", "up", "with", "within", "without", "is", "are", "was", "were", "be", "been", "being", "have", 
    "has", "had", "do", "does", "did", "this", "that", "these", "those", "your", "my", "their", "our", "his", "her"
}

def clean_title_words(title: str) -> set:
    # Clean and split into lowercase words, returning non-stopwords
    words = re.findall(r"\b[a-z0-9']+\b", title.lower())
    return {w for w in words if w not in STOP_WORDS and len(w) > 2}

def is_title_unique(new_title: str, existing_titles: list, category: str = None) -> bool:
    """
    Compares the generated title with all existing published and in-progress titles.
    Uses RapidFuzz ratio, token_sort_ratio, token_set_ratio, and keyword overlap check.
    If any score exceeds the safety thresholds, returns False (duplicate).
    """
    if not existing_titles:
        return True
        
    new_title_lower = new_title.lower().strip()
    new_keywords = clean_title_words(new_title)
    
    # Categories that contain highly custom technical content where repetitions are not allowed
    content_heavy_categories = {
        "Job Role and Career Trends",
        "Resume Writing",
        "AI-Powered Prep",
        "Company Techstack",
        "AI Technology",
        "Developer Technology"
    }
    
    is_content_heavy = category is None or category in content_heavy_categories
    
    for existing in existing_titles:
        existing_lower = existing.lower().strip()
        
        # 1. Standard RapidFuzz check (case-insensitive ratio and token sort)
        ratio = fuzz.ratio(new_title_lower, existing_lower)
        token_sort_ratio = fuzz.token_sort_ratio(new_title_lower, existing_lower)
        
        # General similarity threshold (reduced from 85 to 80 for tighter dedup)
        if ratio > 80 or token_sort_ratio > 80:
            return False
            
        # 2. Advanced checks for content-heavy categories to detect conceptual overlaps
        if is_content_heavy:
            token_set_ratio = fuzz.token_set_ratio(new_title_lower, existing_lower)
            if token_set_ratio > 85:
                return False
                
            # Keyword overlap check
            existing_keywords = clean_title_words(existing)
            if new_keywords and existing_keywords:
                intersection = new_keywords & existing_keywords
                smaller_len = min(len(new_keywords), len(existing_keywords))
                overlap_pct = (len(intersection) / smaller_len) * 100
                
                # Reject if 65% or more keywords match and there is substantial overlap
                if overlap_pct >= 65.0 and len(intersection) >= 2:
                    return False
                    
    return True
