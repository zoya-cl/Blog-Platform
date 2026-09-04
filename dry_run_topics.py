"""
BlogGraph-AI Topic & Title Dry-Run Simulator
=============================================
Simulates N rounds of category selection + title generation
WITHOUT running the actual blog pipeline (no search, no writing, no images).

Uses real LLM calls for title generation so you can see exactly what the
pipeline would produce. Accumulates generated titles across rounds to test
whether dedup and diversity constraints actually work.

Usage:
    python dry_run_topics.py              # Default 15 rounds
    python dry_run_topics.py 20           # Custom number of rounds
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r"c:\Karm\Cantilever Intern\My Work\Blog-Platform")

import re
import time
import json
from collections import Counter

# Import the real pipeline modules
from topic_selection import queue_manager, title_generator
import config

# ─── Configuration ───────────────────────────────────────────
NUM_ROUNDS = int(sys.argv[1]) if len(sys.argv) > 1 else 15
STOP_WORDS = {"a", "an", "the", "in", "of", "for", "and", "or", "to", "is",
              "vs", "your", "how", "what", "why", "which", "that", "are",
              "from", "with", "can", "do", "does", "this", "will", "be"}

# ─── Helpers ─────────────────────────────────────────────────
def extract_keywords(title):
    words = re.findall(r'[a-z]+', title.lower())
    return set(w for w in words if w not in STOP_WORDS and len(w) > 2)

def jaccard(set_a, set_b):
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)

# ─── Dry Run ─────────────────────────────────────────────────
print("=" * 80)
print(f"  TOPIC & TITLE DRY-RUN SIMULATOR — {NUM_ROUNDS} rounds")
print("=" * 80)

queue_manager.init_db()

# Seed with existing titles from the real database
existing_titles = queue_manager.get_all_recent_titles(months=6)
print(f"\nSeeded with {len(existing_titles)} existing titles from DB + disk.\n")

generated = []        # list of {"round", "category", "title", "time_s"}
category_counts = Counter()
format_pattern_counts = Counter()

for i in range(1, NUM_ROUNDS + 1):
    print(f"─── Round {i}/{NUM_ROUNDS} ───")
    
    # 1. Select category
    category, category_guide = queue_manager.get_next_category()
    category_counts[category] += 1
    
    # 2. Generate title (real LLM call)
    start = time.time()
    try:
        title = title_generator.generate_blog_title(
            category=category,
            category_guide=category_guide,
            existing_titles=existing_titles,
            rejected_titles=[]
        )
    except Exception as e:
        title = f"[ERROR: {e}]"
    elapsed = time.time() - start
    
    # 3. Track patterns
    tl = title.lower()
    if re.search(r'\d+-\w+\s+(blueprint|roadmap)', tl):
        format_pattern_counts["N-Step/Stage Blueprint"] += 1
    if tl.startswith("myth"):
        format_pattern_counts["Myth: prefix"] += 1
    if "?" in title:
        format_pattern_counts["Question title (?)"] += 1
    if "2026" in title:
        format_pattern_counts["Year tag (2026)"] += 1
    if ":" in title:
        format_pattern_counts["Colon structure"] += 1
    if "actually" in tl:
        format_pattern_counts["Contains 'actually'"] += 1

    generated.append({
        "round": i,
        "category": category,
        "title": title,
        "time_s": round(elapsed, 1)
    })
    
    # 4. Add to existing_titles for next round's dedup
    existing_titles.append(title)
    
    print(f"  Cat: {category:<28} | Title: {title}")
    print(f"  Time: {elapsed:.1f}s\n")

# ─── Analysis Report ─────────────────────────────────────────
print("\n" + "=" * 80)
print("  ANALYSIS REPORT")
print("=" * 80)

# A. Category Distribution
print("\n── A. Category Distribution ──")
total = sum(category_counts.values())
for cat in config.CATEGORIES:
    count = category_counts.get(cat, 0)
    pct = count / total * 100 if total else 0
    bar = "█" * count
    flag = " ⚠️ ZERO" if count == 0 else (" ⚠️ OVERWEIGHT" if pct > 30 else "")
    print(f"  {cat:<30} {count:>2}/{total} ({pct:>4.0f}%) {bar}{flag}")

# B. All Generated Titles (numbered)
print("\n── B. All Generated Titles ──")
for g in generated:
    print(f"  {g['round']:>2}. [{g['category']:<25}] {g['title']}")

# C. Structural Patterns
print("\n── C. Structural Pattern Frequency ──")
for pattern, count in format_pattern_counts.most_common():
    pct = count / total * 100
    flag = " ⚠️" if pct > 30 else ""
    print(f"  {pattern:<30} {count:>2}/{total} ({pct:.0f}%){flag}")

# D. Keyword Overlap (all pairs with >25% Jaccard)
print("\n── D. Near-Duplicate Detection (Jaccard > 25%) ──")
dupes_found = 0
for i in range(len(generated)):
    for j in range(i + 1, len(generated)):
        kw_i = extract_keywords(generated[i]["title"])
        kw_j = extract_keywords(generated[j]["title"])
        sim = jaccard(kw_i, kw_j)
        if sim > 0.25:
            dupes_found += 1
            shared = sorted(kw_i & kw_j)
            print(f"\n  ⚠️ OVERLAP ({sim:.0%}) — shared: {shared}")
            print(f"    #{generated[i]['round']:>2}: {generated[i]['title']}")
            print(f"    #{generated[j]['round']:>2}: {generated[j]['title']}")

if dupes_found == 0:
    print("  ✅ No near-duplicate pairs detected!")

# E. Also check against the ORIGINAL existing titles
print("\n── E. Overlap With Pre-Existing Blogs ──")
pre_existing = queue_manager.get_all_recent_titles(months=6)
# Remove titles we just generated
original_titles = [t for t in pre_existing if t not in [g["title"] for g in generated]]

overlap_with_old = 0
for g in generated:
    kw_new = extract_keywords(g["title"])
    for old_title in original_titles:
        kw_old = extract_keywords(old_title)
        sim = jaccard(kw_new, kw_old)
        if sim > 0.25:
            overlap_with_old += 1
            print(f"\n  ⚠️ OVERLAP ({sim:.0%}) with existing blog:")
            print(f"    NEW #{g['round']:>2}: {g['title']}")
            print(f"    OLD:       {old_title}")

if overlap_with_old == 0:
    print("  ✅ No new titles overlap with existing published blogs!")

# F. Title Length Stats
print("\n── F. Title Length Distribution ──")
lengths = [len(g["title"]) for g in generated]
print(f"  Min: {min(lengths)} chars | Max: {max(lengths)} chars | Avg: {sum(lengths)/len(lengths):.0f} chars")
too_long = [g for g in generated if len(g["title"]) > 80]
if too_long:
    print(f"  ⚠️ {len(too_long)} titles exceed 80 chars (bad for SEO):")
    for g in too_long:
        print(f"    #{g['round']}: {g['title']} ({len(g['title'])} chars)")

# G. Summary Scorecard
print("\n" + "=" * 80)
print("  SCORECARD")
print("=" * 80)
issues = []
if any(c == 0 for c in [category_counts.get(cat, 0) for cat in config.CATEGORIES]):
    issues.append("❌ Category starvation: Some categories got 0 selections")
if dupes_found > 0:
    issues.append(f"❌ {dupes_found} near-duplicate title pairs within this run")
if overlap_with_old > 0:
    issues.append(f"❌ {overlap_with_old} new titles overlap with existing blogs")
if format_pattern_counts.get("Myth: prefix", 0) > 2:
    issues.append(f"❌ 'Myth:' prefix appeared {format_pattern_counts['Myth: prefix']} times")
if format_pattern_counts.get("Colon structure", 0) / total > 0.7:
    issues.append(f"❌ Colon-split titles at {format_pattern_counts['Colon structure']}/{total} ({format_pattern_counts['Colon structure']/total*100:.0f}%)")
if format_pattern_counts.get("Year tag (2026)", 0) / total > 0.4:
    issues.append(f"❌ '2026' in {format_pattern_counts['Year tag (2026)']}/{total} titles ({format_pattern_counts['Year tag (2026)']/total*100:.0f}%)")
if format_pattern_counts.get("Contains 'actually'", 0) / total > 0.3:
    issues.append(f"❌ 'Actually' overused in {format_pattern_counts["Contains 'actually'"]}/{total} titles ({format_pattern_counts["Contains 'actually'"]/total*100:.0f}%)")

if not issues:
    print("  ✅ ALL CHECKS PASSED — topic selection and title diversity look healthy!")
else:
    for iss in issues:
        print(f"  {iss}")

print(f"\nDry run complete. {NUM_ROUNDS} titles generated in {sum(g['time_s'] for g in generated):.0f}s total.")
