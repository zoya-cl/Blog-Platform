import os
import re
import json
import base64
import requests
from pathlib import Path
from typing import List, Dict, Any
import config

def call_openrouter_gemini_image(prompt: str) -> tuple[str, str]:
    """
    Calls OpenRouter google/gemini-3.1-flash-image-preview completions endpoint.
    Returns (kind, data) where kind is 'b64' or 'url' or 'none'.
    """
    key = config.OPENROUTER_API_KEY
    if not key:
        print("[WARN] OPENROUTER_API_KEY is missing. Skipping image generation.")
        return "none", ""
        
    endpoint = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://bloggraph-ai.dev",
        "X-Title": "BlogGraph-AI Image Ingestion",
    }
    
    payload = {
        "model": config.IMAGE_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "modalities": ["image"],
    }
    
    try:
        r = requests.post(endpoint, headers=headers, json=payload, timeout=120)
        if r.status_code != 200:
            print(f"[WARN] OpenRouter API returned HTTP {r.status_code}: {r.text}")
            return "none", ""
            
        body = r.json()
        message = body["choices"][0]["message"]
        images = message.get("images") or []
        
        if images:
            url = images[0]["image_url"]["url"]
            if url.startswith("data:image"):
                return "b64", url.split(",", 1)[1]
            return "url", url
            
        # Check content list fallback
        content = message.get("content") or []
        if isinstance(content, list):
            for item in content:
                if item.get("type") == "image_url":
                    url = item["image_url"]["url"]
                    if url.startswith("data:image"):
                        return "b64", url.split(",", 1)[1]
                    return "url", url
                    
        return "none", ""
    except Exception as e:
        print(f"[WARN] Error calling OpenRouter: {e}")
        return "none", ""

def image_generator_node(state: dict) -> dict:
    """
    LangGraph node that calls the image model for each item in state['image_plan'],
    saves the image files under output/<slug>/images/, injects the image markdown
    into assembled_draft, and appends the custom 'confirm' Test Yourself component
    at the end of the blog post.
    """
    print("\n--- Running Node: Image Generator ---")
    
    image_plan = state.get("image_plan", [])
    assembled_draft = state.get("assembled_draft", "")
    metadata = state.get("metadata", {})
    slug = metadata.get("slug", "draft-post")
    
    if not config.IMAGE_ENABLED or not image_plan:
        print("Image generation is disabled or plan is empty.")
        return {"assembled_draft": assembled_draft, "generated_images": []}
        
    generated_images = []
    
    # Establish output path: output/<slug>/images/
    output_dir = Path("output") / slug / "images"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Split draft by H2 headings to inject cleanly
    parts = assembled_draft.split("\n## ")
    
    for plan_item in image_plan:
        idx = plan_item["image_index"]
        purpose = plan_item.get("purpose", "Visual Illustration")
        prompt = plan_item["prompt"]
        placement = plan_item["placement"]  # after_section_N
        
        print(f"Generating Image {idx}/{len(image_plan)}: '{purpose}'...")
        kind, data = call_openrouter_gemini_image(prompt)
        
        if kind == "b64":
            filename = f"img_{idx}.png"
            filepath = output_dir / filename
            filepath.write_bytes(base64.b64decode(data))
            
            # Relative path is <slug>/images/img_idx.png
            relative_path = f"{slug}/images/{filename}"
            print(f"  [PASS] Image saved to {filepath} -> RelPath: {relative_path}")
            
            generated_images.append({
                "image_index": idx,
                "path": relative_path,
                "purpose": purpose,
                "placement": placement
            })
            
            # Inject markdown into split parts
            match = re.match(r"^after_section_(\d+)$", placement)
            if match:
                sec_num = int(match.group(1))
                # Validate bounds (parts[0] is intro/header, parts[1] is Section 1...)
                if 1 <= sec_num < len(parts):
                    image_md = f"\n\n![{purpose}]({relative_path})\n\n"
                    parts[sec_num] = parts[sec_num].rstrip() + image_md
                else:
                    # Append to very last section
                    image_md = f"\n\n![{purpose}]({relative_path})\n\n"
                    parts[-1] = parts[-1].rstrip() + image_md
                    
        elif kind == "url":
            print(f"  [PASS] Got image URL: {data}")
            generated_images.append({
                "image_index": idx,
                "path": data,
                "purpose": purpose,
                "placement": placement
            })
            # Inject markdown url
            match = re.match(r"^after_section_(\d+)$", placement)
            if match:
                sec_num = int(match.group(1))
                if 1 <= sec_num < len(parts):
                    image_md = f"\n\n![{purpose}]({data})\n\n"
                    parts[sec_num] = parts[sec_num].rstrip() + image_md
                else:
                    image_md = f"\n\n![{purpose}]({data})\n\n"
                    parts[-1] = parts[-1].rstrip() + image_md
        else:
            print(f"  [WARN] Image {idx} failed to generate. Continuing gracefully.")
            
    # Join parts back with heading syntax
    assembled_draft = "\n## ".join(parts)
    
    return {
        "assembled_draft": assembled_draft,
        "generated_images": generated_images
    }
