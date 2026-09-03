import random
from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate
from providers.llm_factory import get_llm

TITLE_STYLES = [
    "Provocative Question: Formulate the title as an intriguing, analytical question (e.g., 'Is Docker Still Mandatory for SDE Freshers in {year}?').",
    "Side-by-Side Comparison: Frame as a direct X vs Y comparison (e.g., 'FastAPI vs Spring Boot: Which Framework Secures Better Placement Offers in {year}?').",
    "Myth vs Reality: Frame as debunking a common misconception (e.g., 'The Myth of 100+ LeetCode Solved: What Top Tech Companies Actually Test').",
    "Practical Blueprint: Frame as a step-by-step roadmap or strategic blueprint (e.g., 'From Zero to Cloud Engineer: A 4-Stage Preparation Blueprint').",
    "Hard Truth / Lessons: Frame as an honest analysis of mistakes or realities (e.g., '5 Architectural Mistakes Freshers Make in Backend Projects').",
    "Deep-Dive Technical Mechanism: Frame as an insider explanation of how a system works under the hood (e.g., 'How Vector Databases Actually Process Similarity Search at Scale').",
    "Market & Hiring Outlook: Frame as an analytical breakdown of hiring standards and salary trends (e.g., 'AI Engineer Hiring Bar in {year}: What Top Tech Firms Require').",
    "Strategic Decision Guide: Frame as a decision-making framework (e.g., 'When to Use SQL vs NoSQL in SDE System Design Interviews')."
]

def generate_blog_title(category: str, example_patterns: list, existing_titles: list = None, rejected_titles: list = None) -> str:
    """
    Generates a new, highly specific blog title for the given category using the small model tier.
    The title must be placement-prep specific and must pass the specificity check (no generic exam prep).
    """
    current_year = datetime.now().year
    
    # Randomly select a structural title style for maximum headline diversity
    selected_style = random.choice(TITLE_STYLES).format(year=current_year)
    
    # Format patterns for display in prompt
    patterns_str = "\n".join([f"- {p}" for p in example_patterns])
    
    # Format existing titles if any
    existing_str = ""
    if existing_titles:
        existing_str = "EXISTING TITLES IN DATABASE (DO NOT GENERATE THESE OR COVERS OF THESE SAME TOPICS/TECH):\n" + "\n".join([f"- {t}" for t in existing_titles]) + "\n\n"
        
    # Format rejected titles if any
    rejected_str = ""
    if rejected_titles:
        rejected_str = "PREVIOUSLY REJECTED TITLES (DO NOT GENERATE THESE OR ANYTHING HIGHLY SIMILAR):\n" + "\n".join([f"- {t}" for t in rejected_titles]) + "\n\n"
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are an expert editorial blog title generator.\n\n"

            "Generate EXACTLY ONE high-quality blog title.\n\n"

            "TARGET STRUCTURAL STYLE (You MUST follow this headline style format):\n"
            "{target_style}\n\n"

            "RULES:\n\n"

            "1. Output ONLY the title.\n"
            "No quotes, markdown, numbering, or explanations.\n\n"

            "2. The title must be specific and clearly describe the topic.\n"
            "Avoid vague or generic titles.\n\n"

            "3. Keep titles tight and easy to scan.\n"
            "Avoid overly long, dense, or double-colon titles. Keep the headline rhythm strong and punchy.\n\n"

            "4. Avoid 'Academic Paper' phrasing.\n"
            "Do NOT use research-oriented prefixes like 'Understanding the Impact of...', 'Understanding the Trade-offs Between...', or 'An Analysis of...'. Instead, make them conversational, editorial, and curiosity-driven.\n\n"

            "5. Add curiosity and a clear payoff.\n"
            "Explain 'why this matters' or add a hook. Keep it professional, believable, and editorial. Do NOT make titles over-dramatic or sensationalist. Avoid cheap hype.\n\n"

            "6. Include the current year ({year}) only when useful.\n\n"

            "7. Avoid fake personal experience titles like 'I Tried...', 'My Experience...', or 'How I Cracked...'.\n\n"

            "8. The title must be different from rejected titles.\n"
            "If previously rejected titles are provided, do NOT write about the same specific sub-topic or technology.\n\n"

            "9. The title MUST be focused on Software Engineering (SDE), Developer Tech, Cloud, DevOps, Systems, Data, Mobile/Web Dev, or Cybersecurity.\n"
            "Do NOT write about non-developer business/management tech.\n\n"

            "GOOD TITLES:\n"
            "- punchy & easy to scan\n"
            "- specific & searchable\n"
            "- high curiosity/believable payoff\n"
            "- realistic & useful\n\n"

            "BAD TITLES:\n"
            "- academic/dry research paper tone\n"
            "- over-dramatic/aggressive clickbait\n"
            "- vague/generic\n"
            "- repetitive structure"
        )),
        ("user", (
            "Category: {category}\n"
            "Target Style Directive: {target_style}\n\n"
            "Reference Patterns for this Category:\n"
            "{patterns}\n\n"
            "{existing_titles}"
            "{rejected_titles}"
            "Generate the title now:"
        ))
    ])
    
    try:
        llm = get_llm(tier="small", temperature=0.7)
        chain = prompt | llm
        
        response = chain.invoke({
            "category": category,
            "target_style": selected_style,
            "patterns": patterns_str,
            "year": current_year,
            "existing_titles": existing_str,
            "rejected_titles": rejected_str
        })
        
        title = response.content.strip()
        
        # Strip markdown bold formatting (**), quotes, and backticks
        title = title.strip("*'\"`").strip()
        if title.startswith('"') and title.endswith('"'):
            title = title[1:-1].strip()
        if title.startswith("'") and title.endswith("'"):
            title = title[1:-1].strip()
        title = title.strip("*'\"`").strip()
            
        return title
    except Exception as e:
        print(f"Warning: Title generator LLM timed out or failed ({e}). Falling back to pattern generation.")
        if example_patterns:
            chosen = random.choice(example_patterns)
            try:
                return chosen.format(year=current_year)
            except Exception:
                return chosen
        return f"{category} Roadmap: Strategic Guide for {current_year}"
