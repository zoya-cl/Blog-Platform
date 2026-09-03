import os
import re
import json
from typing import List, Dict, Any
from providers.llm_factory import get_llm
from agents.utils import clean_llm_markdown

AUTO_FAQ_GENERATOR_PROMPT = """You are an expert technical content strategist. Your task is to generate a comprehensive Frequently Asked Questions (FAQ) section for a placement preparation blog.

Blog Title: {title}
Blog Category: {category}

Article Overview:
{section_summaries}

Verified Facts List:
{verified_facts}

Rules:
1. Generate 3 to 4 distinct, high-impact FAQ questions that candidates or engineers frequently ask about this topic.
2. For each question, provide a complete, authoritative 2-4 sentence answer.
3. State all facts confidently without excessive hedging.
4. Format each question-answer pair as:
### [Question Text]
[Detailed Answer Text]

Return ONLY the markdown text containing the questions and answers (with no starting title heading like "## Frequently Asked Questions", as that is managed by the system). Do not wrap in backticks or add intro/outro comments."""

def check_transition(curr_section: str, next_section: str) -> str:
    """
    Ensures clean paragraph spacing between markdown sections.
    Does NOT append period artifacts before markdown headers (##).
    """
    curr_clean = curr_section.strip()
    next_clean = next_section.strip()
    
    if not curr_clean or not next_clean:
        return "\n\n"
        
    # If the next section starts with a heading, return clean blank lines
    if next_clean.startswith("#"):
        return "\n\n"
        
    if curr_clean[-1] not in [".", "!", "?", ":", "`", "*"]:
        return ".\n\n"
        
    return "\n\n"

def compute_overlap(comp_type: str, props_a: dict, props_b: dict) -> float:
    """Compute content overlap ratio between two components of the same type."""
    if comp_type == "comparison_widget":
        metrics_a = {m.get("name", "").lower().strip() for m in props_a.get("metrics", []) if isinstance(m, dict)}
        metrics_b = {m.get("name", "").lower().strip() for m in props_b.get("metrics", []) if isinstance(m, dict)}
        if not metrics_a or not metrics_b:
            return 0.0
        shared = metrics_a & metrics_b
        return len(shared) / max(len(metrics_a), len(metrics_b))
    elif comp_type == "table":
        headers_a = set(h.lower().strip() for h in props_a.get("headers", []) if isinstance(h, str))
        headers_b = set(h.lower().strip() for h in props_b.get("headers", []) if isinstance(h, str))
        if not headers_a or not headers_b:
            return 0.0
        return len(headers_a & headers_b) / max(len(headers_a), len(headers_b))
    elif comp_type == "quiz":
        q_a = props_a.get("question", "").lower()
        q_b = props_b.get("question", "").lower()
        words_a = set(re.findall(r'\w+', q_a))
        words_b = set(re.findall(r'\w+', q_b))
        if not words_a or not words_b:
            return 0.0
        return len(words_a & words_b) / max(len(words_a), len(words_b))
    return 0.0


def dedup_components(assembled: str) -> str:
    """
    Safety net: strips near-duplicate COMPONENT blocks based on metric/header overlap
    and enforces maximum component limits per blog.
    """
    COMPONENT_LIMITS = {
        "comparison_widget": 2,
        "table": 2,
        "quiz": 3,
        "code_block": 2,
        "roadmap": 1
    }
    comp_regex = r'(COMPONENT:\s*\n[Tt]ype:\s*(\w+)\s*\n[Pp]rops:\s*(\{[\s\S]*?\}))(?=\n\s*(?:COMPONENT:|[A-Z#]|\n|\Z))'
    matches = list(re.finditer(comp_regex, assembled))

    seen_by_type = {}
    type_counts = {}
    to_remove = []

    for m in matches:
        comp_type = m.group(2).strip().lower()
        props_str = m.group(3).strip()
        try:
            props = json.loads(props_str)
        except Exception:
            continue

        limit = COMPONENT_LIMITS.get(comp_type, 2)
        curr_count = type_counts.get(comp_type, 0)
        if curr_count >= limit:
            print(f"[Assembler Dedup] Removing excess {comp_type} (limit of {limit} reached)")
            to_remove.append(m)
            continue

        if comp_type not in seen_by_type:
            seen_by_type[comp_type] = []

        is_dup = False
        for prev_match, prev_props in seen_by_type[comp_type]:
            overlap = compute_overlap(comp_type, props, prev_props)
            threshold = 0.25 if comp_type == "comparison_widget" else 0.4
            if overlap >= threshold:
                print(f"[Assembler Dedup] Removing duplicate {comp_type} (overlap={overlap:.0%})")
                to_remove.append(m)
                is_dup = True
                break

        if not is_dup:
            seen_by_type[comp_type].append((m, props))
            type_counts[comp_type] = curr_count + 1

    for m in reversed(to_remove):
        assembled = assembled[:m.start()] + assembled[m.end():]

    return assembled


IMAGE_PROMPT_GENERATOR = """You are an expert visual content strategist for technical blogs.
Given a blog title, category, and section summaries, generate creative, descriptive image prompts.

RULES:
1. THUMBNAIL: Exactly 1 thumbnail prompt. Abstract, visually striking, suitable as a blog hero/card image. Modern isometric, 3D render, or clean vector style. MUST explicitly specify "no text, no words".
2. SECTION IMAGES: Exactly 2 to 3 section image prompts. Each must follow a specific section and visually explain or depict that section's core topic.
   - "technical_diagram": Architecture diagrams, flowcharts, topology visuals
   - "conceptual_illustration": Abstract concept visualization, metaphorical illustrations
   - "data_visualization": Comparisons, infographics, benchmark charts
3. PROMPT SPECIFICATIONS: 40-70 words per prompt. Mention specific color palettes (e.g. "cyan and deep navy with orange accents"), visual perspective, and explicitly include "clean render, no text, no words, no labels".
4. SPACING: Space section images evenly. Never place two images after consecutive sections. (e.g. after section 2 and after section 4).
5. ALT TEXT: Provide concise, SEO-friendly alt_text for accessibility.

Blog Title: {title}
Blog Category: {category}
Total Sections: {section_count}

Section Summaries:
{section_summaries}

Output JSON format:
{{
  "thumbnail": {{
    "prompt": "Detailed prompt...",
    "style": "hero_banner"
  }},
  "section_images": [
    {{
      "after_section": 2,
      "prompt": "Detailed prompt...",
      "style": "technical_diagram",
      "alt_text": "Descriptive alt text"
    }}
  ]
}}

Return ONLY raw JSON."""

def generate_image_prompts(title: str, category: str, section_drafts: list) -> dict:
    """Uses medium LLM to generate 1 thumbnail prompt and 2-3 section image prompts."""
    print("Generating AI image prompts for blog...")
    section_summaries = []
    for i, draft in enumerate(section_drafts, 1):
        words = draft.split()[:40]
        summary = " ".join(words)
        section_summaries.append(f"- Section {i}: {summary}...")
    summaries_str = "\n".join(section_summaries)

    try:
        llm = get_llm("medium", temperature=0.5)
        prompt = IMAGE_PROMPT_GENERATOR.format(
            title=title,
            category=category,
            section_count=len(section_drafts),
            section_summaries=summaries_str
        )
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        from agents.utils import parse_json_robustly
        result = parse_json_robustly(content)

        if "thumbnail" not in result:
            result["thumbnail"] = {
                "prompt": f"Modern isometric technical illustration representing {title}, dark background with glowing cyan and indigo accents, clean 3D render, no text",
                "style": "hero_banner"
            }
        if "section_images" not in result:
            result["section_images"] = []

        print(f"Image prompts generated: 1 thumbnail + {len(result['section_images'])} section images.")
        return result
    except Exception as e:
        print(f"Error generating image prompts ({e}). Using default prompts.")
        default_after = 2 if len(section_drafts) >= 2 else 1
        return {
            "thumbnail": {
                "prompt": f"Modern isometric technical illustration representing {title}, dark background with glowing cyan and indigo accents, clean 3D render, no text",
                "style": "hero_banner"
            },
            "section_images": [
                {
                    "after_section": default_after,
                    "prompt": f"Technical architecture diagram explaining core mechanisms of {title}, clean whiteboard style, blue and teal palette, no text no labels",
                    "style": "technical_diagram",
                    "alt_text": f"Architecture diagram for {title}"
                }
            ]
        }

def enforce_h2_headings(draft_parts: list, section_briefs: list) -> list:
    """Ensure every section draft starts with a proper ## heading."""
    fixed = []
    for i, part in enumerate(draft_parts):
        stripped = part.strip()
        if not stripped:
            fixed.append(part)
            continue
        # Check if starts with ##
        if not re.match(r"^##\s+", stripped):
            first_line = stripped.split("\n")[0].strip()
            # If the first line doesn't end with a period and is reasonably short, assume it was intended as a heading
            if len(first_line) < 120 and not first_line.endswith("."):
                rest = stripped[len(first_line):].lstrip("\n")
                stripped = f"## {first_line}\n\n{rest}" if rest else f"## {first_line}"
            elif i < len(section_briefs):
                title = section_briefs[i].get("title", f"Section {i+1}")
                stripped = f"## {title}\n\n{stripped}"
        fixed.append(stripped)
    return fixed

def assembler(state: dict) -> dict:
    """
    Stitches all section drafts in outline order,
    dynamically generates high-quality FAQ answers using LLM,
    and appends the FAQ block cleanly at the end of the article.
    """
    print("\n--- Running Node: Assembler (Pure Python + FAQ LLM) ---")
    drafts = state.get("section_drafts", [])
    retrieved_context = state.get("retrieved_context", {})
    title = state.get("topic", state.get("metadata", {}).get("title", ""))
    category = state.get("category", "")
    
    if not drafts:
        print("Warning: No section drafts found to assemble.")
        return {"assembled_draft": ""}
        
    section_briefs = state.get("section_briefs", [])
    drafts = enforce_h2_headings(drafts, section_briefs)
    
    assembled_parts = []
    
    # 1. Stitch all section drafts sequentially
    for i, curr_part in enumerate(drafts):
        curr_clean = curr_part.strip()
        if not curr_clean:
            continue
            
        if assembled_parts:
            transition = check_transition(assembled_parts[-1], curr_clean)
            assembled_parts.append(transition + curr_clean)
        else:
            assembled_parts.append(curr_clean)
            
    # 2. Append FAQ section at the end if we have multiple sections
    if len(drafts) > 1:
        print("Generating auto-FAQ section for draft...")
        
        # Build section summaries for context
        section_summaries = []
        for s_idx, s_draft in enumerate(drafts):
            words = s_draft.split()[:40]
            summary = " ".join(words)
            section_summaries.append(f"- Section {s_idx+1}: {summary}...")
        summaries_str = "\n".join(section_summaries)
        
        try:
            llm = get_llm("medium", temperature=0.4)
            facts_str = json.dumps(retrieved_context.get("verified_facts", []), indent=2)
            
            prompt = AUTO_FAQ_GENERATOR_PROMPT.format(
                title=title,
                category=category,
                verified_facts=facts_str,
                section_summaries=summaries_str
            )
            
            response = llm.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)
            clean_faq = clean_llm_markdown(content)
            
            faq_block = f"## Frequently Asked Questions\n\n{clean_faq}"
            assembled_parts.append("\n\n" + faq_block)
            print("FAQ section generated successfully with LLM.")
            
        except Exception as e:
            print(f"Error generating FAQ section with LLM: {e}. Passing clean stitching.")
            
    assembled_draft = "".join(assembled_parts).strip()
    assembled_draft = dedup_components(assembled_draft)
    print(f"Draft assembled successfully. Length: {len(assembled_draft)} characters.")

    # Generate image prompts & generate images via ImageClient
    generated_images = []
    if drafts:
        try:
            image_prompts = generate_image_prompts(title=title, category=category, section_drafts=drafts)
            from services.image_client import ImageClient
            import config
            image_client = ImageClient(
                api_url=getattr(config, "IMAGE_API_URL", ""),
                api_key=getattr(config, "IMAGE_API_KEY", "")
            )
            slug = state.get("metadata", {}).get("slug", "")
            if not slug:
                from agents.formatter import sanitize_title
                slug = sanitize_title(title)

            _project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            images_output_dir = os.path.join(_project_root, "output", "images")

            # 1. Generate thumbnail (index=0)
            thumb_spec = image_prompts.get("thumbnail", {})
            if thumb_spec:
                t_prompt = thumb_spec.get("prompt", f"Thumbnail for {title}")
                t_style = thumb_spec.get("style", "hero_banner")
                thumb_rel_path = image_client.generate(
                    prompt=t_prompt,
                    style=t_style,
                    slug=slug,
                    index=0,
                    category=category,
                    output_dir=images_output_dir
                )
                generated_images.append({
                    "type": "thumbnail",
                    "path": thumb_rel_path,
                    "prompt": t_prompt,
                    "style": t_style
                })

            # 2. Generate section images
            for img_spec in image_prompts.get("section_images", []):
                sec_idx = int(img_spec.get("after_section", 1))
                s_prompt = img_spec.get("prompt", f"Illustration for section {sec_idx}")
                s_style = img_spec.get("style", "conceptual_illustration")
                s_alt = img_spec.get("alt_text", f"Visual illustration for section {sec_idx}")
                sec_rel_path = image_client.generate(
                    prompt=s_prompt,
                    style=s_style,
                    slug=slug,
                    index=sec_idx,
                    category=category,
                    output_dir=images_output_dir
                )
                generated_images.append({
                    "type": "section_image",
                    "after_section": sec_idx,
                    "path": sec_rel_path,
                    "alt_text": s_alt,
                    "prompt": s_prompt,
                    "style": s_style
                })
            print(f"Total AI images generated and staged: {len(generated_images)}.")
        except Exception as e:
            print(f"Warning: Image generation failed in assembler node: {e}")

    return {
        "assembled_draft": assembled_draft,
        "generated_images": generated_images
    }
