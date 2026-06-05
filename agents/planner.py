import json
import re
from datetime import datetime, timezone
from agents.utils import parse_json_robustly
from typing import Dict, Any, List
from providers.llm_factory import get_llm
from schemas import SectionBrief, BlogMetadata
import config

PLANNER_SYSTEM_PROMPT = """You are a master technical content strategist and outlining editor. Your task is to design a comprehensive, highly specific blog outline based on the provided SEO intent signals and verified grounding facts.

You must follow these strict rules to design the outline:
1. SPECIFICITY TEST: Every H2 heading and H3 sub-heading in the outline must be highly specific to the target blog topic. You must dynamically inspect the blog's category and SEO intent signals (e.g. `placement_oriented` vs `technology_specific`) to classify the focus:
   - For career-focused or placement-oriented topics (e.g., if `placement_oriented` is true or the category targets career milestones), maintain career and placement specificity (e.g., 'Understanding the 4-Round Google SDE Interview Structure').
   - For technical, architectural, or developer-centric topics (e.g., if `technology_specific` contains technical domains or the category covers tools/comparisons), maintain technical and architectural specificity (e.g., 'In-Memory State Lifecycle in Kubernetes Pods').
   - You must NEVER use generic headings like 'Introduction', 'Summary', 'Best Practices', or 'Conclusion' which could fit unrelated articles.
2. SECTION COUNT CONSTRAINTS: You MUST generate between 4 to 8 sections in the outline depending on topic complexity. Typically, target the 'Section Count Target' specified in the prompt below, but you are allowed to adjust dynamically between 4 and 8 sections to fit the topic's depth perfectly and stabilize writing budgets.
3. INTENT-SIGNAL STRUCTURE: Structure the outline based on the SEO intent signals and retrieved database overviews:
   - Beginner-oriented topics (e.g. basic explanations, fundamentals) must appear early in the outline.
   - Placement-oriented or advanced technical details (specific coding interview tips, real interview rounds) must appear in the middle sections.
   - If a 'Roadmap Data Overview' exists, you MUST design the early/middle sections to align directly with the sequence of steps and topics outlined in that roadmap.
   - If a 'LeetCode Data Overview' exists, you MUST dedicate a middle section specifically to practicing these curated coding questions and algorithms.
   - If PAA (People Also Ask) questions exist in the SEO context, map them to sections that directly answer them (populate 'maps_to_paa').
   - The final section should provide actionable next steps, a checklist, a summary, or a practical takeaway depending on the article type.
4. FACT ASSIGNMENT BY REFERENCE: Do not invent any numbers, percentages, salaries, or specific company metrics. You are strictly PROHIBITED from copy-pasting the raw fact claims or exact multi-sentence text into the outline sections. Instead, assign facts to sections by referencing their 1-based index identifiers from the 'Verified Grounding Facts List' (e.g. `["fact_1", "fact_3"]`). `fact_1` corresponds to the first item in the grounding list, `fact_2` corresponds to the second item, and so on. This prevents ugly text duplication and keeps outline structures clean.
5. NO OVERLAP: Each section must have a distinct, non-overlapping purpose. Do not repeat key points across sections.
6. KEYWORD INJECTION: Assign relevant keywords from the focus/secondary keywords list to the sections where they fit most naturally.
7. SECTION TYPE & COMPONENT DIRECTIVES: Design outline sections with specific functional purposes:
    - Each section must declare a `section_type` matching its style (e.g. 'intro', 'conceptual', 'tutorial', 'comparison', 'roadmap', 'faq', 'summary', 'cta').
    - Each section must declare an extensible array of `component_directives` representing the visual/interactive elements required (e.g. 'table', 'code_block', 'comparison_widget', 'quiz', 'roadmap').
    - UNIQUE COMPONENT RULE: You are STRICTLY FORBIDDEN from assigning the same component type (e.g., 'table', 'comparison_widget', 'roadmap') to multiple sections. Each component type must appear AT MOST ONCE in the entire blog outline (except for the final section's quizzes).
    - COMPONENT LIMIT RULE: Each section brief must contain AT MOST ONE component directive in `component_directives`. Do not overload sections. For backward compatibility, also populate `include_table` (set to true if 'table' is present in `component_directives`) and `include_code_block` (set to true if 'code_block' is present in `component_directives`).
    - CONTENT SUITABILITY RULE: `component_directives` MUST be empty (`[]`) for any section whose `section_type` is 'intro' or 'faq'. For 'conceptual' and 'comparison' sections, only assign a component if the content genuinely requires structured data (e.g., a side-by-side metric comparison → 'table' or 'comparison_widget'). 'cta' and 'summary' sections MUST contain exactly one 'quiz' component directive (to render three sequential 'Test Yourself' questions at the very end of the blog post), and no other component types. The 'confirm' component type is completely deprecated and MUST NOT be used anywhere. NEVER assign `'code_block'` to conceptual, intro, comparison, summary, faq, or cta sections — `'code_block'` is ONLY valid for sections with `section_type` of 'tutorial' or 'roadmap' where real, implementable algorithm code is the primary content.

8. DYNAMIC TARGET WORD COUNTS: Distribute the overall word count target dynamically across the sections based on topic complexity. Sections MUST NOT be of uniform length. Allow introductory, high-level overview, or quick checklist sections to be shorter (e.g., 150 to 250 words), while deep-dive technical implementations, coding walkthroughs, comparative analysis, or operational engineering constraint sections should be much longer and comprehensive (e.g., 500 to 750 words). Ensure that the sum of all section word count targets exactly matches the overall word_count_target.
9. OPERATIONAL & ENGINEERING CONSTRAINTS: For technical and developer-focused articles, you must design sections addressing operational and engineering trade-offs (e.g. latency, GPU/compute costs, memory constraints, context windows, security/injections, data drift, production monitoring) **ONLY if they are directly relevant to the specific article topic**. For example, a deep-dive comparison of AI models or serverless platforms must analyze hardware costs and cold starts, while a DSA interview question guide should focus on space/time algorithmic bounds and runtime constraints without hallucinating GPU or cloud drift parameters.
10. TAGS COUNT RULE: The `tags` list in the output JSON MUST contain between 8 to 12 highly relevant, specific, and descriptive tags (e.g., including specific technology names, concept fields, career domains, platforms, or related algorithms). Avoid generic tags.


You must output a JSON object matching this structure:
{{
  "blog_title": "The final approved title of the blog",
  "meta_description": "A compelling meta description under 160 characters containing the focus keyword.",
  "focus_keyword": "The primary keyword",
  "secondary_keywords": ["keyword 1", "keyword 2"],
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8"],
  "sections": [
    {{
      "section_index": 1,
      "title": "Descriptive, topic-specific H2 Title passing the specificity test",
      "section_type": "conceptual",
      "target_word_count": 350,
      "key_points": [
        "Detail explanation point 1",
        "Detail explanation point 2"
      ],
      "assigned_facts": [
        "fact_1"
      ],
      "assigned_keywords": [
        "keyword 1"
      ],
      "include_table": false,
      "include_code_block": false,
      "component_directives": [
        "comparison_widget"
      ],
      "maps_to_paa": "Optional PAA question this section answers",
      "is_final_section": false
    }}
  ]
}}

Return ONLY valid raw JSON. Do not include any explanations, markdown code blocks, or leading/trailing text. Do not wrap in backticks."""

def slugify(text: str) -> str:
    """Helper to convert title to a url-friendly lowercase slug with hyphens."""
    s = text.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[-\s]+", "-", s)
    return s

def planner_node(state: dict) -> dict:
    """
    LangGraph node that generates the structured blog outline (list of SectionBriefs) and meta description.
    """
    print("\n--- Running Node: Planner Node ---")
    topic = state.get("topic", "")
    category = state.get("category", "")
    seo_context = state.get("seo_context", {})
    retrieved_context = state.get("retrieved_context", {})
    section_count_target = state.get("section_count_target", 5)
    word_count_target = state.get("word_count_target", 1800)
    audience_level = state.get("audience_level", "fresher")
    
    # We use the medium model for structuring/planning tasks
    llm = get_llm("medium", temperature=0.3)
    
    verified_facts = retrieved_context.get("verified_facts", [])
    leetcode_data = retrieved_context.get("leetcode_data", None)
    roadmap_data = retrieved_context.get("roadmap_data", None)
    
    # 1. Build compact token-saving overviews
    leetcode_overview = "None"
    if leetcode_data and isinstance(leetcode_data, list):
        tag = retrieved_context.get("leetcode_tag", "DSA Tag")
        leetcode_overview = f"LeetCode Tag: '{tag}' containing {len(leetcode_data)} curated coding problems."
        
    roadmap_overview = "None"
    if roadmap_data and isinstance(roadmap_data, dict):
        title_val = roadmap_data.get("title", roadmap_data.get("roadmap_title", "Custom Developer Path"))
        steps = roadmap_data.get("steps", [])
        step_list = [f"Step {s.get('step', i)}: {s.get('topic')}" for i, s in enumerate(steps, 1)]
        roadmap_overview = f"Roadmap Title: '{title_val}'\nSteps:\n" + "\n".join([f"  - {step}" for step in step_list])
    
    dynamic_prompt = f"""
---
Target Blog Title: {topic}
Blog Category: {category}
Audience Level: {audience_level}
Section Count Target: {section_count_target}
Word Count Target: {word_count_target}

SEO Context:
{json.dumps(seo_context, indent=2)}

Verified Grounding Facts List:
{json.dumps(verified_facts, indent=2)}

Grounding Database Overviews:
- LeetCode Data Overview: {leetcode_overview}
- Roadmap Data Overview:
{roadmap_overview}

Output Outline JSON:"""

    prompt = PLANNER_SYSTEM_PROMPT + dynamic_prompt
    
    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        
        parsed_dict = parse_json_robustly(content)
        
        # Validate sections using Pydantic SectionBrief structure
        sections_data = parsed_dict.get("sections", [])
        validated_briefs = []
        for i, sec in enumerate(sections_data, 1):
            # Ensure index is consistent
            sec["section_index"] = i
            # Mark the last section
            sec["is_final_section"] = (i == len(sections_data))
            brief = SectionBrief(**sec)
            validated_briefs.append(brief.model_dump() if hasattr(brief, "model_dump") else brief.dict())
            
        # Build Metadata object
        blog_title = parsed_dict.get("blog_title", topic)
        meta_desc = parsed_dict.get("meta_description", "")
        if len(meta_desc) > 160:
            meta_desc = meta_desc[:157] + "..."
            
        focus_kw = parsed_dict.get("focus_keyword", seo_context.get("primary_keyword", topic))
        if "," in focus_kw:
            focus_kw = focus_kw.split(",")[0]
            
        secondary_kws = parsed_dict.get("secondary_keywords", seo_context.get("secondary_keywords", []))
        tags = parsed_dict.get("tags", [category.replace(" ", "-").lower()])
        
        metadata_obj = BlogMetadata(
            title=blog_title,
            slug=slugify(blog_title),
            date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            category=category,
            tags=tags,
            meta_description=meta_desc,
            focus_keyword=focus_kw,
            secondary_keywords=secondary_kws,
            word_count=0,
            quality_score=0.0,
            revision_count=0,
            prompt_version=config.PROMPT_VERSION,
            seo_warnings=[]
        )
        
        metadata_dict = metadata_obj.model_dump() if hasattr(metadata_obj, "model_dump") else metadata_obj.dict()
        
        print(f"Outline planned successfully with {len(validated_briefs)} sections.")
        return {
            "outline": parsed_dict,
            "section_briefs": validated_briefs,
            "metadata": metadata_dict
        }
        
    except Exception as e:
        print(f"Error executing Planner Node: {e}. Generating fallback section outline.")
        # Fallback Section Outline
        fallback_briefs = []
        sec_words = word_count_target // section_count_target
        for i in range(1, section_count_target + 1):
            is_last = (i == section_count_target)
            title = f"Descriptive Technical and Preparation Overview Section {i}"
            sec_type = "intro" if i == 1 else ("summary" if is_last else "conceptual")
            comp_directives = []
            if i == 2:
                comp_directives.append("table")
            elif i == 3:
                comp_directives.append("code_block")
            elif is_last:
                comp_directives.append("quiz")
                
            brief = SectionBrief(
                section_index=i,
                title=title,
                section_type=sec_type,
                target_word_count=sec_words,
                key_points=[f"Overview of core preparation concepts part {i}"],
                assigned_facts=["fact_1", "fact_2"] if verified_facts and len(verified_facts) >= 2 else (["fact_1"] if verified_facts else []),
                assigned_keywords=[seo_context.get("primary_keyword", "")] if i == 1 else [],
                include_table=(i == 2),
                include_code_block=(i == 3),
                component_directives=comp_directives,
                maps_to_paa=None,
                is_final_section=is_last
            )
            fallback_briefs.append(brief.model_dump() if hasattr(brief, "model_dump") else brief.dict())
            
        metadata_fallback = BlogMetadata(
            title=topic,
            slug=slugify(topic),
            date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            category=category,
            tags=[category.replace(" ", "-").lower()],
            meta_description=f"Learn everything about {topic} for placements.",
            focus_keyword=seo_context.get("primary_keyword", topic),
            secondary_keywords=seo_context.get("secondary_keywords", []),
            word_count=0,
            quality_score=0.0,
            revision_count=0,
            prompt_version=config.PROMPT_VERSION,
            seo_warnings=[]
        ).dict()
        
        return {
            "outline": {"sections": fallback_briefs},
            "section_briefs": fallback_briefs,
            "metadata": metadata_fallback
        }
