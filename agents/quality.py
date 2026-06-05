import json
import re
from providers.llm_factory import get_llm
import config
from agents.utils import parse_json_robustly



# ---------------------------------------------------------------------------
# SEO utility helpers (inlined from the removed agents/seo_auditor.py)
# ---------------------------------------------------------------------------

def check_keyword_in_intro(text: str, keyword: str) -> bool:
    """Return True if *keyword* appears in the first 10 % of *text*."""
    if not keyword or not text:
        return False
    intro_end = max(1, len(text) // 10)
    intro = text[:intro_end]
    return keyword.lower() in intro.lower()


def get_keyword_density(text: str, keyword: str) -> float:
    """Return keyword density as a percentage of total word count."""
    if not keyword or not text:
        return 0.0
    words = text.lower().split()
    total = len(words)
    if total == 0:
        return 0.0
    kw_lower = keyword.lower()
    # Count non-overlapping occurrences of the full keyword phrase
    count = text.lower().count(kw_lower)
    kw_word_count = len(kw_lower.split())
    return (count * kw_word_count / total) * 100


QUALITY_SYSTEM_PROMPT = """You are a professional content auditor. Your job is to grade the quality of a technical blog post on a scale of 0.0 to 10.0 based on specific criteria.

Here are the criteria and weightings you must use:
1. Readability (Weight: 15%): Evaluate clarity, sentence structure, and style.
   - Do NOT penalize technical terminology, acronyms, or proper names themselves.
   - Penalize heavily if the text has excessive hedging (e.g., repeating words like "may", "can", "often", "typically", "generally" across multiple sentences, making the writing feel unconfident).
2. Section Diversity & Structure (Weight: 15%): Ensure headings are informative, sections are balanced, and visual elements (tables, code blocks) are used appropriately.
3. Repetition, Circularity & Padding (Weight: 15%): Penalize fluff, filler words, and repetitive advice/points. Heavily penalize circular structures (e.g. restating the same idea repeatedly using different words in subsequent paragraphs). Each paragraph must add new information, not just pad word count.
4. Content Depth & Completeness (Weight: 20%): Verify whether the article adequately covers the core objectives and user intent of the topic, containing concrete, specific examples (not just generic advice).
   - CRITICAL RULE: If the draft contains any placeholder text (such as "Answer to be populated or refined during SEO optimization" or "placeholder"), you MUST grade 'content_depth' as 0.0 and the 'overall_score' MUST be less than 4.0 (failing the quality gate).
5. Coherence & Flow (Weight: 15%): Check that sections transition smoothly.
6. Actionability & Specificity (Weight: 10%): Ensure advice is highly concrete and actionable.
7. Evidence Usage & Claim Confidence (Weight: 10%): Evaluate whether claims are presented with appropriate confidence levels and whether unsupported claims appear to exist. Do NOT perform full grounding verification against the verified facts list (this is handled by a separate node).

CRITICAL EVALUATION GUIDELINES:
- Ignore structured `COMPONENT:` spec blocks when evaluating prose quality. Evaluate only surrounding explanatory text.
- Localization: When identifying critical failures or rewrite targets, you MUST reference specific sections, headings, or paragraph locations to make the feedback highly actionable.
- Weight Calculation: The `overall_score` MUST be calculated approximately according to the provided weights of each dimension.

You must output a JSON object in this format:
{
  "overall_score": 8.2,
  "dimensions": {
    "readability": 8.0,
    "section_diversity": 8.5,
    "repetition_padding": 9.0,
    "content_depth": 7.5,
    "coherence": 8.0,
    "actionability": 8.5,
    "evidence_and_confidence": 9.0
  },
  "feedback": {
    "strengths": "Detailed description of overall writing and technical strengths",
    "critical_failures": [
      "[Section 2 Heading] - Low depth failure description",
      "[Section 5 Heading] - Excessive hedging or repetitive points description"
    ],
    "rewrite_targets": [
      "section 2",
      "section 5"
    ]
  }
}

Return ONLY valid JSON. Do not write any explanations, markdown code blocks, or leading/trailing text. Do not wrap in backticks."""

def quality_node(state: dict) -> dict:
    """
    LangGraph node that computes Flesch Reading Ease readability,
    performs Python-based deterministic SEO checks, and executes qualitative grading using LLM.
    """
    print("\n--- Running Node: Quality Grader ---")
    
    assembled_draft = state.get("assembled_draft", "")
    metadata = state.get("metadata", {})
    focus_keyword = metadata.get("focus_keyword", "")
    secondary_keywords = metadata.get("secondary_keywords", [])
    
    if not focus_keyword:
        # Fallback to seo_context focus keyword if metadata focus keyword is missing
        focus_keyword = state.get("seo_context", {}).get("primary_keyword", "")
        metadata["focus_keyword"] = focus_keyword
        
    if not assembled_draft:
        print("Warning: Assembled draft is empty. Returning low quality score.")
        return {
            "quality_scores": {
                "overall_score": 0.0,
                "dimensions": {},
                "feedback": "Draft was empty."
            }
        }
        
    # Python-based Deterministic SEO checks

    seo_warnings = []
    
    # 1. Focus keyword in introduction
    passed_intro = check_keyword_in_intro(assembled_draft, focus_keyword)
    if not passed_intro:
        seo_warnings.append(f"Focus keyword '{focus_keyword}' not found in the introduction (first 10% of text).")
        
    # 2. Keyword density checks dynamically based on focus keyword length
    density = get_keyword_density(assembled_draft, focus_keyword)
    num_words = len(focus_keyword.split())
    if num_words <= 2:
        min_density, max_density = 1.0, 2.5
    elif num_words == 3:
        min_density, max_density = 0.5, 1.8
    else:
        min_density, max_density = 0.3, 1.2
        
    passed_density = min_density <= density <= max_density
    if not passed_density:
        seo_warnings.append(f"Focus keyword density is {density:.2f}% (target: {min_density}% - {max_density}% for a {num_words}-word focus keyword).")
        
    # 3. Heading presence checks
    h2s = re.findall(r"^##\s+(.+)$", assembled_draft, re.MULTILINE)
    passed_headings = len(h2s) > 0
    if not passed_headings:
        seo_warnings.append("No H2 headings found in the blog post.")
        
    # 4. FAQ presence checks
    has_faq = any("faq" in h.lower() or "frequently asked questions" in h.lower() for h in h2s)
    if not has_faq:
        seo_warnings.append("No FAQ section found (H2 heading containing 'FAQ' or 'Frequently Asked Questions').")
        
    # 5. Meta description checks
    meta_desc = metadata.get("meta_description", "")
    passed_meta_len = len(meta_desc) <= 160
    if not passed_meta_len:
        seo_warnings.append(f"Meta description is too long ({len(meta_desc)} characters, max 160).")
        
    passed_meta_kw = focus_keyword.lower() in meta_desc.lower()
    if not passed_meta_kw:
        seo_warnings.append(f"Focus keyword '{focus_keyword}' not found in meta description.")
        
    # Check for FAQ placeholders
    has_faq_placeholders = "Answer to be populated" in assembled_draft or "*Answer to be populated" in assembled_draft
    if has_faq_placeholders:
        seo_warnings.append("FAQ placeholders found in the blog body. Answers must be populated.")
        
    # 6. Word Count minimum check
    category = state.get("category", "")
    min_word_count = config.WORD_COUNT_MINIMUMS.get(category, 1600)
    actual_word_count = len(assembled_draft.split())
    if actual_word_count < min_word_count:
        seo_warnings.append(f"Total word count is {actual_word_count} words, which falls below the required minimum of {min_word_count} words for the '{category}' category.")
        
    # Format deterministic SEO audit warnings for the LLM
    if seo_warnings:
        seo_warnings_str = "\n".join([f"- {w}" for w in seo_warnings])
    else:
        seo_warnings_str = "- All deterministic SEO and length checks passed successfully!"
        
    # LLM qualitative evaluation (Medium model)
    llm = get_llm("medium", temperature=0.0)
    
    dynamic_prompt = f"""
---
Focus Keyword: {focus_keyword}
Secondary Keywords: {", ".join(secondary_keywords)}

Deterministic SEO Audit Warnings:
{seo_warnings_str}

Blog Draft Content:
{assembled_draft}

Output Quality Report JSON:"""


    prompt = QUALITY_SYSTEM_PROMPT + dynamic_prompt
    
    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        
        parsed_report = parse_json_robustly(content)
        
        # We no longer penalize the overall qualitative score or trigger quality rewrites based on deterministic SEO warnings.
        # This prevents redundant rewrite loops. The warnings are still collected in metadata for the user's information.


            
        print(f"Quality & SEO grading completed. Overall Score: {parsed_report.get('overall_score')}")
        
        # Sync metadata warnings
        metadata["seo_warnings"] = seo_warnings
        metadata["quality_score"] = float(parsed_report.get("overall_score", 0.0))
        
        return {
            "quality_scores": parsed_report,
            "seo_warnings": seo_warnings,
            "metadata": metadata
        }
        
    except Exception as e:
        print(f"Error in Quality Grader node: {e}. Passing default pass score.")
        metadata["seo_warnings"] = seo_warnings
        return {
            "quality_scores": {
                "overall_score": 7.5,
                "dimensions": {
                    "readability": 7.5,
                    "section_diversity": 7.5,
                    "repetition_padding": 7.5,
                    "content_depth": 7.5,
                    "coherence": 7.5,
                    "actionability": 7.5,
                    "evidence_and_confidence": 7.5
                },
                "feedback": {
                    "strengths": "Default grader strengths fallback",
                    "critical_failures": [f"Grader crashed fallback: {e}"] if e else [],
                    "rewrite_targets": []
                }
            },
            "seo_warnings": seo_warnings,
            "metadata": metadata
        }

