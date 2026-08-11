"""
Blog Engine - Simplified Module Test Suite
Run individual pipeline stages or full pipeline end-to-end.
Saves intermediate module outputs into /output/module_outputs/ for testing and inspection.

Usage:
  python test_modules.py              # Interactive menu
  python test_modules.py all          # Runs all modules
  python test_modules.py <1-4>        # Runs specific module
"""

import sys
import os
import json
import time
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

def print_header(title):
    print("\n" + "="*70)
    print(f"   {title}")
    print("="*70)

def ensure_output_dir():
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "module_outputs")
    os.makedirs(out_dir, exist_ok=True)
    return out_dir

def save_module_output(filename: str, data: dict):
    out_dir = ensure_output_dir()
    filepath = os.path.join(out_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"   [Saved Module Artifact -> {filepath}]")

TEST_STATE = {}

def test_module_1_title_generator():
    """Module 1: Title Generator"""
    print_header("MODULE 1: Title Generation & Deduplication")
    from topic_selection.title_generator import generate_blog_title
    
    category = random.choice(config.CATEGORIES)
    print(f"Category: '{category}'")
    
    start_time = time.time()
    title = generate_blog_title(category=category, example_patterns=["System Design Guide"])
    elapsed = time.time() - start_time
    
    print(f"   -> Title: '{title}' ({elapsed:.2f}s)")
    TEST_STATE["category"] = category
    TEST_STATE["title"] = title
    
    save_module_output("module_1_title.json", {
        "category": category,
        "title": title,
        "elapsed_seconds": round(elapsed, 2)
    })
    return True

def test_module_2_search_and_planner():
    """Module 2: Direct Search & Planner Node"""
    print_header("MODULE 2: Direct Search & Planner Node")
    from retrieval.retrieval_agent import run_direct_search
    from retrieval.data_formatter import format_retrieved_data
    from agents.planner import planner_node
    
    if "title" not in TEST_STATE:
        test_module_1_title_generator()
        
    title = TEST_STATE["title"]
    category = TEST_STATE["category"]
    
    print(f"Running Direct Search for: '{title}'")
    start_time = time.time()
    raw_logs = run_direct_search(title, category)
    retrieved_ctx = format_retrieved_data(title, category, raw_logs)
    search_elapsed = time.time() - start_time
    
    print(f"Running Planner Node...")
    planner_state = {
        "topic": title,
        "category": category,
        "seo_context": {"primary_keyword": title},
        "retrieved_context": retrieved_ctx.model_dump()
    }
    planner_start = time.time()
    plan_result = planner_node(planner_state)
    planner_elapsed = time.time() - planner_start
    
    print(f"   -> Search Time:  {search_elapsed:.2f}s")
    print(f"   -> Planner Time: {planner_elapsed:.2f}s")
    print(f"   -> Format:       {plan_result.get('blog_format')}")
    print(f"   -> Word Target:  {plan_result.get('word_count_target')}")
    print(f"   -> Sections:     {len(plan_result.get('section_briefs', []))}")
    
    TEST_STATE.update(planner_state)
    TEST_STATE.update(plan_result)
    
    save_module_output("module_2_planner.json", {
        "title": title,
        "category": category,
        "retrieved_facts_count": len(retrieved_ctx.verified_facts),
        "sources": retrieved_ctx.sources,
        "blog_format": plan_result.get("blog_format"),
        "word_count_target": plan_result.get("word_count_target"),
        "section_count_target": plan_result.get("section_count_target"),
        "outline": plan_result.get("outline"),
        "section_briefs": plan_result.get("section_briefs"),
        "metadata": plan_result.get("metadata"),
        "search_elapsed_seconds": round(search_elapsed, 2),
        "planner_elapsed_seconds": round(planner_elapsed, 2)
    })
    return True

def test_module_3_writer_and_assembler():
    """Module 3: Parallel Writer & Assembler + FAQ"""
    print_header("MODULE 3: Parallel Writer & Assembler + FAQ")
    from agents.writer import writer_async
    from agents.assembler import assembler
    
    if "section_briefs" not in TEST_STATE:
        test_module_2_search_and_planner()
        
    print(f"Writing {len(TEST_STATE['section_briefs'])} sections in parallel...")
    start_time = time.time()
    write_result = writer_async(TEST_STATE)
    write_elapsed = time.time() - start_time
    
    TEST_STATE.update(write_result)
    
    print("Assembling draft & generating Auto-FAQ...")
    assemble_start = time.time()
    assemble_result = assembler(TEST_STATE)
    assemble_elapsed = time.time() - assemble_start
    
    draft = assemble_result.get("assembled_draft", "")
    words = len(draft.split())
    
    print(f"   -> Writer Time:    {write_elapsed:.2f}s")
    print(f"   -> Assembler Time: {assemble_elapsed:.2f}s")
    print(f"   -> Total Draft Words: {words}")
    
    TEST_STATE.update(assemble_result)
    
    save_module_output("module_3_drafts.json", {
        "title": TEST_STATE.get("title", TEST_STATE.get("topic")),
        "section_drafts": write_result.get("section_drafts", []),
        "assembled_draft": draft,
        "draft_word_count": words,
        "writer_elapsed_seconds": round(write_elapsed, 2),
        "assembler_elapsed_seconds": round(assemble_elapsed, 2)
    })
    return True

def test_module_4_full_pipeline():
    """Module 4: Quality Check & Publish (Full Pipeline)"""
    print_header("MODULE 4: Quality & Publish Node")
    from agents.quality import quality_node
    from graph import publish_node
    from agents.formatter import format_post
    
    if "assembled_draft" not in TEST_STATE:
        out_dir = ensure_output_dir()
        m3_file = os.path.join(out_dir, "module_3_drafts.json")
        m2_file = os.path.join(out_dir, "module_2_planner.json")
        
        if os.path.exists(m3_file):
            print("Loading state from saved module_3_drafts.json...")
            with open(m3_file, "r", encoding="utf-8") as f:
                TEST_STATE.update(json.load(f))
            if os.path.exists(m2_file):
                with open(m2_file, "r", encoding="utf-8") as f:
                    TEST_STATE.update(json.load(f))
        else:
            print("No prior test state found. Generating full pipeline from scratch...")
            from run import run_pipeline_for_topic
            category = random.choice(config.CATEGORIES)
            title = TEST_STATE.get("title", f"Modern {category} Architecture and Practices in 2026")
            final_state = run_pipeline_for_topic(category, title)
            TEST_STATE.update(final_state)
            return True

    print("Evaluating Quality & Formatter for active test state...")
    start_time = time.time()
    
    # 1. Quality evaluation pass 1
    q_result = quality_node(TEST_STATE)
    TEST_STATE.update(q_result)
    
    # 2. Quality Gate check: If score < threshold, trigger quality_rewriter pass
    scores = TEST_STATE.get("quality_scores", {})
    overall_score = float(scores.get("overall_score", 0.0))
    threshold = getattr(config, "QUALITY_GATE_THRESHOLD", 7.5)
    rev_count = TEST_STATE.get("quality_revision_count", 0)
    
    if overall_score < threshold and rev_count < 1:
        print(f"\n[Quality Gate] Score {overall_score:.1f} < Threshold {threshold:.1f}. Triggering Quality Rewriter pass...")
        from agents.quality import quality_rewriter
        rw_result = quality_rewriter(TEST_STATE)
        TEST_STATE.update(rw_result)
        
        print("\n[Quality Gate] Re-evaluating Quality Grader after rewrite pass...")
        q2_result = quality_node(TEST_STATE)
        TEST_STATE.update(q2_result)
    else:
        print(f"[Quality Gate] Score {overall_score:.1f} passed threshold ({threshold:.1f}) or max retries reached.")
        
    pub_result = publish_node(TEST_STATE)
    TEST_STATE.update(pub_result)
    
    final_state = format_post(TEST_STATE)
    TEST_STATE.update(final_state)
    
    elapsed = time.time() - start_time
    print(f"   -> Quality & Publish Time: {elapsed:.2f}s")
        
    metadata = TEST_STATE.get("metadata", {})
    print(f"\n   -> Quality Score: {metadata.get('quality_score')}/10")
    print(f"   -> Word Count:    {metadata.get('word_count')} words")
    print(f"   -> Article Slug:  {metadata.get('slug')}")
    
    save_module_output("module_4_published.json", {
        "title": TEST_STATE.get("topic", TEST_STATE.get("title")),
        "metadata": metadata,
        "quality_scores": TEST_STATE.get("quality_scores")
    })
    
    # Also save the raw markdown blog post directly for easy previewing
    out_dir = ensure_output_dir()
    md_path = os.path.join(out_dir, "module_4_output.md")
    final_md = TEST_STATE.get("final_blog", TEST_STATE.get("assembled_draft", ""))
    with open(md_path, "w", encoding="utf-8") as mf:
        mf.write(final_md)
    print(f"   [Saved Final Markdown Blog -> {md_path}]")
    
    save_module_output("full_pipeline_test_trace.json", TEST_STATE)
    return True

def run_all_modules():
    print_header("RUNNING ALL SIMPLIFIED PIPELINE MODULES")
    start = time.time()
    test_module_1_title_generator()
    test_module_2_search_and_planner()
    test_module_3_writer_and_assembler()
    test_module_4_full_pipeline()
    total = time.time() - start
    print_header(f"ALL MODULES COMPLETED SUCCESSFULLY in {total:.2f}s!")
    print(f"\n[+] All module artifacts saved to: {ensure_output_dir()}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1].strip().lower()
        if arg == "all" or arg == "0":
            run_all_modules()
        elif arg == "1":
            test_module_1_title_generator()
        elif arg == "2":
            test_module_2_search_and_planner()
        elif arg == "3":
            test_module_3_writer_and_assembler()
        elif arg == "4":
            test_module_4_full_pipeline()
        else:
            print("Unknown argument. Running full test suite...")
            run_all_modules()
    else:
        print("\n" + "="*50)
        print("BLOG ENGINE - SIMPLIFIED MODULE TEST SUITE")
        print("="*50)
        print("0. Run ALL modules end-to-end")
        print("1. Module 1: Title Generator")
        print("2. Module 2: Direct Search & Planner Node")
        print("3. Module 3: Parallel Writer & Assembler + FAQ")
        print("4. Module 4: Quality & Publish Node")
        
        choice = input("\nSelect choice (0-4, default 0): ").strip()
        if choice == "1":
            test_module_1_title_generator()
        elif choice == "2":
            test_module_2_search_and_planner()
        elif choice == "3":
            test_module_3_writer_and_assembler()
        elif choice == "4":
            test_module_4_full_pipeline()
        else:
            run_all_modules()
