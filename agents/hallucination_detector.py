import json
import re
from providers.llm_factory import get_llm
from agents.utils import parse_json_robustly
from prompts.hallucination_checklists import CHECKLISTS

HALLUCINATION_SYSTEM_PROMPT = """You are an adversarial AI fact-checker and code validator. Your job is to check a draft technical blog post against a database of verified grounding facts and identify any hallucinations, ungrounded claims, or logical/syntactical errors.

You must follow these strict rules:
1. FACT-GROUNDING & TECHNICAL KNOWLEDGE BOUNDS:
   - Universally accepted technical knowledge, standard algorithms, well-established programming concepts, or common engineering terminology do NOT require explicit grounding in the verified facts database. Do NOT flag them as hallucinations.
   - Specific salaries, packaging metrics, statistical percentages, headcounts, or company-specific figures MUST be grounded in the provided 'Verified Grounding Facts'. If the draft states specific metrics or figures that do not appear in the verified facts, flag them as ungrounded unless they are phrased with appropriate hedging language.
2. CONTRADICTION CHECK: Flag any statements in the blog draft that contradict the provided verified facts.
3. STABILIZED CODE & LOGIC VALIDATION: Check code blocks for obvious syntax errors, clear logical inconsistencies, or contradictions with surrounding explanations. Do NOT perform deep algorithmic validation or try to find hidden runtime bugs.
4. CATEGORY-SPECIFIC CHECKLIST: You must apply the following specific rules for this blog category:
{category_checklist}

CRITICAL COMPONENT & SCORING GUIDELINES:
- COMPONENT PROTECTION: Ignore structured `COMPONENT:` spec blocks unless they are explicitly malformed (e.g. invalid JSON props or incorrect type properties).
- SCORING: Use the scoring rules as guidance rather than strict arithmetic. Severity concentration matters more than issue count. A single high severity issue represents a major breach, whereas multiple minor low severity issues should not reduce the score excessively.

For each issue identified, categorize the severity:
- "high": Flat contradiction of a verified fact, malformed component block, obvious code syntax error, or completely fabricated critical metric/salary. Must be fixed.
- "medium": Ungrounded specific claim/metric, statistics/percentage stated as absolute fact without hedging, or slightly misleading technical description. Must be fixed.
- "low": Minor phrasing issues or missing hedging where the risk is low. Optional fix.

You must output a JSON object in this format:
{{
  "score": 10.0, // Start at 10.0. Score should be guidance rather than strict arithmetic. Minimum is 0.0.
  "has_hallucinations": true, // Set to true if any high or medium severity issue is found.
  "hallucinations": [
    {{
      "section": "Section 3 Heading or Number",
      "passage": "Exact quote of the passage from the draft containing the issue",
      "claim": "The ungrounded or incorrect claim being made",
      "reason": "Explain why it is incorrect or ungrounded relative to the verified facts",
      "severity": "high", // "high", "medium", or "low"
      "confidence": 0.85, // Float between 0.0 and 1.0 representing your certainty of this issue
      "fix_suggestion": "Detailed instruction on how to rewrite or hedge the passage"
    }}
  ]
}}

Return ONLY valid JSON. Do not write any explanations, markdown code blocks, or leading/trailing text. Do not wrap in backticks."""

def hallucination_detector(state: dict) -> dict:
    """
    LangGraph node that runs an adversarial fact checking LLM call against verified facts.
    """
    print("\n--- Running Node: Hallucination Detector ---")
    
    assembled_draft = state.get("assembled_draft", "")
    retrieved_ctx = state.get("retrieved_context", {})
    verified_facts = retrieved_ctx.get("verified_facts", [])
    checklist_id = state.get("hallucination_checklist", "generic")
    category = state.get("category", "")
    
    category_checklist = CHECKLISTS.get(checklist_id)
    if not category_checklist:
        category_checklist = CHECKLISTS.get(category)
    if not category_checklist:
        category_checklist = CHECKLISTS.get("generic", "")
    
    # We use the medium model for structuring/evaluating
    llm = get_llm("medium", temperature=0.0)
    
    dynamic_prompt = f"""
---
Blog Category Checklist ID: {checklist_id}
Category Checklist rules:
{category_checklist}

Verified Grounding Facts List:
{json.dumps(verified_facts, indent=2)}

Blog Draft Content:
{assembled_draft}

Output Hallucination Report JSON:"""

    prompt = HALLUCINATION_SYSTEM_PROMPT.format(category_checklist=category_checklist) + dynamic_prompt
    
    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        
        parsed_report = parse_json_robustly(content)
        
        # Post-process score and has_hallucinations to be safe
        score = float(parsed_report.get("score", 10.0))
        hallucinations = parsed_report.get("hallucinations", [])
        
        # Enforce has_hallucinations is true if there are high/medium severities
        has_critical = any(h.get("severity") in ["high", "medium"] for h in hallucinations)
        
        report = {
            "score": score,
            "has_hallucinations": has_critical or parsed_report.get("has_hallucinations", False),
            "hallucinations": hallucinations
        }
        
        print(f"Hallucination detection finished. Score: {report['score']}, Has Hallucinations: {report['has_hallucinations']}, Count: {len(report['hallucinations'])}")
        return {
            "hallucination_report": report
        }
        
    except Exception as e:
        print(f"Error in Hallucination Detector: {e}. Passing clean report.")
        # Fallback to no hallucinations
        return {
            "hallucination_report": {
                "score": 10.0,
                "has_hallucinations": False,
                "hallucinations": []
            }
        }
