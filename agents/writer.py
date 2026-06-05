import asyncio
import json
import re
from typing import Dict, Any, List
from providers.llm_factory import get_llm
import config

WRITER_STATIC_PROMPT = """You are an elite, authoritative technical writer preparing a high-signal technical and placement blog.
You must adhere to these strict rules:
1. VOICE & TONE: Write in a professional, authoritative third-person or second-person ("you") voice. Do NOT use first-person (no "I", "we", "my", "our", "me"). Do NOT roleplay as a candidate or fabricate personal experiences.
2. SPECIFICITY TEST & EXAMPLES: Every piece of advice must be concrete, technical, and highly specific to the target topic. Avoid generic fluff like "study hard", "be confident", or "prepare well". Back up abstract concepts with specific technical examples (e.g. hypothetical score mappings, recursion trace examples, or database constraints).
3. FACT GROUNDING & STRICT ANTI-FABRICATION: You are provided with a 'Verified Facts List' and your Section Brief lists specific 'Assigned Facts' as reference IDs (e.g. `["fact_1", "fact_3"]`). `fact_1` corresponds to the first item in the Verified Facts List, `fact_2` corresponds to the second item, and so on.
   - You MUST extract the specific, detailed numbers, statistics, salaries, and metrics ONLY from these assigned fact indexes and naturally integrate them into your text.
   - ANTI-FABRICATION RULE: If information required for a claim is not available in assigned facts, retrieved context, or universally accepted technical knowledge, do not invent it. Do NOT fabricate numbers, benchmarks, percentages, or metrics.
   - QUALIFIED UNCERTAINTY: If evidence for a required detail is weak, missing, or conflicting in the retrieved facts, explicitly state uncertainty rather than synthesizing stronger, ungrounded conclusions.
4. TARGETED SOURCE CITATIONS (AVOID SPAM): Avoid citation spam. Do NOT add markdown citation links to every sentence or general concept. You MUST use citations ONLY when introducing specific factual claims, statistics, salary data, benchmarks, or retrieved evidence from the assigned facts list. Cite the source by appending a standard markdown link referencing the exact 'source_url' associated with that fact index (e.g. `[Glassdoor](url)` or `[Source Name](url)`).
   - CRITICAL CITATION TEXT RULE: Under no circumstances should you use the literal fact tags (like `[fact_1]`, `[fact_2]`, etc.) as the visible anchor text of the link. You must ALWAYS use a human-readable, recognizable source name derived from the URL or domain (e.g., `[Glassdoor](url)`, `[Scaler](url)`, `[PayScale](url)`). Keep ordinary prose and explanations citation-free.
5. RAW DATA UTILIZATION: In addition to the text-based 'Verified Facts List', you are provided with raw structured datasets: 'leetcode_data' (lists of actual coding questions) and 'roadmap_data' (logical study paths). If the section requires displaying programming problems or roadmap tracks, do NOT write standard markdown tables or bulleted lists. Instead, represent them using the decoupled `COMPONENT:` block spec (defined in Rule 8).
6. INFORMATION DENSITY & REPETITION: Avoid circular statements or repeating the same idea in different words. Every paragraph must introduce new technical details, evidence, or insights.
7. SECTION TYPE & STYLE: Start the section with a level 2 markdown heading (e.g., `## Section Title`) using the exact title of the Section Brief. Tailor your writing style to match the provided `Section Type` perfectly:
   - `'intro'`: Establish hooks, define terms, set up the target problem, and state the article's scope.
   - `'conceptual'`: Clear, authoritative breakdowns of foundational theoretical mechanics.
   - `'tutorial'`: Step-by-step guidance, code trace, or execution walks.
   - `'comparison'`: Deep architectural trade-offs, pros/cons, cost differences, and performance limits.
   - `'roadmap'`: Milestone-based learning path with progressive topic stages.
   - `'faq'`: Direct, punchy answers to People Also Ask (PAA) questions.
   - `'summary'`: Concise recap of technical learnings and synthesis of core findings.
   - `'cta'`: Dynamic, checklist-style next steps and call-to-action milestones.
8. DECOUPLED COMPONENT WIDGET SPECIFICATION: You are strictly PROHIBITED from rendering standard markdown tables, standard markdown code blocks, or fake/ASCII markdown visual layouts for interactive/visual elements. Instead, whenever a component directive is requested in `Component Directives` (e.g. `'table'`, `'code_block'`, `'comparison_widget'`, `'quiz'`, `'roadmap'`, `'confirm'`), you MUST write a clean, structured block specification in this exact text format:

COMPONENT:
type: <component_type>
props: {
  ...props as valid JSON...
}

   - COMPONENT ORDERING RULE: Place component blocks immediately after the paragraph that introduces them (do not group all components at the end or scatter them chaotically).
   - DUPLICATE COMPONENT PROTECTION: Do not render identical, duplicate, or redundant component blocks within the same section.
   - SINGLE-USE RESTRICTION: Do not generate more than one component block per section under any circumstances, EXCEPT for the final section's "Test Yourself" sub-section which must contain exactly three sequential `quiz` components. For any other sections, even if multiple component types are listed in Component Directives, pick the single most relevant one and only generate that.
   - STRICT AUTHORIZATION ONLY: Do NOT generate any COMPONENT: spec blocks unless that specific component type is explicitly listed in this section's Component Directives, EXCEPT for the final section where the three sequential `quiz` components are always required and authorized. If Component Directives is empty and it is not the final section, you must NOT write any COMPONENT: block specs. Under no circumstances should you output any disclaimers, placeholders, notes, or comments (such as "No COMPONENT block is generated...") explaining why a component is not generated; if no component is authorized, simply proceed with the prose text and do not output any mention of a component.
   - CODE BLOCK SECTION-TYPE GATE: Even if 'code_block' appears in Component Directives, you are PROHIBITED from generating a code_block component if the Section Type is 'conceptual', 'intro', 'comparison', 'summary', 'faq', or 'cta'. A `code_block` component is ONLY valid for Section Type 'tutorial' or 'roadmap' where real, executable algorithm or configuration code is the core content. If a code_block directive appears in any other section type, silently ignore it and write prose only.
   - TABLE ROW CONSTRAINT: In the `table` component props, the `rows` property MUST be a list of lists of strings (e.g. `[["value1", "value2"], ...]`). You are STRICTLY FORBIDDEN from using dictionaries for rows (e.g. do NOT write `[{"Header": "value"}, ...]`).

Examples:
- For `code_block`:
COMPONENT:
type: code_block
props: {
  "language": "python",
  "code": "def binary_search(arr, target):\\n    left, right = 0, len(arr) - 1\\n    while left <= right:\\n        mid = (left + right) // 2\\n        if arr[mid] == target:\\n            return mid\\n        elif arr[mid] < target:\\n            left = mid + 1\\n        else:\\n            right = mid - 1\\n    return -1",
  "explanation": "Binary search divides the search space in half with each iteration, yielding O(log n) complexity."
}
*Note*: Provide concise illustrative examples rather than large production implementations unless explicitly required.

- For `table`:
COMPONENT:
type: table
props: {
  "headers": ["Comparison Criteria", "Option A", "Option B"],
  "rows": [
    ["Direct Feature X", "Supported natively", "Requires plugin"],
    ["Performance Impact", "Low overhead (<5ms)", "High overhead (>150ms)"]
  ]
}

- For `quiz`:
COMPONENT:
type: quiz
props: {
  "question": "Which visual boundary does a container share with the host OS, unlike a Virtual Machine?",
  "options": [
    "The physical hardware interface",
    "The operating system kernel",
    "The network adapter space",
    "The application runtime environment"
  ],
  "correct_answer": "The operating system kernel",
  "explanation": "Containers share the host OS kernel via cgroups and namespaces, while VMs run a complete guest OS."
}

- For `comparison_widget`:
COMPONENT:
type: comparison_widget
props: {
  "left_title": "Option A",
  "right_title": "Option B",
  "metrics": [
    {"name": "Execution Overhead", "left": "Near-zero native speed", "right": "Instruction translation layers"}
  ]
}

- For `roadmap` (vertical step-by-step learning path or process flow):
COMPONENT:
type: roadmap
props: {
  "title": "Your DSA Interview Preparation Path",
  "steps": [
    {"label": "Arrays & Hashing", "description": "Build foundational pattern recognition with frequency maps and prefix sums."},
    {"label": "Two Pointers & Sliding Window", "description": "Learn pointer manipulation for sorted arrays and subarray problems."},
    {"label": "Binary Search", "description": "Master logarithmic search across sorted data and answer spaces."},
    {"label": "Trees & Graphs", "description": "DFS, BFS, and traversal strategies for hierarchical and networked data."}
  ]
}



9. CTA & CLOSING: Do NOT use clichés like "so what are you waiting for" or "happy coding". If this is the final section (where 'Is Final Section' is true):
   - For 'Comparison Articles', you MUST provide a definitive verdict that answers: Who should choose each option, When to choose one over the other, and Why, based on skills, interests, and goals.
   - Close the blog with a structured checklist CTA of concrete next steps.
   - At the VERY END of the blog, you MUST include a "Test Yourself" section containing three sequential `quiz` components to test the reader's understanding.
10. TARGET LENGTH: Stay within 50 words of the target word count. Make every sentence count. Do not pad the section with empty filler words.
11. TOPIC BREADTH & PLANNED ENGINEERING CONSTRAINTS: Ground your writing in operational engineering realities (latency, GPU/compute costs, memory constraints, data drift, production monitoring) ONLY when they are explicitly listed as part of the Section Brief's key points, assigned facts, or category guidelines from the outline planner. Do NOT unilaterally introduce or invent engineering constraints that are irrelevant to the topic (e.g., do not discuss GPU cost or server cold starts in a basic DSA binary search tutorial).

Return ONLY the raw markdown text for this section (including the prose and the structured COMPONENT block specs). Do not wrap the whole response in backticks or add any intro/outro messages."""

COHERENCE_STATIC_PROMPT = """You are a meticulous technical editor. Your job is to review a multi-section technical blog that was written in parallel and edit it to read as one cohesive, continuous article.

You must apply these strict rules:
1. PRESERVE EXISTING WORDING: Do NOT rewrite entire paragraphs or sections. Only modify sentences that are absolutely necessary to:
   - Fix transitions between parallel-written sections
   - Remove redundant or repetitive paragraphs/facts
   - Unify terminology
   Preserve the original author's wording whenever possible.
2. SMOOTH & TRUTH-BOUND TRANSITIONS: Edit section boundaries so they flow naturally. Do NOT infer missing transitions by inventing facts, data, or technical claims (strict anti-fabrication).
3. ELIMINATE REPETITION: Identify and remove duplicate advice, identical fact statements, or redundant paragraphs across different sections.
4. UNIFY & NORMALIZE TERMINOLOGY: Normalize inconsistent naming, abbreviations, and terminology throughout the article. Ensure naming conventions (e.g. "LLM" vs "Large Language Model" vs "foundation model" vs "transformer model", or "SDE-1" vs "Software Engineer Fresher") are unified and consistent.
5. HEADING CONSISTENCY: Ensure heading style and grammatical structures (e.g., questions, gerunds, declarative titles) remain consistent across all section titles in the article.
6. COMPONENT PRESERVATION (IMMUTABLE OBJECTS): Under no circumstances should you modify, merge, delete, or reorder any structured `COMPONENT:` block specifications. Treat the entire block from the keyword `COMPONENT:` to its closing curly brace `}` as an immutable, black-box object. You must pass them through to the output exactly as they are.
7. SECTION ORDER & NO NEW FACTS: Do NOT reorder the sections or move paragraphs to different sections. Do NOT introduce any new factual claims, statistics, metrics, or arguments. Only smooth, clean, and unify.
8. VOICE & TONE: Maintain a consistent, professional, authoritative tone throughout the entire document.

Return ONLY the fully edited markdown text of the blog. Do not add intro/outro comments or wrap in backticks."""

def clean_llm_markdown(text: str) -> str:
    """Removes leading/trailing codeblock wrappers if generated by the LLM."""
    clean = text.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:markdown|text)?\n", "", clean)
        clean = re.sub(r"\n```$", "", clean)
        clean = clean.strip()
    return clean

def writer_loop(state: dict) -> dict:
    """
    LangGraph node that runs sequentially N times (once per SectionBrief) in Standard Mode.
    Feeds 'running_context' from the previous section to the next to maintain seamless transitions.
    """
    print("\n--- Running Node: Writer Loop (Standard Mode) ---")
    briefs = state.get("section_briefs", [])
    retrieved_ctx = state.get("retrieved_context", {})
    verified_facts = retrieved_ctx.get("verified_facts", [])
    leetcode_data = retrieved_ctx.get("leetcode_data", None)
    roadmap_data = retrieved_ctx.get("roadmap_data", None)
    category = state.get("category", "")
    word_count_target = state.get("word_count_target", 2000)
    
    # We use the large model for the creative writing task
    llm = get_llm("large", temperature=0.7)
    
    drafts = []
    running_context = ""
    
    for idx, brief in enumerate(briefs, 1):
        print(f"Writing Section {idx}/{len(briefs)}: '{brief.get('title')}' (Target: {brief.get('target_word_count')} words)...")
        
        dynamic_prompt = f"""
---
Blog Category: {category}
Overall Blog Word Target: {word_count_target}

Section Brief to Write:
- Title: {brief.get('title')}
- Section Type: {brief.get('section_type', 'conceptual')}
- Target Word Count: {brief.get('target_word_count')}
- Key Points to Cover: {', '.join(brief.get('key_points', []))}
- Assigned Facts (Grounded index references): {', '.join(brief.get('assigned_facts', []))}
- Assigned Keywords: {', '.join(brief.get('assigned_keywords', []))}
- Component Directives: {', '.join(brief.get('component_directives', []))}
- Include Table: {brief.get('include_table', False)}
- Include Code Block: {brief.get('include_code_block', False)}
- Maps to PAA Question: {brief.get('maps_to_paa')}
- Is Final Section: {brief.get('is_final_section', False)}

Running Context (Last 150 words of previous section):
{running_context}

Verified Facts List (Grounding Database):
{json.dumps(verified_facts, indent=2)}

LeetCode Raw Question Data (Grounding Database):
{json.dumps(leetcode_data, indent=2) if leetcode_data else "None"}

Roadmap Raw Steps Data (Grounding Database):
{json.dumps(roadmap_data, indent=2) if roadmap_data else "None"}

Section Markdown Text:"""

        prompt = WRITER_STATIC_PROMPT + dynamic_prompt
        
        try:
            response = llm.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)
            section_text = clean_llm_markdown(content)
            drafts.append(section_text)
            
            # Slice last 150 words for running context
            words = section_text.split()
            if len(words) > 150:
                running_context = " ".join(words[-150:])
            else:
                running_context = section_text
                
        except Exception as e:
            print(f"Error writing section {idx}: {e}")
            drafts.append(f"## {brief.get('title')}\n\nDraft generation failed for this section. [Placeholder]")
            running_context = ""
            
    return {
        "section_drafts": drafts,
        "running_context": running_context
    }

async def async_write_section(
    llm, 
    brief: dict, 
    verified_facts: list, 
    leetcode_data: list, 
    roadmap_data: dict, 
    idx: int, 
    category: str = "", 
    word_count_target: int = 2000
) -> str:
    """Async helper to write a single section in parallel."""
    print(f"Async Writing Section {idx}: '{brief.get('title')}' (Target: {brief.get('target_word_count')} words)...")
    
    dynamic_prompt = f"""
---
Blog Category: {category}
Overall Blog Word Target: {word_count_target}

Section Brief to Write:
- Title: {brief.get('title')}
- Section Type: {brief.get('section_type', 'conceptual')}
- Target Word Count: {brief.get('target_word_count')}
- Key Points to Cover: {', '.join(brief.get('key_points', []))}
- Assigned Facts (Grounded index references): {', '.join(brief.get('assigned_facts', []))}
- Assigned Keywords: {', '.join(brief.get('assigned_keywords', []))}
- Component Directives: {', '.join(brief.get('component_directives', []))}
- Include Table: {brief.get('include_table', False)}
- Include Code Block: {brief.get('include_code_block', False)}
- Maps to PAA Question: {brief.get('maps_to_paa')}
- Is Final Section: {brief.get('is_final_section', False)}

Verified Facts List (Grounding Database):
{json.dumps(verified_facts, indent=2)}

LeetCode Raw Question Data (Grounding Database):
{json.dumps(leetcode_data, indent=2) if leetcode_data else "None"}

Roadmap Raw Steps Data (Grounding Database):
{json.dumps(roadmap_data, indent=2) if roadmap_data else "None"}

Section Markdown Text:"""

    prompt = WRITER_STATIC_PROMPT + dynamic_prompt
    
    try:
        # Await the langchain call (invoked inside an executor to keep it non-blocking if using synchronous client)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: llm.invoke(prompt))
        content = response.content if hasattr(response, "content") else str(response)
        return clean_llm_markdown(content)
    except Exception as e:
        print(f"Error async writing section {idx}: {e}")
        return f"## {brief.get('title')}\n\nDraft generation failed for this section. [Placeholder]"

async def async_write_all(state: dict) -> List[str]:
    """Helper to run parallel section writes."""
    briefs = state.get("section_briefs", [])
    retrieved_ctx = state.get("retrieved_context", {})
    verified_facts = retrieved_ctx.get("verified_facts", [])
    leetcode_data = retrieved_ctx.get("leetcode_data", None)
    roadmap_data = retrieved_ctx.get("roadmap_data", None)
    category = state.get("category", "")
    word_count_target = state.get("word_count_target", 2000)
    llm = get_llm("large", temperature=0.7)
    
    tasks = [
        async_write_section(
            llm, 
            brief, 
            verified_facts, 
            leetcode_data, 
            roadmap_data, 
            i, 
            category, 
            word_count_target
        ) for i, brief in enumerate(briefs, 1)
    ]
    return await asyncio.gather(*tasks)

def writer_async(state: dict) -> dict:
    """
    LangGraph node that runs parallel section writing in Map-Reduce Mode.
    Does not pass running_context; stitching & smoothing is handled downstream by the coherence_editor.
    """
    print("\n--- Running Node: Writer Async (Map-Reduce Mode) ---")
    drafts = asyncio.run(async_write_all(state))
    return {
        "section_drafts": drafts
    }

def coherence_editor(state: dict) -> dict:
    """
    LangGraph node that processes the stitched async drafts to resolve cross-section terminology,
    smooth boundaries, and remove repetitive content.
    """
    print("\n--- Running Node: Coherence Editor (Map-Reduce Mode) ---")
    assembled_draft = state.get("assembled_draft", "")
    if not assembled_draft:
        # If not assembled yet, stitch quickly for the editor
        drafts = state.get("section_drafts", [])
        assembled_draft = "\n\n".join(drafts)
        
    llm = get_llm("medium", temperature=0.3)
    
    dynamic_prompt = f"""
---
Assembled Parallel Draft:
{assembled_draft}

Coherent Markdown Draft:"""

    prompt = COHERENCE_STATIC_PROMPT + dynamic_prompt
    
    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        edited_draft = clean_llm_markdown(content)
        print("Coherence editing completed successfully.")
        return {
            "assembled_draft": edited_draft
        }
    except Exception as e:
        print(f"Error in Coherence Editor: {e}. Keeping original assembled draft.")
        return {
            "assembled_draft": assembled_draft
        }
