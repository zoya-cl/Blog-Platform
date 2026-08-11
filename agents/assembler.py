import re
import json
from typing import List, Dict, Any
from providers.llm_factory import get_llm
from agents.utils import clean_llm_markdown

AUTO_FAQ_GENERATOR_PROMPT = """You are an expert technical content strategist. Your task is to generate a comprehensive Frequently Asked Questions (FAQ) section for a placement preparation blog.

Blog Title: {title}
Blog Category: {category}

Article Overview:
{section_summaries}

Verified Facts List:
{verified_facts}

Rules:
1. Generate 3 to 4 distinct, high-impact FAQ questions that candidates or engineers frequently ask about this topic.
2. For each question, provide a complete, authoritative 2-4 sentence answer.
3. State all facts confidently without excessive hedging.
4. Format each question-answer pair as:
### [Question Text]
[Detailed Answer Text]

Return ONLY the markdown text containing the questions and answers (with no starting title heading like "## Frequently Asked Questions", as that is managed by the system). Do not wrap in backticks or add intro/outro comments."""

def check_transition(curr_section: str, next_section: str) -> str:
    """
    Ensures clean paragraph spacing between markdown sections.
    Does NOT append period artifacts before markdown headers (##).
    """
    curr_clean = curr_section.strip()
    next_clean = next_section.strip()
    
    if not curr_clean or not next_clean:
        return "\n\n"
        
    # If the next section starts with a heading, return clean blank lines
    if next_clean.startswith("#"):
        return "\n\n"
        
    if curr_clean[-1] not in [".", "!", "?", ":", "`", "*"]:
        return ".\n\n"
        
    return "\n\n"

def assembler(state: dict) -> dict:
    """
    Stitches all section drafts in outline order,
    dynamically generates high-quality FAQ answers using LLM,
    and appends the FAQ block cleanly at the end of the article.
    """
    print("\n--- Running Node: Assembler (Pure Python + FAQ LLM) ---")
    drafts = state.get("section_drafts", [])
    retrieved_context = state.get("retrieved_context", {})
    title = state.get("topic", state.get("metadata", {}).get("title", ""))
    category = state.get("category", "")
    
    if not drafts:
        print("Warning: No section drafts found to assemble.")
        return {"assembled_draft": ""}
        
    assembled_parts = []
    
    # 1. Stitch all section drafts sequentially
    for i, curr_part in enumerate(drafts):
        curr_clean = curr_part.strip()
        if not curr_clean:
            continue
            
        if assembled_parts:
            transition = check_transition(assembled_parts[-1], curr_clean)
            assembled_parts.append(transition + curr_clean)
        else:
            assembled_parts.append(curr_clean)
            
    # 2. Append FAQ section at the end if we have multiple sections
    if len(drafts) > 1:
        print("Generating auto-FAQ section for draft...")
        
        # Build section summaries for context
        section_summaries = []
        for s_idx, s_draft in enumerate(drafts):
            words = s_draft.split()[:40]
            summary = " ".join(words)
            section_summaries.append(f"- Section {s_idx+1}: {summary}...")
        summaries_str = "\n".join(section_summaries)
        
        try:
            llm = get_llm("medium", temperature=0.4)
            facts_str = json.dumps(retrieved_context.get("verified_facts", []), indent=2)
            
            prompt = AUTO_FAQ_GENERATOR_PROMPT.format(
                title=title,
                category=category,
                verified_facts=facts_str,
                section_summaries=summaries_str
            )
            
            response = llm.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)
            clean_faq = clean_llm_markdown(content)
            
            faq_block = f"## Frequently Asked Questions\n\n{clean_faq}"
            assembled_parts.append("\n\n" + faq_block)
            print("FAQ section generated successfully with LLM.")
            
        except Exception as e:
            print(f"Error generating FAQ section with LLM: {e}. Passing clean stitching.")
            
    assembled_draft = "".join(assembled_parts).strip()
    print(f"Draft assembled successfully. Length: {len(assembled_draft)} characters.")
    return {
        "assembled_draft": assembled_draft
    }
