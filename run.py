import uuid
import sys
from datetime import datetime
import config
from topic_selection import queue_manager, title_generator, dedup_checker
from seo_processing import (
    query_normalizer_expander,
    autocomplete_fetcher,
    paa_fetcher,
    seo_cleaner,
    seo_context_builder
)
from retrieval.retrieval_cache import load_retrieval_cache, save_retrieval_cache
from retrieval.category_tool_router import get_tools_for_category
from retrieval.retrieval_agent import run_retrieval_agent
from retrieval.data_formatter import format_retrieved_data


def run_phase_0(max_category_attempts: int = 5) -> dict:
    """
    Orchestrates the Phase 0 topic selection and registration,
    and runs Stage 1 (SEO Pre-Processing) sequentially.
    
    Returns:
        dict: The initial BlogState containing trace_id, topic, category, and seo_context.
    """
    print("Initializing Database...")
    queue_manager.init_db()
    
    for cat_attempt in range(1, max_category_attempts + 1):
        print(f"\n--- Category Selection Attempt {cat_attempt}/{max_category_attempts} ---")
        category, patterns = queue_manager.get_next_category()
        print(f"Selected Category (Seasonal Weighted): '{category}'")
        print(f"Example Patterns:\n" + "\n".join([f"  - {p}" for p in patterns[:3]]))

        # Fetch existing titles for the same category from the last 3 months
        existing_titles = queue_manager.get_recent_titles(category, months=3)
        print(f"Loaded {len(existing_titles)} recent titles for '{category}' from database for deduplication.")

        success = False
        approved_title = None
        rejected_titles = []
        
        # Propose titles up to the retry cap from config
        retry_cap = config.RETRY_CAPS.get("title_dedup", 3)
        for title_attempt in range(1, retry_cap + 1):
            print(f"Generating title candidate (Attempt {title_attempt}/{retry_cap})...")
            candidate_title = title_generator.generate_blog_title(category, patterns, existing_titles, rejected_titles)
            print(f"Candidate Title: '{candidate_title}'")
            
            is_unique = dedup_checker.is_title_unique(candidate_title, existing_titles, category)
            if is_unique:
                approved_title = candidate_title
                success = True
                print("Title passed deduplication check!")
                break
            else:
                print(f"Title candidate rejected: Duplicate or highly similar to an existing title.")
                rejected_titles.append(candidate_title)
        
        if success and approved_title:
            trace_id = str(uuid.uuid4())
            print(f"Registering topic in SQLite queue with Trace ID: {trace_id}")
            queue_manager.mark_in_progress(trace_id, category, approved_title)
            print(f"SUCCESS: Registered '{approved_title}' under '{category}'.")
            
            # Check if API keys are present (if not, we generate mock/simulated context for the dry run)
            has_key = bool(config.GROQ_API_KEY) or bool(config.NVIDIA_API_KEY)
            if not has_key:
                print("NOTE: No API keys detected. Generating simulated SEOContext & RetrievedContext...")
                mock_context = {
                    "primary_keyword": "simulated placement prep key",
                    "secondary_keywords": ["mock SDE guide", "mock questions"],
                    "faq_candidates": ["What is SDE?", "How to prepare?"],
                    "intent_signals": {
                        "beginner": True,
                        "placement_oriented": True,
                        "technology_specific": ["mock"],
                        "comparison": False,
                        "freshness": False
                    },
                    "normalized_query": "simulated placement prep key",
                    "expanded_queries": ["mock SDE guide"]
                }
                blog_state = {
                    "trace_id": trace_id,
                    "topic": approved_title,
                    "category": category,
                    "seo_context": mock_context,
                    "retrieved_context": {
                        "verified_facts": [{"claim": "Mock fact for placement prep", "source_url": "https://example.com", "retrieved_at": "2026-05-28"}],
                        "salary_ranges": {"Mock SDE Role": "6-10 LPA"},
                        "skill_requirements": ["Python", "DSA"],
                        "tech_stacks": ["Git", "GitHub"],
                        "student_experiences": ["Mock candidate interview experience"],
                        "sources": ["https://example.com"]
                    },
                    "retrieval_required": False,
                    "retrieval_depth": "none"
                }
                return blog_state
                
            # Stage 1 — SEO Pre-Processing
            print("\n==============================================")
            print("RUNNING STAGE 1 — SEO PRE-PROCESSING")
            print("==============================================")
            
            print("Running query normalization & expansion...")
            normalized = query_normalizer_expander.normalize_and_expand_query(approved_title, category=category)
            
            print("Fetching Google Autocomplete suggestions...")
            raw_suggestions = autocomplete_fetcher.fetch_autocomplete_suggestions(normalized["expanded_queries"])
            
            print("Fetching People Also Ask questions...")
            paa_questions = paa_fetcher.fetch_paa_questions(normalized["primary_query"])
            
            print("Running LLM semantic filter & curation...")
            curated_data = seo_cleaner.clean_and_curate_seo_data(
                title=approved_title,
                primary_query=normalized["primary_query"],
                raw_suggestions_dict=raw_suggestions,
                paa_questions=paa_questions
            )
            
            print("Building validated SEOContext object...")
            seo_context = seo_context_builder.build_seo_context(
                curated_seo_data=curated_data,
                normalized_query=normalized["primary_query"],
                expanded_queries_dict=normalized["expanded_queries"]
            )
            
            seo_context_dict = seo_context.model_dump() if hasattr(seo_context, "model_dump") else seo_context.dict()
            
            # Stage 2 — Retrieval Ingestion Layer
            depth = config.RETRIEVAL_DEPTHS.get(category, "none")
            retrieval_required = (depth != "none")
            
            print("\n==============================================")
            print("RUNNING STAGE 2 — RETRIEVAL INGESTION")
            print("==============================================")
            print(f"Retrieval Depth for '{category}': {depth}")
            
            retrieved_context_dict = {
                "verified_facts": [],
                "salary_ranges": {},
                "skill_requirements": [],
                "tech_stacks": [],
                "student_experiences": [],
                "sources": []
            }
            
            if retrieval_required:
                # Check cache first
                cached_ctx = load_retrieval_cache(trace_id)
                if cached_ctx is not None:
                    print(f"CACHE HIT: Loaded retrieved context for trace {trace_id}.")
                    retrieved_context_dict = cached_ctx.model_dump() if hasattr(cached_ctx, "model_dump") else cached_ctx.dict()
                else:
                    print(f"CACHE MISS: Executing ReAct retrieval agent for trace {trace_id}...")
                    # Get routing tools
                    active_tools = get_tools_for_category(category, depth)
                    print(f"Active tools: {[t.name for t in active_tools]}")
                    
                    # Run agent
                    raw_logs = run_retrieval_agent(approved_title, category, seo_context_dict, active_tools, depth)
                    
                    # Run the Research Aggregator to structure raw logs
                    retrieved_ctx_obj = format_retrieved_data(approved_title, category, raw_logs)
                    
                    # Save to cache
                    save_retrieval_cache(trace_id, approved_title, retrieved_ctx_obj)
                    
                    retrieved_context_dict = retrieved_ctx_obj.model_dump() if hasattr(retrieved_ctx_obj, "model_dump") else retrieved_ctx_obj.dict()
            else:
                print("Retrieval is not required for this category. Skipping retrieval agent execution.")

            blog_state = {
                "trace_id": trace_id,
                "topic": approved_title,
                "category": category,
                "seo_context": seo_context_dict,
                "retrieved_context": retrieved_context_dict,
                "retrieval_required": retrieval_required,
                "retrieval_depth": depth
            }
            
            print(f"SUCCESS: Stage 2 Retrieval Ingestion completed.")
            return blog_state
        else:
            print(f"Warning: Failed to generate a unique title for category '{category}' after {retry_cap} attempts. Skipping category...")
            
    print(f"Error: Exceeded max category attempts ({max_category_attempts}). Pipeline stopped.")
    sys.exit(1)


def init_blog_state(phase_0_state: dict) -> dict:
    state = phase_0_state.copy()
    defaults = {
        "running_context": "",
        "assembled_draft": "",
        "section_drafts": [],
        "section_briefs": [],
        "outline": {},
        "generation_mode": "",
        "audience_level": "",
        "word_count_target": 0,
        "section_count_target": 0,
        "writer_template": "",
        "hallucination_checklist": "",
        "hallucination_report": {},
        "hallucination_revision_count": 0,
        "quality_scores": {},
        "quality_revision_count": 0,
        "seo_audit_results": {},
        "seo_revision_count": 0,
        "seo_warnings": [],
        "final_blog": "",
        "metadata": {},
        "prompt_version": config.PROMPT_VERSION
    }
    for k, v in defaults.items():
        if k not in state:
            state[k] = v
    return state


def run_pipeline_for_topic(category: str, title: str) -> dict:
    """
    Runs the complete BlogGraph-AI pipeline for a user-specified title and category.
    """
    if category not in config.CATEGORIES:
        raise ValueError(f"Category '{category}' is invalid. Must be one of: {config.CATEGORIES}")
    queue_manager.init_db()
    trace_id = str(uuid.uuid4())
    queue_manager.mark_in_progress(trace_id, category, title)
    
    # 1. Run SEO Pre-Processing (Stage 1) & Retrieval (Stage 2)
    has_key = bool(config.GROQ_API_KEY) or bool(config.NVIDIA_API_KEY)
    if not has_key:
        print("NOTE: No API keys detected. Generating simulated SEOContext & RetrievedContext...")
        mock_context = {
            "primary_keyword": title.lower(),
            "secondary_keywords": ["mock guide", "mock questions"],
            "faq_candidates": ["What is this?", "How to prepare?"],
            "intent_signals": {
                "beginner": True,
                "placement_oriented": True,
                "technology_specific": ["mock"],
                "comparison": False,
                "freshness": False
            },
            "normalized_query": title.lower(),
            "expanded_queries": ["mock guide"]
        }
        blog_state_result = {
            "trace_id": trace_id,
            "topic": title,
            "category": category,
            "seo_context": mock_context,
            "retrieved_context": {
                "verified_facts": [{"claim": f"Mock fact for {title}", "source_url": "https://example.com", "retrieved_at": "2026-05-28"}],
                "salary_ranges": {"Mock Role": "6-10 LPA"},
                "skill_requirements": ["Python"],
                "tech_stacks": ["Git"],
                "student_experiences": ["Mock candidate interview experience"],
                "sources": ["https://example.com"]
            },
            "retrieval_required": False,
            "retrieval_depth": "none"
        }
    else:
        # Stage 1 — SEO Pre-Processing
        print("\n==============================================")
        print("RUNNING STAGE 1 — SEO PRE-PROCESSING (CUSTOM)")
        print("==============================================")
        normalized = query_normalizer_expander.normalize_and_expand_query(title, category=category)
        raw_suggestions = autocomplete_fetcher.fetch_autocomplete_suggestions(normalized["expanded_queries"])
        paa_questions = paa_fetcher.fetch_paa_questions(normalized["primary_query"])
        curated_data = seo_cleaner.clean_and_curate_seo_data(
            title=title,
            primary_query=normalized["primary_query"],
            raw_suggestions_dict=raw_suggestions,
            paa_questions=paa_questions
        )
        seo_context = seo_context_builder.build_seo_context(
            curated_seo_data=curated_data,
            normalized_query=normalized["primary_query"],
            expanded_queries_dict=normalized["expanded_queries"]
        )
        seo_context_dict = seo_context.model_dump() if hasattr(seo_context, "model_dump") else seo_context.dict()
        
        # Stage 2 — Retrieval Ingestion Layer
        depth = config.RETRIEVAL_DEPTHS.get(category, "none")
        retrieval_required = (depth != "none")
        
        print("\n==============================================")
        print("RUNNING STAGE 2 — RETRIEVAL INGESTION (CUSTOM)")
        print("==============================================")
        
        retrieved_context_dict = {
            "verified_facts": [],
            "salary_ranges": {},
            "skill_requirements": [],
            "tech_stacks": [],
            "student_experiences": [],
            "sources": []
        }
        
        if retrieval_required:
            active_tools = get_tools_for_category(category, depth)
            raw_logs = run_retrieval_agent(title, category, seo_context_dict, active_tools, depth)
            retrieved_ctx_obj = format_retrieved_data(title, category, raw_logs)
            retrieved_context_dict = retrieved_ctx_obj.model_dump() if hasattr(retrieved_ctx_obj, "model_dump") else retrieved_ctx_obj.dict()
            
        blog_state_result = {
            "trace_id": trace_id,
            "topic": title,
            "category": category,
            "seo_context": seo_context_dict,
            "retrieved_context": retrieved_context_dict,
            "retrieval_required": retrieval_required,
            "retrieval_depth": depth
        }
        
    # 2. Run graph workflow (Stages 3-7)
    full_state = init_blog_state(blog_state_result)
    from graph import graph
    final_state = graph.invoke(full_state)
    
    # 3. Format output (which automatically saves to DB and disk)
    from agents.formatter import format_post
    final_state = format_post(final_state)
    
    return final_state



if __name__ == "__main__":
    import json
    import os
    
    print("==============================================")
    print("BlogGraph-AI Pipeline Runner")
    print("==============================================")
    print("1. Run Phase 0 (Automatic category selection, title generation, SEO pre-processing, and retrieval)")
    print("2. Run full LangGraph workflow with automatic category & title selection")
    print("3. On-Demand generation: select specific category & input custom title")
    
    choice = input("\nEnter choice (1, 2, or 3, default: 2): ").strip()
    if not choice:
        choice = "2"
        
    if choice == "3":
        print("\nAvailable Categories:")
        for idx, cat in enumerate(config.CATEGORIES, 1):
            print(f"  {idx}. {cat}")
            
        cat_idx = input(f"Select category (1-{len(config.CATEGORIES)}): ").strip()
        if not cat_idx.isdigit() or not (1 <= int(cat_idx) <= len(config.CATEGORIES)):
            print("Invalid category selected. Defaulting to first category.")
            category = config.CATEGORIES[0]
        else:
            category = config.CATEGORIES[int(cat_idx) - 1]
            
        title = input("Enter custom blog title (leave empty for auto-generation): ").strip()
        if not title:
            # Auto-generate a title for the selected category
            patterns = queue_manager.EXAMPLE_TITLE_PATTERNS.get(category, [])
            current_year = datetime.now().year
            processed_patterns = [p.replace("{year}", str(current_year)) for p in patterns]
            existing_titles = queue_manager.get_recent_titles(category, months=3)
            print("Generating title candidate...")
            title = title_generator.generate_blog_title(category, processed_patterns, existing_titles, [])
            print(f"Auto-generated Title: '{title}'")
            
        print(f"\nRunning pipeline for Category: '{category}' | Title: '{title}'")
        final_state = run_pipeline_for_topic(category=category, title=title)
        
        metadata = final_state.get("metadata", {})
        print("\n" + "=" * 60)
        print("METADATA SUMMARY (JSON)")
        print("=" * 60)
        print(json.dumps(metadata, indent=2))
        print("=" * 60)
        
    elif choice == "1":
        # Run only stage 0-2 (Phase 0)
        blog_state_result = run_phase_0()
        print("\n" + "=" * 60)
        print("PHASE 0, STAGE 1 & STAGE 2 EXECUTION COMPLETE")
        print("=" * 60)
        print(f"Category:       {blog_state_result['category']}")
        print(f"Approved Title: {blog_state_result['topic']}")
        print(f"Trace ID:       {blog_state_result['trace_id']}")
        print("-" * 60)
        
    else:
        # Run full pipeline automatically (default choice 2)
        blog_state_result = run_phase_0()
        print("\n" + "=" * 60)
        print("PHASE 0, STAGE 1 & STAGE 2 EXECUTION COMPLETE")
        print("=" * 60)
        print(f"Category:       {blog_state_result['category']}")
        print(f"Approved Title: {blog_state_result['topic']}")
        print(f"Trace ID:       {blog_state_result['trace_id']}")
        print("-" * 60)
        
        full_state = init_blog_state(blog_state_result)
        
        print("\n==============================================")
        print("RUNNING LANGGRAPH STAGE 3-7 GRAPH WORKFLOW")
        print("==============================================")
        
        from graph import graph
        final_state = graph.invoke(full_state)
        
        print("\n==============================================")
        print("LANGGRAPH GRAPH EXECUTION COMPLETE")
        print("==============================================")
        
        from agents.formatter import format_post
        final_state = format_post(final_state)
        
        metadata = final_state.get("metadata", {})
        print("\n" + "=" * 60)
        print("METADATA SUMMARY (JSON)")
        print("=" * 60)
        print(json.dumps(metadata, indent=2))
        print("=" * 60)


