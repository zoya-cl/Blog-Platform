from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate
from providers.llm_factory import get_llm

def generate_blog_title(category: str, example_patterns: list, existing_titles: list = None, rejected_titles: list = None) -> str:
    """
    Generates a new, highly specific blog title for the given category using the small model tier.
    The title must be placement-prep specific and must pass the specificity check (no generic exam prep).
    """
    current_year = datetime.now().year
    
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

            "RULES:\n\n"

            "1. Output ONLY the title.\n"
            "No quotes, markdown, numbering, or explanations.\n\n"

            "2. The title must be specific and clearly describe the topic.\n"
            "Avoid vague or generic titles.\n\n"

            "3. Keep titles tight and easy to scan.\n"
            "Avoid overly long, dense, or double-colon titles (e.g., instead of 'Cloud-Native Architecture vs Monolithic Design: A Comparison of Scalability and Maintenance Costs in 2026', use 'Monolith vs Cloud-Native: The Real Cost of Scaling in 2026'). Keep the headline rhythm strong and punchy.\n\n"

            "4. Avoid 'Academic Paper' phrasing.\n"
            "Do NOT use research-oriented prefixes like 'Understanding the Impact of...', 'Understanding the Trade-offs Between...', or 'An Analysis of...'. Instead, make them conversational, editorial, and curiosity-driven.\n\n"

            "5. Add curiosity and a clear payoff.\n"
            "Explain 'why this matters' or add a hook. Keep it professional, believable, and editorial. Do NOT make titles over-dramatic, aggressive, or sensationalist (e.g., instead of 'Why Your Favorite LeetCode Solutions Are Actually Wrong', use 'Why Many Popular LeetCode Solutions Break Down in Real Interviews'). Avoid cheap, Twitter-thread-style hype.\n\n"

            "6. Increase Title Structure Diversity.\n"
            "Do NOT repeat the same patterns (like 'Complete Guide...', 'Crafting...', or 'Understanding...'). Avoid repeating the same conversational intensifiers like 'Actually', 'Really', or 'Secretly'. Vary the format using styles like:\n"
            "- Why...\n"
            "- What Actually...\n"
            "- X vs Y...\n"
            "- Common Mistakes...\n"
            "- Can You...\n"
            "- Inside...\n"
            "- The Biggest Myth...\n"
            "- How Companies...\n\n"

            "7. Include the current year ({year}) only when useful.\n\n"

            "8. Avoid fake personal experience titles like:\n"
            "- I Tried...\n"
            "- My Experience...\n"
            "- How I Cracked...\n\n"

            "9. The title must be different from rejected titles.\n"
            "If previously rejected titles are provided, do NOT write about the same specific sub-topic or technology. For example, if a title about 'Dynamic Programming' was rejected, choose a completely different technical sub-topic (like Graphs, Bit Manipulation, or SQL) instead of just rewording the DP title.\n\n"

            "10. The title MUST be focused on Software Engineering (SDE), Developer Tech, Cloud, DevOps, Systems, Data, Mobile/Web Dev, or Cybersecurity.\n"
            "Do NOT write about non-developer business/management tech (e.g., SAP FICO, Salesforce Admin, HR, MBA). These are strictly off-topic.\n\n"

            "11. Category-Specific Formatting Exceptions:\n"
            "- For 'Interview Question Collections' category, KEEP IT SIMPLER. Use direct list-based titles (e.g., 'Top 30 React & JavaScript Interview Questions' or 'Top 50 Core Java Interview Questions'). Do NOT make them complex, editorial, or narrative.\n"
            "- For 'Can I Get Placed With' category, KEEP IT SIMPLER. Use direct, search-friendly question formats (e.g., 'Can I Get a DevOps Job as a Fresher?' or 'Can I Get Placed Without Internship Experience?'). Do NOT use complex narrative or curiosity hooks.\n\n"

            "GOOD TITLES:\n"
            "- punchy & easy to scan\n"
            "- specific & searchable\n"
            "- high curiosity/believable payoff\n"
            "- realistic & useful\n\n"

            "BAD TITLES:\n"
            "- academic/dry research paper tone\n"
            "- over-dramatic/aggressive clickbait (e.g., 'Why Your Favorite LeetCode Solutions Are Actually Wrong')\n"
            "- repetitive word patterns (e.g., overusing 'Actually', 'Really')\n"
            "- overly long/dense\n"
            "- vague/generic\n"
            "- repetitive structure"
        )),
        ("user", (
            "Category: {category}\n"
            "Reference Patterns for this Category:\n"
            "{patterns}\n\n"
            "{existing_titles}"
            "{rejected_titles}"
            "Generate the title now:"
        ))
    ])
    
    llm = get_llm(tier="small", temperature=0.2)
    chain = prompt | llm
    
    response = chain.invoke({
        "category": category,
        "patterns": patterns_str,
        "year": current_year,
        "existing_titles": existing_str,
        "rejected_titles": rejected_str
    })
    
    title = response.content.strip()
    
    # Strip any leading/trailing quotes that LLMs sometimes add anyway
    if title.startswith('"') and title.endswith('"'):
        title = title[1:-1].strip()
    if title.startswith("'") and title.endswith("'"):
        title = title[1:-1].strip()
        
    return title
