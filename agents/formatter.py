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

    # Step 1: Calculate Word Count & Reading Time
    word_count = len(final_blog.split())
    reading_time_minutes = math.ceil(word_count / 200)
    metadata["word_count"] = word_count
    
    # Step 2: Clean Citations, Callouts, and Banned Phrases
    processed_blog = convert_callouts(final_blog)
    processed_blog = clean_fact_citations(processed_blog)
    processed_blog = strip_banned_phrases(processed_blog)

    # Step 2.5: Insert IMAGE: blocks and stage thumbnail
    generated_images = state.get("generated_images", [])
    processed_blog = insert_image_blocks(processed_blog, generated_images)

    thumbnail_items = [img for img in generated_images if img.get("type") == "thumbnail"]
    if thumbnail_items:
        t_path = thumbnail_items[0].get("path", "")
        metadata["thumbnail"] = t_path if t_path.startswith("/") else f"/{t_path}"
        metadata["thumbnail_prompt"] = thumbnail_items[0].get("prompt", "")
    
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
        
    # Step 4: Construct and Write Metadata JSON sidecar
    quality_score = float(metadata.get("quality_score", 0.0))
    revision_count = int(metadata.get("revision_count", 0))
    
    json_data = {
        "title": metadata.get("title", topic),
        "slug": metadata.get("slug", base_name),
        "date": metadata.get("date", ""),
        "category": category,
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
