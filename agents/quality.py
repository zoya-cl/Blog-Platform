import json
import re
from providers.llm_factory import get_llm
import config
from agents.utils import parse_json_robustly



def count_syllables(word: str) -> int:
    word = word.lower().strip()
    if len(word) <= 3:
        return 1
    word = re.sub(r'(?:[^laeiouy]|ed|es|e)$', '', word)
    word = re.sub(r'^y', '', word)
    syllables = len(re.findall(r'[aeiouy]{1,2}', word))
    return max(1, syllables)

def calculate_flesch_reading_ease(text: str) -> float:
    """Calculates Flesch Reading Ease score (0 to 100)."""
    clean_text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    clean_text = re.sub(r'COMPONENT:.*?props:\s*\{.*?\}', '', clean_text, flags=re.DOTALL)
    clean_text = re.sub(r'#+\s+.*', '', clean_text)
    
    sentences = [s for s in re.split(r'[.!?]+', clean_text) if s.strip()]
    words = [w for w in re.findall(r'\b[a-zA-Z]+\b', clean_text) if w.strip()]
    
    if not sentences or not words:
        return 60.0
        
    num_sentences = len(sentences)
    num_words = len(words)
    num_syllables = sum(count_syllables(w) for w in words)
    
    score = 206.835 - 1.015 * (num_words / num_sentences) - 84.6 * (num_syllables / num_words)
    return max(0.0, min(100.0, round(score, 2)))


QUALITY_SYSTEM_PROMPT = """You are a professional content auditor. Your job is to grade the quality of a technical blog post on a scale of 0.0 to 10.0 based on specific criteria.

Here are the criteria and weightings you must use:
1. Readability (Weight: 15%): Evaluate clarity, sentence structure, and style.
   - Consider the calculated Flesch Reading Ease score provided in the prompt.
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
        
    # Calculate quantitative readability metric
    readability_score = calculate_flesch_reading_ease(assembled_draft)
    print(f"Calculated Flesch Reading Ease score: {readability_score}/100")
        
    # Python-based Deterministic Structural checks
    seo_warnings = []
    
    # 1. Heading presence checks
    h2s = re.findall(r"^##\s+(.+)$", assembled_draft, re.MULTILINE)
    passed_headings = len(h2s) > 0
    if not passed_headings:
        seo_warnings.append("No H2 headings found in the blog post.")
        
    # 2. Check for FAQ placeholders
    has_faq_placeholders = "Answer to be populated" in assembled_draft or "*Answer to be populated" in assembled_draft
    if has_faq_placeholders:
        seo_warnings.append("FAQ placeholders found in the blog body. Answers must be populated.")
        
    # 3. Word Count minimum check
    category = state.get("category", "")
    min_word_count = getattr(config, "WORD_COUNT_MINIMUMS", {}).get(category, 1600)
    actual_word_count = len(assembled_draft.split())
    if actual_word_count < min_word_count:
        seo_warnings.append(f"Total word count is {actual_word_count} words, which falls below the required minimum of {min_word_count} words for the '{category}' category.")
        
    # Format deterministic audit warnings for the LLM
    if seo_warnings:
        seo_warnings_str = "\n".join([f"- {w}" for w in seo_warnings])
    else:
        seo_warnings_str = "- All deterministic structure and length checks passed successfully!"
        
    # LLM qualitative evaluation (Medium model)
    llm = get_llm("medium", temperature=0.0)
    
    dynamic_prompt = f"""
---
Focus Keyword: {focus_keyword}
Secondary Keywords: {", ".join(secondary_keywords)}
Calculated Flesch Reading Ease Score: {readability_score} / 100 (60-70 is standard, 70-80 easy to read)

Deterministic Audit Warnings:
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
        print(f"Error in Quality Grader node: {e}. Falling back to retry score.")
        metadata["seo_warnings"] = seo_warnings
        return {
            "quality_scores": {
                "overall_score": 5.0,
                "dimensions": {
                    "readability": 5.0,
                    "section_diversity": 5.0,
                    "repetition_padding": 5.0,
                    "content_depth": 5.0,
                    "coherence": 5.0,
                    "actionability": 5.0,
                    "evidence_and_confidence": 5.0
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


QUALITY_REWRITE_SYSTEM_PROMPT = """You are an elite technical writer and editor. Your task is to revise a blog draft to resolve quality or SEO issues identified by our grading system.

You must apply these strict rules:
1. TARGETED CORRECTION ONLY: Modify ONLY the specific sections or aspects of the blog draft directly responsible for failing grader checks. Do NOT rewrite passing sections.
2. EXPANSION BOUNDS: If you must expand sections, do NOT invent facts or benchmarks. Expand using existing section context or facts.
3. COMPONENT PROTECTION: Do NOT modify, delete, or remove structured `COMPONENT:` blocks.
4. ELIMINATE REPETITION: Clean circular logic or repetitive phrasing flagged by the grader.
5. WORD COUNT ENFORCEMENT: Preserve the overall length of the draft.

Return ONLY the final revised markdown text of the blog."""

def clean_llm_markdown(text: str) -> str:
    clean = text.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:markdown|text)?\n", "", clean)
        clean = re.sub(r"\n```$", "", clean)
        clean = clean.strip()
    return clean

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

    prompt = QUALITY_REWRITE_SYSTEM_PROMPT + dynamic_prompt
    
    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        revised_draft = clean_llm_markdown(content)
        
        orig_count = len(assembled_draft.split())
        new_count = len(revised_draft.split())
        if orig_count > 0 and new_count < int(orig_count * 0.95):
            print(f"Warning: Quality rewrite reduced word count from {orig_count} to {new_count} (dropped > 5%). Preserving original draft.")
            return {
                "quality_revision_count": revision_count
            }
            
        print(f"Quality rewrite iteration {revision_count} completed. Word count: {new_count}.")
        return {
            "assembled_draft": revised_draft,
            "quality_revision_count": revision_count
        }
    except Exception as e:
        print(f"Error in Quality Rewriter: {e}. Keeping original draft.")
        return {
            "quality_revision_count": revision_count
        }


