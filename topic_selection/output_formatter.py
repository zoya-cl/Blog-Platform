"""
Blog Output Formatter for Fulcrum Frontend.

Converts pipeline raw markdown and trace artifacts into structured JSON matching
the Fulcrum frontend data contract (ContentBlock[] union types) and writes to MongoDB.
"""

import os
import json
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from topic_selection.mongo_db import get_db

# Category mapping from pipeline categories to Fulcrum platform categories
CATEGORY_MAP = {
    "Placement Roadmaps": "Interview Prep",
    "Resume Writing": "Resume",
    "Comparison Articles": "Companies Test",
    "AI Technology": "Preparation",
    "Developer Technology": "Preparation",
    "Job Role and Career Trends": "Career",
}

DEFAULT_AUTHOR = {
    "name": "Fulcrum Editorial",
    "role": "Content Team",
    "avatar": "https://fulcrum-cl-images.s3.ap-south-1.amazonaws.com/gray-abstract-wireframe-technology-background+1fulcrum.png"
}

SIDEBAR_CARDS = {
    "Interview Prep": [
        {
            "type": "playbook",
            "title": "Interview Playbook",
            "description": "Master your preparation with our very famous frameworks to prepare for your next Interview.",
            "buttonText": "Try Now"
        },
        {
            "type": "dream-track",
            "title": "Dream Company Track",
            "description": "Follow a step-by-step prep roadmap tailored completely around the hiring process of your target company.",
            "buttonText": "Try Now"
        }
    ],
    "Resume": [
        {
            "type": "build-resume",
            "title": "Build ATS friendly resume",
            "description": "Use our AI Resume builder to tailor your resume with more than 10+ ATS Friendly templates",
            "buttonText": "Try Now"
        },
        {
            "type": "ats-score",
            "title": "Check Resume ATS Score",
            "description": "Find and fix hidden issues and gaps instantly to make sure your resume survives the recruiter filters.",
            "buttonText": "Try Now"
        }
    ],
    "default": [
        {
            "type": "playbook",
            "title": "Interview Playbook",
            "description": "Master your preparation with our very famous frameworks to prepare for your next Interview.",
            "buttonText": "Try Now"
        }
    ]
}


def slugify(text: str) -> str:
    """Converts heading or title to a clean URL slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text.strip("-")


def format_display_date(date_str: Optional[str]) -> str:
    """
    Converts 'YYYY-MM-DD' or ISO format into 'Month Day, Year' (e.g. 'Sep 4, 2026').
    Works reliably across Windows and Linux.
    """
    if not date_str:
        dt = datetime.now()
    else:
        try:
            if "T" in date_str:
                dt = datetime.fromisoformat(date_str)
            else:
                dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        except Exception:
            dt = datetime.now()
            
    return f"{dt.strftime('%b')} {dt.day}, {dt.year}"


def parse_props_json(raw_json: str) -> dict:
    """
    Robust JSON parser for COMPONENT block props.
    Handles trailing characters, trailing commas, and unescaped quotes.
    """
    raw_json = raw_json.strip()
    # Extract only the outermost { ... }
    idx_open = raw_json.find("{")
    idx_close = raw_json.rfind("}")
    if idx_open != -1 and idx_close != -1 and idx_close > idx_open:
        raw_json = raw_json[idx_open:idx_close + 1]
        
    try:
        return json.loads(raw_json)
    except Exception:
        pass
        
    # Clean trailing commas before closing braces/brackets
    cleaned = re.sub(r",\s*([}\]])", r"\1", raw_json)
    try:
        return json.loads(cleaned)
    except Exception:
        pass
        
    # If standard parse fails, try basic regex extraction of common keys
    extracted = {}
    m_left = re.search(r'"left_title":\s*"([^"]+)"', raw_json)
    m_right = re.search(r'"right_title":\s*"([^"]+)"', raw_json)
    if m_left:
        extracted["left_title"] = m_left.group(1)
    if m_right:
        extracted["right_title"] = m_right.group(1)
        
    m_q = re.search(r'"question":\s*"([^"]+)"', raw_json)
    if m_q:
        extracted["question"] = m_q.group(1)
        
    if extracted:
        return extracted
        
    return {"raw": raw_json}


def parse_blog_markdown(markdown_str: str) -> List[Dict[str, Any]]:
    """
    Parses a markdown blog string into structured sections with ContentBlock[] body.
    
    Block types:
    - paragraph: {"type": "paragraph", "text": str}
    - heading: {"type": "heading", "level": 3, "text": str}
    - list: {"type": "list", "ordered": bool, "items": list[str]}
    - table: {"type": "table", "headers": list[str], "rows": list[list[str]]}
    - quiz: {"type": "quiz", "question": str, "options": list[str], "correct_answer": str, "explanation": str}
    - comparison_widget: {"type": "comparison_widget", "left_title": str, "right_title": str, "metrics": list[dict]}
    - roadmap: {"type": "roadmap", "title": str, "steps": list[dict]}
    - code_block: {"type": "code_block", "language": str, "code": str, "explanation": Optional[str]}
    """
    if not markdown_str:
        return []

    lines = markdown_str.split("\n")
    sections = []
    current_section = None
    
    i = 0
    n = len(lines)
    
    def append_block(block):
        nonlocal current_section, sections
        if current_section is None:
            current_section = {
                "id": "introduction",
                "heading": "Introduction",
                "body": []
            }
            sections.append(current_section)
        current_section["body"].append(block)

    while i < n:
        raw_line = lines[i]
        line = raw_line.strip()
        
        # 1. Skip blank lines
        if not line:
            i += 1
            continue
            
        # 2. Skip top-level # title, header metadata lines, and horizontal dividers
        if line.startswith("# ") and not line.startswith("## ") and not line.startswith("### "):
            i += 1
            continue
        if line.startswith("**Category:**") or line.startswith("**Date:**"):
            i += 1
            continue
        if line == "---":
            i += 1
            continue

        # 3. H2 Section Heading: '## Heading'
        if line.startswith("## ") and not line.startswith("### "):
            heading_text = line[3:].strip()
            heading_text = re.sub(r"^\*\*(.*?)\*\*$", r"\1", heading_text).strip()
            section_id = slugify(heading_text)
            if not section_id:
                section_id = f"section-{len(sections) + 1}"
            current_section = {
                "id": section_id,
                "heading": heading_text,
                "body": []
            }
            sections.append(current_section)
            i += 1
            continue

        # 4. H3 Subheading: '### Subheading'
        if line.startswith("### "):
            subheading_text = line[4:].strip()
            subheading_text = re.sub(r"^\*\*(.*?)\*\*$", r"\1", subheading_text).strip()
            append_block({
                "type": "heading",
                "level": 3,
                "text": subheading_text
            })
            i += 1
            continue

        # 5. COMPONENT block
        if "COMPONENT:" in line or "component:" in line:
            component_match = re.search(r"(.*?)\b(COMPONENT|component):\s*(.*)", line)
            prefix_text = ""
            remainder = ""
            if component_match:
                prefix_text = component_match.group(1).strip()
                remainder = component_match.group(3).strip()
            
            # If text preceded COMPONENT: on the same line, emit as paragraph first
            if prefix_text:
                append_block({
                    "type": "paragraph",
                    "text": prefix_text
                })
            
            comp_type = ""
            if remainder and ("type:" in remainder.lower()):
                m_type = re.search(r"type:\s*([a-zA-Z0-9_]+)", remainder, re.IGNORECASE)
                if m_type:
                    comp_type = m_type.group(1).lower()

            i += 1
            props_lines = []
            in_props = False
            brace_depth = 0
            
            while i < n:
                cur_l = lines[i].strip()
                if not cur_l:
                    if in_props and brace_depth > 0:
                        props_lines.append("")
                    elif not in_props:
                        pass
                    else:
                        break
                    i += 1
                    continue
                
                # Check for Type: line
                if not comp_type and re.match(r"^type:\s*([a-zA-Z0-9_]+)", cur_l, re.IGNORECASE):
                    m_type = re.match(r"^type:\s*([a-zA-Z0-9_]+)", cur_l, re.IGNORECASE)
                    comp_type = m_type.group(1).lower()
                    i += 1
                    continue
                
                # Check for Props: {
                if not in_props and re.match(r"^props:\s*\{?", cur_l, re.IGNORECASE):
                    in_props = True
                    idx = cur_l.find("{")
                    if idx != -1:
                        props_str_part = cur_l[idx:]
                        props_lines.append(props_str_part)
                        brace_depth += props_str_part.count("{") - props_str_part.count("}")
                        if brace_depth == 0 and len(props_lines) > 0:
                            i += 1
                            break
                    i += 1
                    continue
                
                if in_props:
                    props_lines.append(lines[i])
                    brace_depth += lines[i].count("{") - lines[i].count("}")
                    if brace_depth <= 0:
                        i += 1
                        break
                    i += 1
                    continue
                
                if cur_l.startswith("#") or cur_l.startswith("COMPONENT:") or cur_l.startswith("IMAGE:"):
                    break
                i += 1

            parsed_props = {}
            if props_lines:
                raw_json = "\n".join(props_lines)
                parsed_props = parse_props_json(raw_json)

            comp_block = {"type": comp_type or "component"}
            comp_block.update(parsed_props)
            append_block(comp_block)
            continue

        # 6. IMAGE block: skip entirely (gradient cover images used instead)
        if line.startswith("IMAGE:") or line.startswith("image:"):
            i += 1
            while i < n:
                cur_l = lines[i].strip()
                if not cur_l:
                    i += 1
                    break
                if cur_l.startswith("#") or cur_l.startswith("COMPONENT:") or cur_l.startswith("IMAGE:"):
                    break
                i += 1
            continue

        # 7. Raw Markdown Table
        if line.startswith("|") and line.endswith("|"):
            table_lines = []
            while i < n and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                table_lines.append(lines[i].strip())
                i += 1
            
            if len(table_lines) >= 2:
                raw_headers = [c.strip() for c in table_lines[0].strip("|").split("|")]
                start_row = 1
                if len(table_lines) > 1 and re.match(r"^\|(\s*:?-+:?\s*\|)+$", table_lines[1]):
                    start_row = 2
                rows = []
                for r_line in table_lines[start_row:]:
                    row_cells = [c.strip() for c in r_line.strip("|").split("|")]
                    rows.append(row_cells)
                
                append_block({
                    "type": "table",
                    "headers": raw_headers,
                    "rows": rows
                })
            continue

        # 8. Bullet / Numbered Lists
        is_bullet = bool(re.match(r"^(\*|-)\s+", line))
        is_numbered = bool(re.match(r"^\d+\.\s+", line))
        if is_bullet or is_numbered:
            list_items = []
            ordered = is_numbered
            while i < n:
                cur_l = lines[i].strip()
                if not cur_l:
                    break
                m_b = re.match(r"^(\*|-)\s+(.*)", cur_l)
                m_n = re.match(r"^\d+\.\s+(.*)", cur_l)
                if ordered and m_n:
                    list_items.append(m_n.group(1).strip())
                elif not ordered and m_b:
                    list_items.append(m_b.group(2).strip())
                elif not ordered and m_n:
                    list_items.append(m_n.group(1).strip())
                elif ordered and m_b:
                    list_items.append(m_b.group(2).strip())
                else:
                    if list_items and not cur_l.startswith("#") and not cur_l.startswith("COMPONENT:"):
                        list_items[-1] += " " + cur_l
                    else:
                        break
                i += 1
            
            if list_items:
                append_block({
                    "type": "list",
                    "ordered": ordered,
                    "items": list_items
                })
            continue

        # 9. Paragraph
        para_lines = []
        while i < n:
            cur_l = lines[i].strip()
            if not cur_l:
                i += 1
                break
            if (cur_l.startswith("## ") or cur_l.startswith("### ") or 
                "COMPONENT:" in cur_l or "component:" in cur_l or 
                cur_l.startswith("IMAGE:") or cur_l.startswith("image:") or 
                (cur_l.startswith("|") and cur_l.endswith("|")) or
                re.match(r"^(\*|-|\d+\.)\s+", cur_l) or
                cur_l == "---" or cur_l.startswith("# ")):
                break
            para_lines.append(cur_l)
            i += 1
        
        if para_lines:
            full_text = " ".join(para_lines)
            append_block({
                "type": "paragraph",
                "text": full_text
            })

    return sections


def format_blog_for_frontend(trace_data: dict, sidecar_data: Optional[dict] = None, blog_index: int = 0) -> dict:
    """
    Transforms trace data and sidecar metadata into the structured document required
    by the Fulcrum frontend and saves to MongoDB.
    """
    metadata = trace_data.get("metadata", {})
    if sidecar_data:
        metadata = {**metadata, **sidecar_data}
        
    title = metadata.get("title") or trace_data.get("topic", "Untitled Blog")
    raw_category = metadata.get("category") or trace_data.get("category", "Preparation")
    mapped_category = CATEGORY_MAP.get(raw_category, "Preparation")
    
    slug = metadata.get("slug")
    if not slug:
        slug = slugify(title)
        
    date_val = metadata.get("date") or datetime.now().strftime("%Y-%m-%d")
    formatted_date = format_display_date(date_val)
    
    reading_time_val = metadata.get("reading_time_minutes", 10)
    read_time = f"{reading_time_val} min read" if isinstance(reading_time_val, (int, float)) else str(reading_time_val)
    if "read" not in read_time.lower():
        read_time = f"{read_time} min read"
        
    meta_desc = metadata.get("meta_description") or f"Learn more about {title} with comprehensive engineering guides and industry insights."
    tags = metadata.get("tags") or []
    
    # Cover image cycle (card_cover_1.png to card_cover_6.png)
    cover_image = f"/blogs/card_cover_{(blog_index % 6) + 1}.png"
    
    # Parse markdown into structured sections
    final_blog_markdown = trace_data.get("final_blog", "")
    sections = parse_blog_markdown(final_blog_markdown)
    
    # Table of contents
    table_of_contents = [{"id": s["id"], "label": s["heading"]} for s in sections]
    
    # Sidebar cards for category
    sidebar_cards = SIDEBAR_CARDS.get(mapped_category, SIDEBAR_CARDS["default"])
    
    now_iso = datetime.now().isoformat()
    
    return {
        "slug": slug,
        "title": title,
        "category": mapped_category,
        "original_category": raw_category,
        "author": DEFAULT_AUTHOR,
        "date": formatted_date,
        "readTime": read_time,
        "coverImage": cover_image,
        "snippet": meta_desc,
        "tableOfContents": table_of_contents,
        "sections": sections,
        "relatedArticles": [],
        "sidebarCards": sidebar_cards,
        "tags": tags,
        "meta_description": meta_desc,
        "status": "draft",
        "quality_score": float(metadata.get("quality_score", 0.0)),
        "word_count": int(metadata.get("word_count", 0)),
        "created_at": now_iso,
        "updated_at": now_iso
    }


def save_blog_to_db(blog_data: dict) -> None:
    """
    Saves or updates the structured blog document in the MongoDB 'blogs' collection.
    """
    try:
        db = get_db()
        collection = db["blogs"]
        
        # Ensure index on slug and category
        collection.create_index("slug", unique=True)
        collection.create_index("category")
        collection.create_index("status")
        
        # Preserve original created_at if document already exists
        existing = collection.find_one({"slug": blog_data["slug"]}, {"created_at": 1})
        if existing and "created_at" in existing:
            blog_data["created_at"] = existing["created_at"]
            
        collection.update_one(
            {"slug": blog_data["slug"]},
            {"$set": blog_data},
            upsert=True
        )
        print(f"[OK] Saved structured blog to MongoDB 'blogs' collection: '{blog_data['slug']}'")
    except Exception as e:
        print(f"[ERROR] Failed to save blog '{blog_data.get('slug')}' to MongoDB: {e}")
        raise


def format_and_save_blog(trace_path: Optional[str] = None, 
                         sidecar_path: Optional[str] = None,
                         trace_data: Optional[dict] = None, 
                         sidecar_data: Optional[dict] = None,
                         blog_index: int = 0) -> dict:
    """
    High-level orchestrator: loads files (if paths provided), parses markdown,
    formats blog according to Fulcrum contract, and saves to MongoDB.
    """
    if trace_data is None and trace_path and os.path.exists(trace_path):
        with open(trace_path, "r", encoding="utf-8") as f:
            trace_data = json.load(f)
            
    if trace_data is None:
        raise ValueError("Either trace_path or trace_data must be provided.")
        
    # Attempt to locate matching sidecar if not provided
    if sidecar_data is None:
        if sidecar_path and os.path.exists(sidecar_path):
            with open(sidecar_path, "r", encoding="utf-8") as f:
                sidecar_data = json.load(f)
        elif trace_path:
            candidate = trace_path.replace("-trace.json", ".json")
            if os.path.exists(candidate):
                with open(candidate, "r", encoding="utf-8") as f:
                    sidecar_data = json.load(f)
            else:
                out_dir = os.path.dirname(trace_path)
                slug = trace_data.get("metadata", {}).get("slug", "")
                if slug and out_dir:
                    short_slug = slug[:60]
                    for candidate_file in os.listdir(out_dir):
                        if candidate_file.endswith(".json") and not candidate_file.endswith("-trace.json"):
                            if candidate_file.startswith(short_slug):
                                cand_p = os.path.join(out_dir, candidate_file)
                                with open(cand_p, "r", encoding="utf-8") as f:
                                    sidecar_data = json.load(f)
                                break

    formatted = format_blog_for_frontend(trace_data, sidecar_data, blog_index=blog_index)
    save_blog_to_db(formatted)
    return formatted
