import os
import re
import math
import json
import config
from topic_selection import queue_manager

def sanitize_title(title: str) -> str:
    """Converts title to a safe URL-friendly string."""
    s = title.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[-\s]+", "-", s)
    return s[:80]

def convert_callouts(text: str) -> str:
    """Converts GitHub alert syntax (> [!TIP]) into standard markdown blockquotes."""
    def replacer(match):
        alert_type = match.group(1).upper()
        content = match.group(2).strip()
        return f"> **[{alert_type}]**\n> {content}"
    return re.sub(r"^>\s*\[!(TIP|WARNING|NOTE|IMPORTANT|CAUTION)\]\r?\n((?:^>.*(?:\r?\n|$))*)", replacer, text, flags=re.MULTILINE)

def clean_fact_citations(text: str) -> str:
    """
    Replaces raw [fact_N](url) or [fact_N] citations with human-readable domain names like [Glassdoor](url).
    """
    from urllib.parse import urlparse
    
    def replacer(match):
        url = match.group(1)
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            if domain.startswith("www."):
                domain = domain[4:]
            if "." in domain:
                name = domain.split(".")[0]
                source_name = name.capitalize()
            else:
                source_name = domain.capitalize() if domain else "Source"
        except Exception:
            source_name = "Source"
        return f"[{source_name}]({url})"
        
    return re.sub(r"\[fact_\d+\]\((.*?)\)", replacer, text)

def strip_banned_phrases(text: str) -> str:
    """Programmatically removes any occurrences of config.BANNED_PHRASES from final content and cleans orphaned punctuation."""
    for phrase in getattr(config, "BANNED_PHRASES", []):
        pattern = re.compile(r"\b" + re.escape(phrase) + r"\b", re.IGNORECASE)
        text = pattern.sub("", text)
    # Clean up orphaned leading punctuation created by stripping (e.g. ", while..." or ". ,")
    text = re.sub(r"(?m)^\s*[,;:]\s*", "", text)
    text = re.sub(r"\.\s*[,;:]\s*", ". ", text)
    text = re.sub(r"(?m)^\s*,\s*([a-zA-Z])", r"\1", text)
    text = re.sub(r"(?m)^\s*([a-z])", lambda m: m.group(1).upper(), text)
    text = re.sub(r"[ \t]+", " ", text)
    return text

BANNED_HEADINGS = [
    r"^#{2,4}\s+Conclusion\s*$",
    r"^#{2,4}\s+In Conclusion\s*$", 
    r"^#{2,4}\s+Summary\s*$",
    r"^#{2,4}\s+Final Thoughts\s*$",
    r"^#{2,4}\s+Wrapping Up\s*$",
]

def strip_banned_headings(text: str) -> str:
    """Removes banned heading lines entirely from the markdown."""
    for pat in BANNED_HEADINGS:
        text = re.sub(pat, "", text, flags=re.MULTILINE | re.IGNORECASE)
    return text

def strip_component_preamble(text: str) -> str:
    """Remove generic preamble sentences before COMPONENT: blocks."""
    patterns = [
        r"(?:The following|Here is a|Consider the following|Below is a|The table below)[^\n]*\n\s*\n(?=COMPONENT:)",
        r"(?:This comparison|The following comparison)[^\n]*\n\s*\n(?=COMPONENT:)",
        r"(?:To understand|To see|To compare|To illustrate)[^\n]*(?:consider|compare|see|look at)[^\n]*\n\s*\n(?=COMPONENT:)",
        r"(?:Test your knowledge|Test your understanding)[^\n]*(?:with|below|using)[^\n]*\n?\s*(?=COMPONENT:)",
    ]
    for pat in patterns:
        text = re.sub(pat, "", text, flags=re.IGNORECASE)
    return text

def detect_truncated_text(text: str) -> list:
    """
    Detect sentences that appear truncated (ending with dangling articles, prepositions, or
    internal mid-sentence missing noun phrases like 'play a in').
    Returns list of warning strings for logging.
    """
    warnings = []
    lines = text.split('\n')
    for i, line in enumerate(lines):
        stripped = line.rstrip()
        if not stripped or stripped.startswith('#') or stripped.startswith('COMPONENT:'):
            continue
        dangling_patterns = [
            # Line ends with dangling article/preposition/conjunction
            r'\b(a|an|the|and|or|but|in|on|at|to|for|with|by|of|from|is|are|was|were|can|will)\s*$',
            # Mid-sentence truncated phrase: e.g. "play a in landing", "takes a to", "is a for"
            r'\b(a|an|the)\s+(in|on|at|to|for|with|by|of|from)\b'
        ]
        for pat in dangling_patterns:
            if re.search(pat, stripped, re.IGNORECASE):
                warnings.append(f"[TRUNCATED] Line {i+1}: '{stripped[-60:]}'")
                break
    return warnings

def dedup_reference_links(text: str) -> str:
    """Remove duplicate markdown links pointing to the same URL, keeping the first occurrence."""
    from urllib.parse import urlparse
    seen_urls = set()
    
    def normalize_url(url):
        parsed = urlparse(url)
        return (parsed.netloc + parsed.path).rstrip('/')
    
    def replacer(match):
        label = match.group(1)
        url = match.group(2)
        # Skip local/internal image links
        if url.startswith('/images/') or url.startswith('images/'):
            return match.group(0)
        norm = normalize_url(url)
        if norm in seen_urls:
            # Keep just the label text without the duplicate link
            return label
        seen_urls.add(norm)
        return match.group(0)
    
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)', replacer, text)

def insert_image_blocks(text: str, generated_images: list) -> str:
    """
    Inserts IMAGE: blocks into markdown after designated sections.
    IMAGE:
    src: /images/{slug}/section-{index}.webp
    alt: Descriptive alt text
    """
    section_images = [img for img in generated_images if img.get("type") == "section_image"]
    if not section_images:
        return text

    img_by_section = {}
    for img in section_images:
        sec_num = img.get("after_section", 1)
        if sec_num not in img_by_section:
            img_by_section[sec_num] = []
        path = img.get("path", "")
        src = path if path.startswith("/") else f"/{path}"
        alt = img.get("alt_text", "Technical blog illustration")
        block = f"\n\nIMAGE:\nsrc: {src}\nalt: {alt}\n"
        img_by_section[sec_num].append(block)

    pattern = re.compile(r'(?m)(?=^##\s+)')
    sections = pattern.split(text)

    assembled_sections = []
    sec_counter = 0

    for part in sections:
        if not part.strip():
            continue
        if part.strip().startswith("##"):
            sec_counter += 1
            content = part.rstrip()
            if sec_counter in img_by_section:
                for img_block in img_by_section[sec_counter]:
                    content += img_block
            assembled_sections.append(content)
        else:
            assembled_sections.append(part.rstrip())

    return "\n\n".join(assembled_sections).strip()

EXCHANGE_RATE = 83.0  # INR per USD

def validate_currency_conversions(text: str) -> str:
    """
    Find INR amounts with USD conversions in parentheses and validate the math.
    Corrects miscalculated parentheticals (e.g. ₹2.9Cr being calculated as ~$35,000 USD).
    """
    def lpa_to_usd(lpa_val):
        return (lpa_val * 100000) / EXCHANGE_RATE
    
    def cr_to_usd(cr_val):
        return (cr_val * 10000000) / EXCHANGE_RATE
    
    def format_usd(usd_val):
        if usd_val >= 1000000:
            return f"${usd_val/1000000:.1f}M"
        elif usd_val >= 1000:
            return f"${usd_val/1000:,.0f}K"
        return f"${usd_val:,.0f}"
    
    # Pattern: ₹X-Y LPA (~$A-$B USD)
    def fix_lpa_range(match):
        low_lpa = float(match.group(1))
        high_lpa = float(match.group(2))
        low_usd = lpa_to_usd(low_lpa)
        high_usd = lpa_to_usd(high_lpa)
        return f"₹{match.group(1)}–{match.group(2)} LPA (~{format_usd(low_usd)}–{format_usd(high_usd)} USD)"
    
    # Pattern: ₹X.YCr-₹A.BCr+ (~$C-$D USD)
    def fix_cr_range(match):
        low_cr = float(match.group(1))
        high_cr = float(match.group(2))
        low_usd = cr_to_usd(low_cr)
        high_usd = cr_to_usd(high_cr)
        plus = match.group(3) or ""
        return f"₹{match.group(1)}Cr–₹{match.group(2)}Cr{plus} (~{format_usd(low_usd)}–{format_usd(high_usd)} USD)"
    
    # Fix ₹X-Y LPA (~$wrong USD) patterns
    text = re.sub(
        r'[₹?]([\d.]+)[–\-]([\d.]+)\s*LPA\s*\((?:~\s*)?\$?[\d,KkMm.]+[–\-]\$?[\d,KkMm.]+\s*USD\)',
        fix_lpa_range, text, flags=re.IGNORECASE
    )
    
    # Fix ₹X.YCr-₹A.BCr+ (~$wrong USD) patterns
    text = re.sub(
        r'[₹?]([\d.]+)\s*Cr[–\-][₹?]?([\d.]+)\s*Cr(\+)?\s*\((?:~\s*)?\$?[\d,KkMm.]+[–\-]\$?[\d,KkMm.]+\s*USD\)',
        fix_cr_range, text, flags=re.IGNORECASE
    )
    
    return text

def format_post(state: dict) -> dict:
    """
    Post-processing function:
    - Calculates word count and reading time
    - Cleans up citations and callouts
    - Programmatically strips banned phrases
    - Writes Markdown & Metadata JSON sidecar to /output
    - Marks topic as published in MongoDB
    """
    print("\n--- Running Post-Processing Formatter ---")
    
    trace_id = state.get("trace_id", "")
    topic = state.get("topic", "")
    category = state.get("category", "")
    metadata = state.get("metadata", {})
    
    final_blog = state.get("final_blog", "")
    if not final_blog:
        final_blog = state.get("assembled_draft", "")
        
    if not final_blog:
        print("Error: No blog post text found in state to format.")
        return state

    # Step 1: Initialize Word Count & Reading Time
    word_count = len(final_blog.split())
    reading_time_minutes = math.ceil(word_count / 200)
    metadata["word_count"] = word_count
    
    # Step 2: Clean Citations, Callouts, and Banned Phrases
    processed_blog = convert_callouts(final_blog)
    processed_blog = clean_fact_citations(processed_blog)
    processed_blog = dedup_reference_links(processed_blog)
    processed_blog = strip_banned_phrases(processed_blog)
    processed_blog = strip_banned_headings(processed_blog)
    processed_blog = strip_component_preamble(processed_blog)
    processed_blog = validate_currency_conversions(processed_blog)
    # Safety net: strip any leftover rewriter artifact
    processed_blog = re.sub(r"(?i)Revised Blog Draft Markdown:\s*$", "", processed_blog).strip()

    # Step 2.5: Insert IMAGE: blocks and stage thumbnail
    generated_images = state.get("generated_images", [])
    processed_blog = insert_image_blocks(processed_blog, generated_images)

    thumbnail_items = [img for img in generated_images if img.get("type") == "thumbnail"]
    if thumbnail_items:
        t_path = thumbnail_items[0].get("path", "")
        metadata["thumbnail"] = t_path if t_path.startswith("/") else f"/{t_path}"
        metadata["thumbnail_prompt"] = thumbnail_items[0].get("prompt", "")
    
    # Step 2.8: Truncation Detection
    truncation_warnings = detect_truncated_text(processed_blog)
    if truncation_warnings:
        print(f"WARNING: {len(truncation_warnings)} potentially truncated sentences detected:")
        for tw in truncation_warnings:
            print(f"  {tw}")
        metadata["truncation_warnings"] = truncation_warnings

    # Step 3: File System Setup
    _project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(_project_root, "output")
    os.makedirs(output_dir, exist_ok=True)
    
    base_name = sanitize_title(metadata.get("title", topic))
    if not base_name:
        base_name = "blog-post"
        
    md_filename = f"{base_name}.md"
    json_filename = f"{base_name}.json"
    
    md_filepath = os.path.join(output_dir, md_filename)
    json_filepath = os.path.join(output_dir, json_filename)
    
    if os.path.exists(md_filepath) or os.path.exists(json_filepath):
        suffix = trace_id[:6] if trace_id else "post"
        md_filename = f"{base_name}-{suffix}.md"
        json_filename = f"{base_name}-{suffix}.json"
        md_filepath = os.path.join(output_dir, md_filename)
        json_filepath = os.path.join(output_dir, json_filename)
        
    # Step 4: Recalculate Word Count on Cleaned Blog and Write Metadata
    word_count = len(processed_blog.split())
    reading_time_minutes = math.ceil(word_count / 200)
    metadata["word_count"] = word_count
    metadata["reading_time_minutes"] = reading_time_minutes
    # Construct and Write Metadata JSON sidecar
    quality_score = float(metadata.get("quality_score", 0.0))
    revision_count = int(metadata.get("revision_count", 0))
    
    json_data = {
        "title": metadata.get("title", topic),
        "slug": metadata.get("slug", base_name),
        "date": metadata.get("date", ""),
        "category": category,
        "blog_format": state.get("blog_format", "deep_dive"),
        "audience_level": state.get("audience_level", "fresher"),
        "tags": metadata.get("tags", []),
        "meta_description": metadata.get("meta_description", ""),
        "focus_keyword": metadata.get("focus_keyword", ""),
        "secondary_keywords": metadata.get("secondary_keywords", []),
        "word_count": word_count,
        "word_count_target": state.get("word_count_target", 0),
        "section_count_target": state.get("section_count_target", 0),
        "reading_time_minutes": reading_time_minutes,
        "quality_score": quality_score,
        "revision_count": revision_count,
        "prompt_version": int(metadata.get("prompt_version", config.PROMPT_VERSION)),
        "thumbnail": metadata.get("thumbnail", ""),
        "thumbnail_prompt": metadata.get("thumbnail_prompt", ""),
        "image_count": len([img for img in generated_images if img.get("type") == "section_image"]),
        "approved": "no"
    }
    
    with open(json_filepath, "w", encoding="utf-8") as jf:
        json.dump(json_data, jf, indent=2)
    print(f"Sidecar metadata saved: {json_filepath}")
    
    # Step 5: Write Markdown File
    header_line = (
        f"**Category:** {category} | "
        f"**Date:** {json_data['date']} | "
        f"**Word Count:** {word_count} | "
        f"**Reading Time:** {reading_time_minutes} min | "
        f"**Score:** {quality_score:.1f}/10"
    )
    
    full_markdown = f"# {json_data['title']}\n\n{header_line}\n---\n\n{processed_blog}"
    
    with open(md_filepath, "w", encoding="utf-8") as mf:
        mf.write(full_markdown)
    print(f"Final markdown blog saved: {md_filepath}")
    
    # Step 6: Save to MongoDB
    queue_manager.mark_published(
        trace_id=trace_id,
        filename=md_filename,
        score=quality_score,
        word_count=word_count,
        markdown_content=full_markdown,
        metadata_json=json.dumps(json_data)
    )
    
    state["final_blog"] = processed_blog
    metadata["word_count"] = word_count
    state["metadata"] = metadata
    
    return state
