import uuid
import sys
import json
from datetime import datetime
import config
from topic_selection import queue_manager, title_generator, dedup_checker
from retrieval.retrieval_agent import run_direct_search
from retrieval.data_formatter import format_retrieved_data

def run_pipeline_for_topic(category: str, title: str) -> dict:
    """
    Runs the complete simplified BlogGraph-AI pipeline for a title and category:
    1. Direct Tavily search + data aggregator
    2. LangGraph state machine (Planner -> Async Writer -> Assembler + FAQ -> Quality -> Publish)
    3. Post-processing Formatter (saves .md, .json, and updates MongoDB)
    """
    if category not in config.CATEGORIES:
        raise ValueError(f"Category '{category}' is invalid. Must be one of: {config.CATEGORIES}")
        
    print("\n==============================================")
    print(f"RUNNING BLOG PIPELINE: '{title}' [{category}]")
    print("==============================================")
    
    queue_manager.init_db()
    trace_id = str(uuid.uuid4())
    queue_manager.mark_in_progress(trace_id, category, title)
    
    # 1. Direct Search & Research Aggregator
    raw_logs = run_direct_search(title, category)
    retrieved_ctx_obj = format_retrieved_data(title, category, raw_logs)
    retrieved_context_dict = retrieved_ctx_obj.model_dump() if hasattr(retrieved_ctx_obj, "model_dump") else retrieved_ctx_obj.dict()
    
    seo_context_dict = {
        "primary_keyword": title,
        "secondary_keywords": [],
        "faq_candidates": [],
        "intent_signals": {}
    }
    
    # 2. Build initial state
    initial_state = {
        "trace_id": trace_id,
        "topic": title,
        "category": category,
        "seo_context": seo_context_dict,
        "retrieved_context": retrieved_context_dict,
        "prompt_version": config.PROMPT_VERSION
    }
    
    # 3. Execute LangGraph workflow
    print("\n--- Invoking LangGraph Workflow ---")
    from graph import graph
    final_state = graph.invoke(initial_state)
    
    # 4. Format & Save output
    from agents.formatter import format_post
    final_state = format_post(final_state)
    
    # 5. Local trace saving disabled (MongoDB 'blogs' collection is source of truth)
    # Trace file saving skipped

    # 6. Format for Fulcrum frontend and save to MongoDB 'blogs' collection
    try:
        from topic_selection.output_formatter import format_and_save_blog
        format_and_save_blog(trace_data=final_state)
    except Exception as e:
        print(f"Warning: Could not format and save blog for frontend: {e}")
    
    return final_state

def run_auto_pipeline() -> dict:
    """Selects a category and title automatically, then runs the full pipeline."""
    queue_manager.init_db()
    category, category_guide = queue_manager.get_next_category()
    # Pass ALL recent titles (cross-category) to prevent topic overlap
    existing_titles = queue_manager.get_all_recent_titles(months=3)
    
    candidate_title = title_generator.generate_blog_title(category, category_guide, existing_titles, [])
    print(f"Auto-selected Category: '{category}' | Title: '{candidate_title}'")
    
    return run_pipeline_for_topic(category, candidate_title)

if __name__ == "__main__":
    print("==============================================")
    print("BlogGraph-AI Simplified Pipeline Runner")
    print("==============================================")
    print("1. Run pipeline automatically (Category selection -> Direct Search -> Writer -> Publish)")
    print("2. On-Demand generation (Custom title & category)")
    
    choice = input("\nEnter choice (1 or 2, default: 1): ").strip()
    if choice == "2":
        print("\nAvailable Categories:")
        for idx, cat in enumerate(config.CATEGORIES, 1):
            print(f"  {idx}. {cat}")
            
        cat_idx = input(f"Select category (1-{len(config.CATEGORIES)}): ").strip()
        if not cat_idx.isdigit() or not (1 <= int(cat_idx) <= len(config.CATEGORIES)):
            category = config.CATEGORIES[0]
        else:
            category = config.CATEGORIES[int(cat_idx) - 1]
            
        title = input("Enter custom blog title: ").strip()
        if not title:
            patterns = getattr(queue_manager, "EXAMPLE_TITLE_PATTERNS", {}).get(category, [])
            title = title_generator.generate_blog_title(category, patterns, [], [])
            print(f"Auto-generated Title: '{title}'")
            
        final_state = run_pipeline_for_topic(category=category, title=title)
    else:
        final_state = run_auto_pipeline()
        
    metadata = final_state.get("metadata", {})
    print("\n" + "=" * 60)
    print("METADATA SUMMARY")
    print("=" * 60)
    print(json.dumps(metadata, indent=2))
    print("=" * 60)
