import json
import re
from providers.llm_factory import get_llm
import config

HALLUCINATION_REWRITE_SYSTEM_PROMPT = """You are a meticulous technical editor. Your task is to revise a technical blog post to correct hallucinated, ungrounded, or incorrect claims based on the provided hallucination report and verified grounding facts.

You must follow these strict instructions:
1. TARGETED CORRECTION ONLY: ONLY modify the specific passages flagged in the hallucination report. Replace them with corrected, grounded phrasing. Do NOT rewrite, clean, or compress any other parts of the blog post. Keep the structure, headings, and paragraphs intact.
2. IMMUTABLE COMPONENT & IMAGE BLOCKS: Never modify, delete, reorder, or regenerate structured `COMPONENT:` spec blocks or standard markdown image tags (e.g., `![alt text](path/to/image.png)`) unless they are explicitly flagged in the report. Treat both as completely immutable and preserve them exactly where they are in the text.
3. CITATION PRESERVATION: Preserve all existing source citations (e.g. `[Glassdoor](url)`) in the text unless the hallucination report explicitly requires changing or removing them.
4. STRONGER ANTI-REWRITE & UNCERTAINTY: If a flagged passage cannot be corrected or verified using the provided grounding facts, replace the passage with a qualified uncertainty statement (e.g., "The exact metrics for this category are unverified, but industry practices suggest...") rather than inventing or hypothesizing new evidence.
5. WORD COUNT PRESERVATION: You MUST preserve the length of the draft. Do NOT shorten, summarize, or compress the article. The output must have approximately the same length and structure as the original input.

Return ONLY the final revised markdown text of the blog. Do not add intro/outro comments or wrap in backticks."""

QUALITY_REWRITE_SYSTEM_PROMPT = """You are an elite technical writer and editor. Your task is to revise a blog draft to resolve quality or SEO issues identified by our grading system.

You must apply these strict rules:
1. TARGETED CORRECTION ONLY: Modify ONLY the specific sections or aspects of the blog draft directly responsible for failing grader checks. Do NOT rewrite or modify passing sections; leave them completely untouched.
2. EXPANSION BOUNDS (ANTI-FABRICATION): If you must expand sections to meet word count targets or increase technical depth, you are strictly PROHIBITED from inventing new facts, statistics, benchmarks, or code. Expand ONLY by using:
   - Existing grounding facts provided in the Verified Grounding Facts List
   - Existing section context and details
   - Already retrieved evidence present in the draft
3. BALANCE CONFIDENCE & UNCERTAINTY: Avoid unnecessary hedging for established technical facts, but preserve and respect uncertainty when grounding evidence is incomplete, conflicting, or unverified.
4. COMPONENT & IMAGE PROTECTION: Do NOT modify, delete, merge, reorder, or remove structured `COMPONENT:` blocks or standard markdown image tags (e.g., `![alt text](path/to/image.png)`) unless explicitly flagged by the grader. Treat both as completely immutable and preserve them exactly where they are in the text.
5. ELIMINATE REPETITION & STUFFING: Clean circular logic or keyword stuffing flagged by the grader. Ensure the focus keyword is naturally integrated (especially in the intro) without mechanical repetition.
6. WORD COUNT ENFORCEMENT: Preserve the overall length of the draft, expanding only where word count minimums were flagged using verified grounding facts or structural elaboration of existing context.

Return ONLY the final revised markdown text of the blog. Do not add intro/outro comments or wrap in backticks."""

def clean_llm_markdown(text: str) -> str:
    clean = text.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:markdown|text)?\n", "", clean)
        clean = re.sub(r"\n```$", "", clean)
        clean = clean.strip()
    return clean

def hallucination_rewriter(state: dict) -> dict:
    """
    LangGraph node that takes the assembled draft and applies targeted fixes for hallucinated passages.
    """
    print("\n--- Running Node: Hallucination Rewriter ---")
    assembled_draft = state.get("assembled_draft", "")
    report = state.get("hallucination_report", {})
    retrieved_ctx = state.get("retrieved_context", {})
    verified_facts = retrieved_ctx.get("verified_facts", [])
    
    revision_count = state.get("hallucination_revision_count", 0) + 1
    
    # We use the large model for high factual precision during targeted edits
    llm = get_llm("large", temperature=0.2)

    
    dynamic_prompt = f"""
---
Hallucination Report:
{json.dumps(report, indent=2)}

Verified Grounding Facts List:
{json.dumps(verified_facts, indent=2)}

Current Blog Draft:
{assembled_draft}

Revised Blog Draft Markdown:"""

    prompt = HALLUCINATION_REWRITE_SYSTEM_PROMPT + dynamic_prompt
    
    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        revised_draft = clean_llm_markdown(content)
        print(f"Hallucination rewrite iteration {revision_count} completed.")
        return {
            "assembled_draft": revised_draft,
            "hallucination_revision_count": revision_count
        }
    except Exception as e:
        print(f"Error in Hallucination Rewriter: {e}. Keeping original draft.")
        return {
            "hallucination_revision_count": revision_count
        }

def quality_rewriter(state: dict) -> dict:
    """
    LangGraph node that rewrites or improves the blog post based on quality grading feedback.
    """
    print("\n--- Running Node: Quality Rewriter ---")
    assembled_draft = state.get("assembled_draft", "")
    quality_scores = state.get("quality_scores", {})
    section_briefs = state.get("section_briefs", [])
    retrieved_ctx = state.get("retrieved_context", {})
    verified_facts = retrieved_ctx.get("verified_facts", [])
    word_count_target = state.get("word_count_target", 2000)
    revision_count = state.get("quality_revision_count", 0) + 1
    
    # Large model for quality rewriting where style/prose matters
    llm = get_llm("large", temperature=0.7)
    
    dynamic_prompt = f"""
---
Target Word Count: {word_count_target} words
Quality Grader Feedback:
{json.dumps(quality_scores, indent=2)}

Original Section Outline:
{json.dumps(section_briefs, indent=2)}

Verified Grounding Facts List:
{json.dumps(verified_facts, indent=2)}

Current Blog Draft:
{assembled_draft}

Revised Blog Draft Markdown:"""

    prompt = QUALITY_REWRITE_SYSTEM_PROMPT.format(word_count_target=word_count_target) + dynamic_prompt
    
    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        revised_draft = clean_llm_markdown(content)
        print(f"Quality rewrite iteration {revision_count} completed.")
        return {
            "assembled_draft": revised_draft,
            "quality_revision_count": revision_count
        }
    except Exception as e:
        print(f"Error in Quality Rewriter: {e}. Keeping original draft.")
        return {
            "quality_revision_count": revision_count
        }
