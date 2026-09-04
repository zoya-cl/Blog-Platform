"""
Backfill script to format and save all existing blogs from output/ into MongoDB blogs collection.
"""

import os
import glob
import sys
from topic_selection.output_formatter import format_and_save_blog

def run_backfill():
    print("=" * 60)
    print("Starting Blog Backfill to MongoDB 'blogs' collection")
    print("=" * 60)
    
    project_root = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(project_root, "output")
    
    traces = glob.glob(os.path.join(output_dir, "*-trace.json"))
    print(f"Found {len(traces)} trace files in {output_dir}\n")
    
    success_count = 0
    fail_count = 0
    
    for idx, trace_path in enumerate(traces):
        filename = os.path.basename(trace_path)
        try:
            formatted = format_and_save_blog(trace_path=trace_path, blog_index=idx)
            sec_count = len(formatted.get("sections", []))
            block_count = sum(len(s.get("body", [])) for s in formatted.get("sections", []))
            comp_count = sum(
                1 for s in formatted.get("sections", [])
                for b in s.get("body", [])
                if b.get("type") in ["quiz", "table", "comparison_widget", "roadmap", "code_block"]
            )
            print(f"[{idx+1}/{len(traces)}] SUCCESS: '{formatted['title'][:45]}...'")
            print(f"    Slug: {formatted['slug']}")
            print(f"    Category: {formatted['original_category']} -> {formatted['category']}")
            print(f"    Sections: {sec_count} | Blocks: {block_count} | Components: {comp_count}")
            success_count += 1
        except Exception as e:
            print(f"[{idx+1}/{len(traces)}] ERROR on {filename}: {e}")
            fail_count += 1
            
    print("\n" + "=" * 60)
    print(f"BACKFILL COMPLETE: {success_count} succeeded, {fail_count} failed out of {len(traces)}")
    print("=" * 60)

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    run_backfill()
