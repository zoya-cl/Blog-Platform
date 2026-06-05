import json
import re
from providers.llm_factory import get_llm
from agents.utils import parse_json_robustly
import config

INTAKE_SYSTEM_PROMPT = """You are an administrative configuration assistant. Given a blog topic, category, and whether research context was retrieved, you must output a JSON configuration mapping exactly the parameters needed to compile this blog post.

You must choose values adhering to these strict rules:
1. 'audience_level': "fresher" or "intermediate" (use "fresher" for guides, roadmaps, interview questions; "intermediate" for advanced concepts or tech stacks).
2. 'word_count_target': integer (select based on the configured category limit: Placement Roadmaps/Complete Prep: 2200; DSA/Interview Collections/Concepts: 2000; Others: 1600).
3. 'section_count_target': integer (select dynamically between 4 and 8. If the topic is broad and requires rich, diverse deep-dives, select a higher count like 6-8. If the topic is focused and requires extremely deep analysis of a few areas, select a lower count like 4-5).
4. 'writer_template': string name representing the prompt layout for this category (e.g. 'roadmap_template', 'interview_collection_template', 'techstack_template', or 'standard_template').
5. 'hallucination_checklist': string ID of the checklist to load (must be one of: 'Job Role and Career Trends', 'Resume Writing', 'Placement Roadmaps', 'Interview Question Collections', 'DSA and Coding', 'Comparison Articles', 'AI Technology', 'Developer Technology').
You must output ONLY valid JSON in this format:
{{
  "audience_level": "fresher",
  "word_count_target": 1800,
  "section_count_target": 5,
  "writer_template": "standard_template",
  "hallucination_checklist": "dsa_and_coding"
}}

Do not write any intro, markdown wrap, backticks, or explanation. Only return raw JSON."""

def intake_node(state: dict) -> dict:
    """
    LangGraph node that determines generation configuration parameters for the pipeline based on the category.
    """
    print("\n--- Running Node: Intake Node ---")
    topic = state.get("topic", "")
    category = state.get("category", "")
    retrieved_ctx = state.get("retrieved_context", {})
    retrieval_required = state.get("retrieval_required", False)
    
    # We load the small model for this task
    llm = get_llm("small", temperature=0.0)
    
    # Check if we have facts retrieved
    facts_count = len(retrieved_ctx.get("verified_facts", []))
    has_retrieved_context = facts_count > 0
    
    dynamic_prompt = f"""
---
Blog Topic: {topic}
Blog Category: {category}
Retrieval Required: {retrieval_required}
Retrieved Facts Count: {facts_count}
Has Retrieved Context: {has_retrieved_context}

Output Configuration JSON:"""

    prompt = INTAKE_SYSTEM_PROMPT + dynamic_prompt
    
    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        
        parsed_dict = parse_json_robustly(content)
        
        # Ensure fallback types/keys exist
        updates = {
            "audience_level": str(parsed_dict.get("audience_level", "fresher")),
            "generation_mode": "map-reduce",
            "word_count_target": int(parsed_dict.get("word_count_target", 1800)),
            "section_count_target": int(parsed_dict.get("section_count_target", 5)),
            "writer_template": str(parsed_dict.get("writer_template", "standard_template")),
            "hallucination_checklist": str(parsed_dict.get("hallucination_checklist", "generic"))
        }
        
        print(f"Intake parameters derived: Word Target: {updates['word_count_target']}, Sections: {updates['section_count_target']}, Checklist: {updates['hallucination_checklist']}")
        return updates
        
    except Exception as e:
        print(f"Warning: Intake Node LLM parsing failed: {e}. Loading default parameters.")
        # Load safe default parameters
        return {
            "audience_level": "fresher",
            "generation_mode": "map-reduce",
            "word_count_target": 1800,
            "section_count_target": 5,
            "writer_template": "standard_template",
            "hallucination_checklist": "generic"
        }
