import re
from typing import List
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from providers.llm_factory import get_llm

# list of regex patterns to filter out spam, book downloads, and forum threads
BLOCKLIST_PATTERNS = [
    r"\breddit\b",
    r"\bpdf\b",
    r"\bdownload\b",
    r"\bfree\b",
    r"\bgithub\b",
    r"\bsolution manual\b",
    r"\banswer key\b",
    r"\bchegg\b",
    r"\bcourse hero\b"
]


# our seo cleaner filters keywords with a tech context. we focus on topics relevant to software
# development, tech interviews, and systems, while stripping out noise like web platform status pages
# (e.g. 'leetcode server offline') that don't match the educational nature of the blog post.
class IntentSignals(BaseModel):
    beginner: bool = Field(description="whether the query intent targets beginners")
    placement_oriented: bool = Field(description="whether the query intent targets tech interviews and job prep")
    technology_specific: List[str] = Field(description="list of specific technical software/hardware technologies, frameworks, libraries, or languages identified")
    comparison: bool = Field(description="whether the query intent compares tech options")
    freshness: bool = Field(description="whether the query intent targets recent or future trends")


class SEOCurationOutput(BaseModel):
    primary_keyword: str = Field(description="a grammatically complete search keyword representing the core intent of the blog. no commas, maximum 6 words.")
    secondary_keywords: List[str] = Field(
        description=(
            "3-5 highly relevant, technical secondary search keywords selected/adapted from raw suggestions. "
            "CRITICAL: Keywords must be specific technical terms, tools, or concepts (e.g., 'Django middleware', 'Docker multi-stage build'). "
            "Do NOT include broad, high-level abstract categories like 'Education Sector', 'Learning Platforms', 'Technology', or 'Career'."
        )
    )
    faq_candidates: List[str] = Field(description="4-6 highly relevant FAQ questions ending with a question mark")
    intent_signals: IntentSignals


def get_blocked_pattern(suggestion_string: str) -> str:
    """returns the matched pattern if the suggestion hits our blocklist, else none"""
    suggestion_lower = suggestion_string.lower().strip()
    for pattern in BLOCKLIST_PATTERNS:
        # check if the blocklist pattern matches anywhere in our suggestion
        if re.search(pattern, suggestion_lower):
            return pattern
            
    return None


def clean_and_curate_seo_data(
    title: str,
    primary_query: str,
    raw_suggestions_dict: dict,
    paa_questions: list,
    verbose: bool = True
) -> dict:
    """filters search queries using a blocklist and then uses an llm to pick the best keywords and faqs"""
    if verbose:
        print("\n[SEO Cleaner] Starting LLM-in-the-loop semantic filtering...")
        
    # first we do local filtering to remove duplicates and blocklisted spam before calling the llm
    filtered_suggestions = []
    seen_suggestions = set()
    
    for bucket_name, suggestions_list in raw_suggestions_dict.items():
        for suggestion in suggestions_list:
            suggestion_stripped = suggestion.strip()
            suggestion_lower = suggestion_stripped.lower()
            
            if not suggestion_stripped:
                continue
            if suggestion_lower in seen_suggestions:
                if verbose:
                    print(f"  [Clean] Pre-filter rejected '{suggestion_stripped}' -> Duplicate suggestion.")
                continue
                
            matched_pattern = get_blocked_pattern(suggestion_stripped)
            if matched_pattern:
                if verbose:
                    print(f"  [Clean] Pre-filter rejected '{suggestion_stripped}' -> Matched blocklist '{matched_pattern}'.")
                continue
                
            seen_suggestions.add(suggestion_lower)
            filtered_suggestions.append(suggestion_stripped)
            
    # filter the people also ask questions using the same blocklist
    filtered_paa = []
    for question in paa_questions:
        question_stripped = question.strip()
        question_lower = question_stripped.lower()
        matched_pattern = get_blocked_pattern(question_stripped)
        if matched_pattern or not question_stripped:
            continue
        filtered_paa.append(question_stripped)
        
    if verbose:
        print(f"  [Clean] Pre-filter completed. Retained {len(filtered_suggestions)} suggestions and {len(filtered_paa)} PAA questions.")

    # we use an llm here because mechanical keywords tools often drift into unrelated topics
    # (like selecting 'leetcode slow today' when writing about interview prep). the llm also
    # helps pick a natural, grammatically correct primary keyword under 6 words instead of
    # just chopping off text mid-sentence, and categorizes technical intents accurately.
    system_instructions = (
        "You are an expert tech blog SEO editor. Your job is to curate, clean, and validate search queries and questions for a blog post.\n\n"
        "INSTRUCTIONS:\n"
        "Given the blog title and a list of raw search queries and FAQ questions fetched from Google search, you must:\n"
        "1. Select a 'primary_keyword' representing the core intent. It must be grammatically complete and max 6 words with no commas.\n"
        "2. Curate 3-5 'secondary_keywords' from the suggestions. Filter out irrelevant noise (e.g. server status issues like 'leetcode slow today').\n"
        "3. Curate 4-6 'faq_candidates' ending with question marks.\n"
        "4. Classify intent signals coverage."
    )
    
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_instructions),
        ("user", (
            "Blog Title: {title}\n"
            "Normalized Query: {primary_query}\n"
            "Raw Suggestions:\n{suggestions_str}\n\n"
            "Raw PAA Questions:\n{paa_str}\n\n"
            "Generate structured output now:"
        ))
    ])
    
    # format lists into simple bullet points for the prompt
    suggestions_bulleted = "\n".join([f"- {s}" for s in filtered_suggestions])
    paa_bulleted = "\n".join([f"- {q}" for q in filtered_paa])
    
    small_llm = get_llm(tier="small", temperature=0.0)
    structured_llm = small_llm.with_structured_output(SEOCurationOutput)
    chain = prompt_template | structured_llm
    
    # safe fallback values if the llm fails or returns invalid response
    fallback_pk = primary_query
    if len(fallback_pk.split()) > 6:
        fallback_pk = " ".join(fallback_pk.split()[:6])
        
    fallback_data = {
        "primary_keyword": fallback_pk,
        "secondary_keywords": filtered_suggestions[:5],
        "faq_candidates": filtered_paa[:6],
        "intent_signals": {
            "beginner": True,
            "placement_oriented": True,
            "technology_specific": [],
            "comparison": False,
            "freshness": False
        }
    }
    
    try:
        result = chain.invoke({
            "title": title,
            "primary_query": primary_query,
            "suggestions_str": suggestions_bulleted,
            "paa_str": paa_bulleted
        })
        curated_data = result.model_dump()
        if verbose:
            print("  [Clean] LLM semantic curation successfully completed.")
            print(f"    Selected Primary Keyword: '{curated_data['primary_keyword']}'")
            print(f"    Selected Secondary Keywords: {curated_data['secondary_keywords']}")
        return curated_data
    except Exception as parse_error:
        print(f"Error retrieving structured output in clean_and_curate_seo_data: {parse_error}")
        
    return fallback_data


