import random
import json
import re
from datetime import datetime, timezone
from agents.utils import parse_json_robustly
from typing import Dict, Any, List
from providers.llm_factory import get_llm
from schemas import SectionBrief, BlogMetadata
import config

NARRATIVE_ARCS = [
    "Progressive Arc: Foundations -> Architectural Mechanisms -> Edge Cases & Trade-offs -> Production Reality",
    "Problem-Solution Arc: Real-world Engineering Pain Points -> Root Cause Analysis -> Technical Solutions -> Architectural Verdict",
    "Myth-Reality Arc: Common Misconceptions -> Grounded Evidence & Benchmarks -> Technical Truth -> Strategic Action Plan",
    "Case Study Arc: High-Scale Industrial Context -> Implementation Bottlenecks -> Quantitative Results -> Lessons & Generalization"
]

PLANNER_SYSTEM_PROMPT = """You are a master technical content strategist and outlining editor. Given a blog topic, category, SEO context, and verified facts, your job is to choose the optimal blog configuration and output a complete, highly specific section-by-section outline.

RULES:
1. CONFIGURATION:
   - 'blog_format': Choose the best format: "deep_dive", "listicle", "step_by_step", "comparison", "qa_interview", "myth_buster".
   - 'audience_level': "fresher" or "intermediate".
   - 'word_count_target': integer between 1600 and 2400 based on format depth.
   - 'section_count_target': integer between 4 and 8.
2. SPECIFICITY: Every section title must be highly specific to the blog topic. NEVER use generic titles like 'Introduction', 'Summary', or 'Conclusion'.
3. FACT ASSIGNMENT: Assign verified facts using their 'fact_1', 'fact_2' reference IDs. Each fact ID MUST be assigned to exactly ONE section — never reuse or assign the same fact to multiple sections to avoid duplication.
4. NO OVERLAP: Each section must have a distinct, non-overlapping focus.
5. FORMAT TITLE FORMATTING:
   - For 'myth_buster', title format MUST be "Myth: [Common Belief]".
   - For 'listicle', titles should be numbered items.
   - For 'step_by_step', titles should be sequential steps/milestones.

Output JSON structure:
{
  "blog_format": "deep_dive",
  "audience_level": "intermediate",
  "word_count_target": 1800,
  "section_count_target": 5,
  "blog_title": "The final approved title",
  "meta_description": "Compelling meta description under 160 chars.",
  "focus_keyword": "Primary keyword",
  "secondary_keywords": ["keyword 1", "keyword 2"],
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8"],
  "sections": [
    {
      "section_index": 1,
      "title": "Topic-Specific H2 Title",
      "section_type": "conceptual",
      "target_word_count": 350,
      "key_points": ["Point 1", "Point 2"],
      "assigned_facts": ["fact_1"],
      "assigned_keywords": ["keyword 1"],
      "include_table": false,
      "include_code_block": false,
      "component_directives": ["comparison_widget"],
      "maps_to_paa": null,
      "is_final_section": false
    }
  ]
}

Return ONLY raw JSON."""

def slugify(text: str) -> str:
    s = text.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[-\s]+", "-", s)
    return s

def planner_node(state: dict) -> dict:
    """
    LangGraph node combining Intake & Planning:
    Determines blog format/targets and generates the full section-by-section outline.
    """
    print("\n--- Running Node: Planner Node (Intake + Planning) ---")
    topic = state.get("topic", "")
    category = state.get("category", "")
    seo_context = state.get("seo_context", {})
    retrieved_context = state.get("retrieved_context", {})
    
    llm = get_llm("medium", temperature=0.3)
    
    verified_facts = retrieved_context.get("verified_facts", [])
    fact_summaries = []
    for i, fact in enumerate(verified_facts, 1):
        claim = fact.get("claim", "")
        words = claim.split()[:40]
        summary = " ".join(words) + ("..." if len(claim.split()) > 40 else "")
        fact_summaries.append(f"  fact_{i}: \"{summary}\"")
    fact_summaries_str = "\n".join(fact_summaries) if fact_summaries else "  None"
    
    selected_arc = random.choice(NARRATIVE_ARCS)
    
    dynamic_prompt = f"""
---
Target Blog Title: {topic}
Blog Category: {category}
Target Narrative Arc: {selected_arc}

SEO Context:
{json.dumps(seo_context, indent=2)}

Verified Facts Summary:
{fact_summaries_str}

Output Outline JSON:"""

    prompt = PLANNER_SYSTEM_PROMPT + dynamic_prompt
    
    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        parsed_dict = parse_json_robustly(content)
        
        blog_format = str(parsed_dict.get("blog_format", "deep_dive"))
        audience_level = str(parsed_dict.get("audience_level", "fresher"))
        word_count_target = int(parsed_dict.get("word_count_target", 1800))
        section_count_target = int(parsed_dict.get("section_count_target", 5))
        
        sections_data = parsed_dict.get("sections", [])
        validated_briefs = []
        for i, sec in enumerate(sections_data, 1):
            sec["section_index"] = i
            sec["is_final_section"] = (i == len(sections_data))
            brief = SectionBrief(**sec)
            validated_briefs.append(brief.model_dump() if hasattr(brief, "model_dump") else brief.dict())
            
        blog_title = parsed_dict.get("blog_title", topic)
        meta_desc = parsed_dict.get("meta_description", f"Guide on {topic}.")
        if len(meta_desc) > 160:
            meta_desc = meta_desc[:157] + "..."
            
        focus_kw = str(parsed_dict.get("focus_keyword", topic)).strip("*'\"`")
        if "," in focus_kw:
            focus_kw = focus_kw.split(",")[0].strip()
        if ":" in focus_kw:
            focus_kw = focus_kw.split(":")[-1].strip()
        words = focus_kw.split()
        if len(words) > 5:
            focus_kw = " ".join(words[:4])
            
        metadata_obj = BlogMetadata(
            title=blog_title,
            slug=slugify(blog_title),
            date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            category=category,
            tags=parsed_dict.get("tags", [category.replace(" ", "-").lower()]),
            meta_description=meta_desc,
            focus_keyword=focus_kw,
            secondary_keywords=parsed_dict.get("secondary_keywords", []),
            word_count=0,
            quality_score=0.0,
            revision_count=0,
            prompt_version=config.PROMPT_VERSION,
            blog_format=blog_format,
            seo_warnings=[]
        )
        metadata_dict = metadata_obj.model_dump() if hasattr(metadata_obj, "model_dump") else metadata_obj.dict()
        
        print(f"Outline planned successfully: Format={blog_format}, Target={word_count_target}w, Sections={len(validated_briefs)}.")
        return {
            "blog_format": blog_format,
            "audience_level": audience_level,
            "word_count_target": word_count_target,
            "section_count_target": section_count_target,
            "outline": parsed_dict,
            "section_briefs": validated_briefs,
            "metadata": metadata_dict
        }
        
    except Exception as e:
        print(f"Warning: Planner Node parsing failed ({e}). Generating safe fallback outline.")
        fallback_briefs = []
        sec_words = 1800 // 5
        fallback_titles = [
            f"Understanding {topic[:30]}: Core Concepts",
            f"Key Architectural Mechanisms",
            f"Implementation & Code Walkthrough",
            f"Engineering Trade-offs & Common Pitfalls",
            f"Key Takeaways and Summary"
        ]
        for i, title_str in enumerate(fallback_titles, 1):
            is_last = (i == 5)
            brief = SectionBrief(
                section_index=i,
                title=title_str,
                section_type="intro" if i == 1 else ("summary" if is_last else "conceptual"),
                target_word_count=sec_words,
                key_points=[f"Overview point for {topic[:30]}"],
                assigned_facts=[],
                assigned_keywords=[],
                component_directives=["quiz"] if is_last else [],
                is_final_section=is_last
            )
            fallback_briefs.append(brief.model_dump() if hasattr(brief, "model_dump") else brief.dict())
            
        metadata_fallback = BlogMetadata(
            title=topic,
            slug=slugify(topic),
            date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            category=category,
            tags=[category.replace(" ", "-").lower()],
            meta_description=f"Guide on {topic[:100]}.",
            focus_keyword=topic,
            secondary_keywords=[],
            word_count=0,
            quality_score=0.0,
            revision_count=0,
            prompt_version=config.PROMPT_VERSION,
            seo_warnings=[]
        )
        return {
            "blog_format": "deep_dive",
            "audience_level": "fresher",
            "word_count_target": 1800,
            "section_count_target": 5,
            "outline": {"sections": fallback_briefs},
            "section_briefs": fallback_briefs,
            "metadata": metadata_fallback.model_dump() if hasattr(metadata_fallback, "model_dump") else metadata_fallback.dict()
        }
