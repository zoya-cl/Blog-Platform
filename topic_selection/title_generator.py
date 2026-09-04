import os
import re
import random
from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate
from providers.llm_factory import get_llm

TITLE_STYLES = [
    {
        "name": "Provocative Question",
        "instruction": "Frame the title as a single sharp, analytical question that challenges a common assumption. The question must have a non-obvious answer. Keep it under 65 characters.",
        "structure": "[Challenge/question about X]?"
    },
    {
        "name": "X vs Y Showdown",
        "instruction": "Frame as a direct head-to-head comparison of two specific technologies or approaches. Lead with the two things being compared. No subtitle needed.",
        "structure": "[Tech A] vs [Tech B] — [one-line differentiator]"
    },
    {
        "name": "Contrarian Take",
        "instruction": "Challenge conventional wisdom in the category. Start with the thing everyone assumes is true, then explain why it's flawed. Do NOT use the word 'Myth'.",
        "structure": "[Thing everyone believes] — [Why it's actually wrong]"
    },
    {
        "name": "Numbered Mistakes/Lessons",
        "instruction": "List a specific count of mistakes, lessons, or architectural signals. The count must be between 3 and 7. Focus on things engineers get WRONG, not generic tips.",
        "structure": "[N] [Mistakes/Signals/Lessons] That [Specific Consequence]"
    },
    {
        "name": "How-It-Works Under the Hood",
        "instruction": "Reveal the internal mechanism of a specific technology or system. Use 'Under the Hood' or clear technical mechanisms to signal insider engineering depth. No year tag needed.",
        "structure": "How [Specific System] [Works/Processes/Handles] [Specific Thing] Under the Hood"
    },
    {
        "name": "The Hidden Cost/Trade-off",
        "instruction": "Expose a non-obvious downside, trade-off, or hidden complexity of something popular. Frame it as a realistic engineering revelation.",
        "structure": "The Hidden [Cost/Complexity/Trade-off] of [Popular Technology or Practice]"
    },
    {
        "name": "Career Decision Fork",
        "instruction": "Frame as a specific career or technology crossroads with clear trade-offs and stakes. Focus on the decision, not generic advice. Target Indian engineering freshers.",
        "structure": "[Path A] or [Path B] — [What's actually at stake]"
    },
    {
        "name": "What [Role] Really Does",
        "instruction": "Demystify a specific technical role by revealing daily realities, engineering standards, or expectations vs hype. Focus on counterintuitive aspects.",
        "structure": "What [Specific Role] [Does/Builds/Requires] in [Context]"
    }
]

OVERUSED_PATTERNS = [
    r"\d+-\w+\s+blueprint",          # "5-Step Blueprint", "6-Stage Blueprint"
    r"\d+-stage\s+",                  # "5-Stage Preparation"
    r"\d+-step\s+",                   # "5-Step Guide"
    r"the\s+ultimate\s+guide",
    r"the\s+complete\s+guide",
    r"everything\s+you\s+need\s+to\s+know",
    r"strategic\s+decision\s+guide",  # Catches repeated phrase
    r"a\s+\d+-stage\s+.*blueprint",   # Catches "A 5-Stage X Blueprint"
    r"hiring\s+bar\s+in\s+\d{4}",     # Catches "Hiring Bar in 2026"
    r"from\s+\w+\s+to\s+\w+:\s+a",   # Catches "From X to Y: A..."
]

TITLE_STOP_WORDS = {
    "a", "an", "the", "in", "of", "for", "and", "or", "to",
    "is", "vs", "your", "how", "what", "why", "which", "that",
    "are", "from", "with", "can", "do", "does", "this", "will",
    "be", "not", "its", "it", "you", "than", "more", "should"
}

EDITORIAL_FILLER_WORDS = {"actually", "really", "hidden", "secret", "surprising"}

MAX_RETRIES = 3


def extract_title_keywords(title: str) -> set:
    """Extract meaningful keywords from a title for semantic similarity comparison."""
    words = re.findall(r'[a-z]+', title.lower())
    return set(w for w in words if w not in TITLE_STOP_WORDS and len(w) > 2)


def is_structurally_repetitive(title: str, existing_titles: list) -> bool:
    """Check if the title matches an overused structural pattern already present in existing titles."""
    title_lower = title.lower()
    for pattern in OVERUSED_PATTERNS:
        if re.search(pattern, title_lower):
            for existing in (existing_titles or []):
                if re.search(pattern, existing.lower()):
                    return True
    return False


def run_quality_gates(title: str, existing_titles: list) -> str | None:
    """
    Run deterministic quality checks on a generated title candidate.
    Returns a rejection reason string if failing a gate, or None if all gates pass.
    """
    title_lower = title.lower()
    
    # Gate 1: Length — reject if > 80 chars
    if len(title) > 80:
        return f"Too long ({len(title)} chars, max 80)"
    
    # Gate 2: Structural repetition — check OVERUSED_PATTERNS against existing
    if is_structurally_repetitive(title, existing_titles or []):
        return "Matches overused structural pattern in existing titles"
    
    # Gate 3: Semantic similarity — Jaccard keyword overlap > 0.25 with any recent title
    title_keywords = extract_title_keywords(title)
    if title_keywords:
        for existing in (existing_titles or []):
            existing_keywords = extract_title_keywords(existing)
            overlap = title_keywords & existing_keywords
            union = title_keywords | existing_keywords
            if union and len(overlap) / len(union) > 0.25:
                return f"Too similar to existing: '{existing}' (shared: {sorted(overlap)})"
    
    # Gate 4: Year proportion — if >40% of last 10 titles have year, reject year-tagged titles
    if re.search(r'\b20\d{2}\b', title):
        recent = (existing_titles or [])[-10:]
        year_count = sum(1 for t in recent if re.search(r'\b20\d{2}\b', t))
        if recent and year_count / len(recent) > 0.4:
            return f"Year tag overused ({year_count}/{len(recent)} recent titles have year)"
    
    # Gate 5: Colon proportion — if >60% of last 10 titles have colons, reject colon titles
    if ":" in title:
        recent = (existing_titles or [])[-10:]
        colon_count = sum(1 for t in recent if ":" in t)
        if recent and colon_count / len(recent) > 0.6:
            return f"Colon structure overused ({colon_count}/{len(recent)} recent titles)"
    
    # Gate 6: Banned prefixes that survived stripping
    if title_lower.startswith(("myth:", "myth vs")):
        return "Banned prefix 'Myth:' survived stripping"

    # Gate 7: Editorial filler word diversity — if >30% of last 10 titles have the same filler word, reject
    recent = (existing_titles or [])[-10:]
    if recent:
        for filler in EDITORIAL_FILLER_WORDS:
            if filler in title_lower:
                filler_count = sum(1 for t in recent if filler in t.lower())
                if filler_count / len(recent) > 0.3:
                    return f"Filler word '{filler}' overused ({filler_count}/{len(recent)} recent titles)"
    
    return None  # All gates passed


def generate_blog_title(category: str, category_guide: dict = None, existing_titles: list = None, rejected_titles: list = None) -> str:
    """
    Generates a new, punchy, non-repetitive blog title for the given category.
    Enforces deterministic quality gates and structural diversity.
    """
    current_year = datetime.now().year
    
    # Pick an abstract structural headline style
    selected_style = random.choice(TITLE_STYLES)
    
    # Build covered topics summary using keywords to avoid LLM copying full titles
    covered_topics = ""
    if existing_titles:
        topic_keywords = []
        for t in existing_titles[-25:]:
            kws = extract_title_keywords(t)
            if kws:
                topic_keywords.append(", ".join(sorted(kws)[:5]))
        if topic_keywords:
            covered_topics = (
                "ALREADY COVERED TOPIC THEMES (do NOT write about these subjects again):\n"
                + "\n".join(f"- {k}" for k in topic_keywords)
                + "\n\n"
            )
            
    # Format rejected titles if any
    rejected_str = ""
    if rejected_titles:
        rejected_str = (
            "PREVIOUSLY REJECTED TITLES (these were rejected for being too long, "
            "structurally repetitive, or too similar to existing blogs — DO NOT generate anything similar):\n"
            + "\n".join(f"- {t}" for t in rejected_titles)
            + "\n\n"
        )
    
    # Build category context from guide
    guide = category_guide if isinstance(category_guide, dict) else {}
    topic_areas_str = ", ".join(guide.get("topic_areas", [])) if guide.get("topic_areas") else "Core engineering topics, practical trade-offs, architecture, placements"
    off_limits_str = guide.get("off_limits", "Generic motivational advice, non-tech content")
    description_str = guide.get("description", category)
    
    system_prompt = (
        "You are a senior tech blog editor crafting ONE title for an Indian engineering career and tech blog.\n"
        "Audience: CS students, freshers, and early-career software engineers preparing for placements and roles.\n\n"

        "TARGET HEADLINE STRUCTURE TO FOLLOW:\n"
        f"Style: {selected_style['name']}\n"
        f"Instruction: {selected_style['instruction']}\n"
        f"Target Shape: {selected_style['structure']}\n\n"

        "HARD EDITORIAL RULES:\n"
        "1. Output ONLY the title. No quotes, markdown, asterisks, numbering, or explanations.\n"
        "2. MAXIMUM 75 characters. Shorter and punchier is better. Trim ruthlessly.\n"
        "3. Must be specific — name a concrete technology, protocol, tool, role, or architecture.\n"
        "4. Do NOT start titles with 'Myth:', 'Myth vs Reality:', or 'Understanding'.\n"
        "5. Do NOT use the phrases 'Strategic Decision Guide', 'Blueprint', or 'Everything You Need to Know'.\n"
        f"6. Include the year '{current_year}' ONLY if the topic is genuinely time-sensitive (e.g. salary benchmarks, hiring market trends). Most technical architecture or fundamental topics do NOT need a year tag.\n"
        "7. Avoid dry academic paper phrasing ('An Analysis of...', 'Exploring the Trade-offs of...').\n"
        "8. Avoid fake personal framing ('I Tried...', 'My Experience...').\n"
        "9. Choose a FRESH, distinctive angle that is not listed in the already covered topics.\n"
    )
    
    user_prompt = (
        f"Category: {category}\n"
        f"Category Scope: {description_str}\n"
        f"Topic Areas to Explore: {topic_areas_str}\n"
        f"Off-Limits: {off_limits_str}\n\n"
        f"{covered_topics}"
        f"{rejected_str}"
        "Generate the title now:"
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", user_prompt)
    ])
    
    try:
        llm = get_llm(tier="small", temperature=0.7)
        chain = prompt | llm
        
        response = chain.invoke({})
        title = response.content.strip()
        
        # --- Post-processing pipeline (ALL steps run before returning) ---
        
        # Step 1: Strip markdown bold, quotes, and backticks
        title = title.strip("*'\"`").strip()
        if title.startswith('"') and title.endswith('"'):
            title = title[1:-1].strip()
        if title.startswith("'") and title.endswith("'"):
            title = title[1:-1].strip()
        title = title.strip("*'\"`").strip()
        
        # Step 2: Strip banned prefixes that LLM may have generated
        if title.lower().startswith("myth:"):
            title = title[5:].strip().lstrip("–—-").strip()
            if title:
                title = title[0].upper() + title[1:]
        elif title.lower().startswith("myth vs reality:"):
            title = title[16:].strip().lstrip("–—-").strip()
            if title:
                title = title[0].upper() + title[1:]
        elif title.lower().startswith("myth vs."):
            title = title[8:].strip().lstrip("–—-").strip()
            if title:
                title = title[0].upper() + title[1:]
        title = title.strip("*'\"`").strip()
        
        # Step 3: Run deterministic quality gates
        rejection_reason = run_quality_gates(title, existing_titles)
        if rejection_reason:
            current_rejected = (rejected_titles or []) + [title]
            print(f"  [TITLE REJECTED: {rejection_reason}] '{title}'")
            if len(current_rejected) <= MAX_RETRIES:
                print(f"  --> Regenerating title (attempt {len(current_rejected)} of {MAX_RETRIES})...")
                return generate_blog_title(
                    category=category,
                    category_guide=category_guide,
                    existing_titles=existing_titles,
                    rejected_titles=current_rejected
                )
            else:
                print(f"  [MAX RETRIES REACHED] Accepting candidate title after {MAX_RETRIES} attempts.")
        
        return title
        
    except Exception as e:
        print(f"Warning: Title generator LLM timed out or failed ({e}). Falling back to fallback generator.")
        return f"Modern {category} Strategies for Software Engineers"
