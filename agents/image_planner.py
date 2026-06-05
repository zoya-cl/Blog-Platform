import json
import re
from typing import List, Dict, Any
from providers.llm_factory import get_llm
from agents.utils import parse_json_robustly
import config

IMAGE_PLANNER_SYSTEM_PROMPT = """You are a senior technical art director and infographic strategist. Your task is to design a high-signal image generation plan for a technical blog post.
The images you plan will be generated using a state-of-the-art text-to-image model (google/gemini-3.1-flash-image-preview) which has EXCEPTIONAL text rendering capabilities. You should actively design images with clear, legible text overlays, correct labels, and clean professional typography.

Rules:
1. IMAGE BUDGET: Based on the target word count, decide on the image count:
   - < 1200 words: exactly 1 image
   - 1200 - 2000 words: exactly 2 images
   - > 2000 words: exactly 3 images
   (Do NOT exceed these budgets).

2. SECTION PLACEMENT: Place images immediately after H2 sections where they add the most explanatory value. Specify placement in the format "after_section_N" where N is the H2 section index (e.g., after the 2nd H2 section -> "after_section_2").

3. STYLE DECORATION: Align the visual style of each planned image with the blog category:
   - 'Comparison Articles' -> "A clean minimalist flat-design infographic split into two panels. Left panel has a big clear correct text header '<LabelA>' and shows service concepts. Right panel has a big clear correct text header '<LabelB>' and shows service concepts. Indigo and slate color palette. Modern vector illustration."
   - 'Placement Roadmaps' -> "A modern vertical roadmap flowchart with progressive milestone boxes connected by line arrows. Milestones labeled with clear topic text. Minimalist flat visual design."
   - 'Job Role and Career Trends' -> "A premium vector visual card representing key metrics or a comparison dashboard. Minimalist styling with legible charts, bold metric numbers, and correct data labels."
   - 'AI Technology' / 'Developer Technology' -> "A clean technical systems architecture diagram showing connected nodes and data flow paths. Every component/service is explicitly labeled with highly legible text."
   - 'DSA and Coding' -> "A step-by-step conceptual algorithm trace box or memory state diagram. Extremely clear, labeled inputs, outputs, and index pointers."
   - 'Resume Writing' -> "A side-by-side 'Do vs Don't' resume layout card, comparing clean layout traits against cluttered styles, with bold, correct typography."
   
4. DETAILED PROMPT SPECIFICATION: For each image, write a comprehensive 3-5 sentence prompt for the text-to-image generator.
   - You MUST explicitly specify the EXACT text labels, headings, and words that need to be written in the image.
   - Enclose the exact words to render in single quotes within your prompt (e.g. "Render the header 'CLOUD-NATIVE' on the left side").
   - Mandate clean sans-serif typography, slate/indigo corporate color palette, high contrast, and clean vector layout.
   - Absolutely no random background noise or cluttered details.
   - ASPECT RATIO: You MUST specify that the image should be horizontal landscape (16:9) or square (1:1). NEVER request vertically tall images.

You must output a JSON list matching this structure:
[
  {
    "image_index": 1,
    "section_index": 2,
    "section_title": "Section H2 Heading text",
    "image_type": "comparison | roadmap | architecture | concept",
    "placement": "after_section_2",
    "purpose": "A brief explanation of why this image is generated and placed here.",
    "prompt": "The detailed visual prompt containing exact text labels and vector art details."
  }
]

Return ONLY valid raw JSON. Do not include any explanations, markdown code blocks, or leading/trailing text."""

def image_planner_node(state: dict) -> dict:
    """
    LangGraph node that reads the assembled draft and decides how many
    and what kinds of images to generate, creating a structured image_plan.
    """
    print("\n--- Running Node: Image Planner ---")
    
    if not config.IMAGE_ENABLED:
        print("Image generation is disabled in config. Skipping.")
        return {"image_plan": []}
        
    assembled_draft = state.get("assembled_draft", "")
    metadata = state.get("metadata", {})
    category = state.get("category", "")
    word_count_target = state.get("word_count_target", 2000)
    
    if not assembled_draft:
        print("Warning: Assembled draft is empty. Cannot plan images.")
        return {"image_plan": []}
        
    # Determine H2 headings and their order in assembled_draft for reference
    h2_headings = re.findall(r"^##\s+(.+)$", assembled_draft, re.MULTILINE)
    print(f"Detected H2 sections: {len(h2_headings)}")
    for idx, heading in enumerate(h2_headings, 1):
        print(f"  {idx}. {heading}")
        
    llm = get_llm("medium", temperature=0.2)
    
    dynamic_prompt = f"""
---
Blog Title: {metadata.get('title', 'Unknown Topic')}
Blog Category: {category}
Word Count Target: {word_count_target}

Detected Sections:
{json.dumps([{"section_index": idx, "title": h} for idx, h in enumerate(h2_headings, 1)], indent=2)}

Assembled Blog Content:
{assembled_draft[:4000]}  # Send first 4k chars for planning context

Output Image Plan JSON:"""

    prompt = IMAGE_PLANNER_SYSTEM_PROMPT + dynamic_prompt
    
    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        
        image_plan = parse_json_robustly(content)
        
        # Validate structure
        validated_plan = []
        if isinstance(image_plan, list):
            for i, item in enumerate(image_plan, 1):
                item["image_index"] = i
                # Enforce placement is valid
                place = item.get("placement", f"after_section_{min(i, len(h2_headings))}")
                if not re.match(r"^after_section_\d+$", place):
                    place = f"after_section_{min(i, len(h2_headings))}"
                item["placement"] = place
                validated_plan.append(item)
                
        print(f"Planned {len(validated_plan)} images successfully.")
        return {
            "image_plan": validated_plan
        }
        
    except Exception as e:
        print(f"Error executing Image Planner: {e}. Generating fallback image plan.")
        # Fallback to 1 image after the first section
        fallback_plan = [
            {
                "image_index": 1,
                "section_index": 1,
                "section_title": h2_headings[0] if h2_headings else "Core Concepts",
                "image_type": "concept",
                "placement": "after_section_1",
                "purpose": "A foundational diagram showing key concepts.",
                "prompt": f"A clean minimalist vector concept diagram representing '{metadata.get('title')}' with Indigo and slate color palette and clear legibly rendered text labels."
            }
        ]
        return {
            "image_plan": fallback_plan
        }
