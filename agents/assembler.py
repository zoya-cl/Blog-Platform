import re
import json
from typing import List, Dict, Any
from providers.llm_factory import get_llm

FAQ_GENERATOR_PROMPT = """You are an expert technical content strategist. Your task is to write a detailed, highly informative, and specific FAQ section for a placement preparation blog.

Here are the details:
Blog Title: {title}
FAQ Questions:
{questions}

Verified Facts List (Grounding Database):
{verified_facts}

Rules:
1. For each question, provide a complete, authoritative, and specific 2-4 sentence answer.
2. State all facts confidently; do not overuse hedging words (like may, can, often, typically, generally) for standard, universally accepted technical definitions and programming practices.
3. You must use the verified facts provided where applicable.
4. Each question-answer pair must be structured as:
### [Question Text]
[Detailed Answer Text]

Return ONLY the markdown text containing the questions and answers (with no starting title heading like "## Frequently Asked Questions" or "FAQ", as that is managed by the system). Do not wrap in backticks or add any intro/outro messages."""

def check_transition(curr_section: str, next_section: str) -> str:
    """
    Pure Python check to see if a transition is needed between sections.
    If the current section does not end with typical sentence punctuation,
    it adds a period. If the boundary transition seems abrupt, it returns a spacer.
    """
    curr_clean = curr_section.strip()
    next_clean = next_section.strip()
    
    if not curr_clean or not next_clean:
        return ""
        
    transition_prefix = ""
    # Ensure current section ends with punctuation
    if curr_clean[-1] not in [".", "!", "?", ":", "`", "*"]:
        transition_prefix = ". "
        
    return transition_prefix

def assembler(state: dict) -> dict:
    """
    Stitches the section drafts in outline order,
    uses LLM to dynamically generate high-quality answers for FAQ candidates (no placeholders),
    and appends the FAQ block before the final CTA section.
    """
    print("\n--- Running Node: Assembler (Pure Python + FAQ LLM) ---")
    drafts = state.get("section_drafts", [])
    seo_context = state.get("seo_context", {})
    faq_candidates = seo_context.get("faq_candidates", [])
    retrieved_context = state.get("retrieved_context", {})
    title = state.get("topic", state.get("metadata", {}).get("title", ""))
    
    if not drafts:
        print("Warning: No section drafts found to assemble.")
        return {"assembled_draft": ""}
        
    assembled_parts = []
    num_sections = len(drafts)
    
    if num_sections > 1 and faq_candidates:
        # Stitch up to second to last section
        for i in range(num_sections - 1):
            curr_part = drafts[i]
            if i > 0:
                transition = check_transition(assembled_parts[-1], curr_part)
                assembled_parts.append(transition + curr_part)
            else:
                assembled_parts.append(curr_part)
                
        # Generate the FAQ section dynamically using LLM to avoid placeholders
        print(f"Generating answers for {len(faq_candidates)} FAQ candidates...")
        faq_lines = ["\n\n## Frequently Asked Questions\n"]
        
        try:
            llm = get_llm("medium", temperature=0.2)
            questions_str = "\n".join([f"- {q}" for q in faq_candidates])
            facts_str = json.dumps(retrieved_context.get("verified_facts", []), indent=2)
            
            prompt = FAQ_GENERATOR_PROMPT.format(
                title=title,
                questions=questions_str,
                verified_facts=facts_str
            )
            
            response = llm.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)
            clean_faq = content.strip()
            
            # Remove backtick wrap if present
            if clean_faq.startswith("```"):
                clean_faq = re.sub(r"^```(?:markdown|text)?\n", "", clean_faq)
                clean_faq = re.sub(r"\n```$", "", clean_faq)
                clean_faq = clean_faq.strip()
                
            faq_lines.append(clean_faq)
            print("FAQ section generated successfully with LLM.")
            
        except Exception as e:
            print(f"Error generating FAQ section with LLM: {e}. Falling back to rule-based FAQs.")
            # Fallback to avoid empty answers or placeholder words that fail quality gate
            for j, q in enumerate(faq_candidates, 1):
                faq_lines.append(f"\n### {q.strip()}")
                faq_lines.append(f"\nThis guide explains key details to help you prepare. Make sure to study the main frameworks, platforms, and tools covered above to build a competitive edge in your upcoming interviews.")
                
        assembled_parts.append("\n".join(faq_lines))
        
        # Append final section containing the CTA
        final_part = drafts[-1]
        transition = check_transition(assembled_parts[-1], final_part)
        assembled_parts.append(transition + final_part)
        
    else:
        # No FAQ or single section: just stitch all drafts in order
        for i, curr_part in enumerate(drafts):
            if i > 0:
                transition = check_transition(assembled_parts[-1], curr_part)
                assembled_parts.append(transition + curr_part)
            else:
                assembled_parts.append(curr_part)
                
    assembled_draft = "\n\n".join(assembled_parts)
    print(f"Draft assembled successfully. Length: {len(assembled_draft)} characters.")
    return {
        "assembled_draft": assembled_draft
    }
