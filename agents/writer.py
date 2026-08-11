import asyncio
import json
import re
from typing import Dict, Any, List
from providers.llm_factory import get_llm
import config
import random

WRITER_TEMPLATES = {
    "roadmap_template": """
CATEGORY-SPECIFIC GUIDELINES (Roadmap):
- Structure content as progressive milestones with clear prerequisites.
- Include explicit timeline markers (e.g., "Week 1-2", "Month 1") where appropriate.
- Focus on actionable learning paths with measurable outcomes.""",

    "interview_collection_template": """
CATEGORY-SPECIFIC GUIDELINES (Interview Collection):
- Structure questions by pattern type (e.g., sliding window, two pointers, DP).
- Provide sample inputs/outputs for coding problems.
- Highlight common pitfalls and optimization techniques interviewers expect.""",

    "techstack_template": """
CATEGORY-SPECIFIC GUIDELINES (Tech Stack):
- Focus on architectural decisions, trade-offs, and integration patterns.
- Compare technologies with concrete performance/cost metrics where available.
- Address scaling considerations, failure modes, and operational concerns.""",

    "standard_template": """
CATEGORY-SPECIFIC GUIDELINES (Standard):
- Provide authoritative, high-density coverage balancing theory with examples.
- Maintain logical flow from foundational concepts to advanced applications."""
}

WRITER_CORE_PROMPT = """You are an elite technical writer preparing a high-signal technical and placement blog.

CORE RULES:
1. VOICE: Write in a professional, authoritative third-person or second-person ("you") voice. Do NOT use first-person (no "I", "we", "my", "our", "me"). Do NOT roleplay as a candidate or fabricate personal experiences.
2. SPECIFICITY: Every piece of advice must be concrete, technical, and highly specific to the target topic. Avoid generic fluff like "study hard" or "prepare well". Back up abstract concepts with specific technical examples.
3. FACT GROUNDING & ANTI-HALLUCINATION: You MUST extract specific numbers, statistics, metrics, and claims ONLY from the provided 'Section Facts' list. NEVER fabricate benchmark statistics, salary numbers, percentages, or metrics. If factual evidence is missing, state uncertainty explicitly ("Industry practices suggest...").
4. CITATIONS: Cite sources when introducing specific factual claims or metrics using a standard markdown link referencing the exact 'source_url' (e.g. [Glassdoor](url) or [AWS Docs](url)). NEVER use literal tags like [fact_1] as anchor text.
5. INFORMATION DENSITY: Avoid circular statements, filler transitions ("At this point...", "In today's..."), or repeating the same idea in different words. Every paragraph must introduce new technical details.
6. TARGET LENGTH: Stay strictly within ±15% of the target word count. Do not write repetitive fluff to artificially inflate word count.
7. COMPONENT SELECTION: Limit quiz components. Include at most ONE quiz component per section ONLY if specifically requested. Prefer comparison_widget, table, or code_block for visual engagement.

BANNED PHRASES (never use these):
{banned_phrases}

Start the section with a level 2 markdown heading: ## {section_title}"""

FORMAT_PROMPTS = {
    "deep_dive": """FORMAT RULES (Deep Dive):
- Write rich, analytical prose paragraphs. Lead with the 'why' before the 'what'.
- Build progressive complexity: start accessible, end with production-grade nuance.
- Use sub-headings (###) sparingly for major logical shifts within the section.""",

    "listicle": """FORMAT RULES (Listicle):
- Lead with a bold item name, then 2-3 sentences of focused detail.
- Each item should be self-contained and scannable.
- Vary sentence openers across items. Do not start every item the same way.""",

    "step_by_step": """FORMAT RULES (Step-by-Step):
- Start each section with the step objective: 'Goal: [what you'll achieve]'.
- Include prerequisites if any. Use directive voice: 'Install X. Configure Y.'
- End each step with a checkpoint: 'At this point, you should have...'""",

    "comparison": """FORMAT RULES (Comparison):
- Present both sides with equal depth. No bias toward either option.
- Use concrete metrics (latency, cost, team size) not vague opinions.
- Include a verdict sub-section in the final section: 'Choose X if... Choose Y if...'""",

    "qa_interview": """FORMAT RULES (Q&A Interview):
- Structure as ### Question followed by a clear, direct answer.
- For coding questions, include time/space complexity.
- Group related questions. Add interviewer perspective tips.""",

    "myth_buster": """FORMAT RULES (Myth-Buster):
- Start each section with '### Myth: [common belief]' then '### Reality: [the truth]'.
- Explain WHY the myth exists before debunking it.
- Use evidence from the provided facts to support the reality.""",
}

COMPONENT_SPEC_RULES = """DECOUPLED COMPONENT WIDGET SPECIFICATION:
You are strictly PROHIBITED from rendering standard markdown tables, standard markdown code blocks, or fake/ASCII markdown visual layouts for interactive/visual elements. Instead, whenever a component directive is requested in `Component Directives` (e.g. 'table', 'code_block', 'comparison_widget', 'quiz', 'roadmap'), you MUST write a clean, structured block specification in this exact text format:

COMPONENT:
type: <component_type>
props: {
  ...props as valid JSON...
}

- Place component blocks immediately after the paragraph that introduces them.
- Do not render identical, duplicate, or redundant component blocks within the same section.
- Do not generate more than one component block per section under any circumstances, EXCEPT for the final section which must contain exactly three sequential quiz components.
- Do NOT generate any COMPONENT: spec blocks unless that specific component type is explicitly listed in Component Directives (or if it's the final section quizzes).
- Even if 'code_block' appears in Component Directives, you are PROHIBITED from generating a code_block component if the Section Type is 'conceptual', 'intro', 'comparison', 'summary', 'faq', or 'cta'. It is ONLY valid for Section Type 'tutorial' or 'roadmap'.
- In the table component props, the 'rows' property MUST be a list of lists of strings (e.g. [["val1", "val2"]]). Do NOT write list of dicts.

Examples:
- For code_block:
COMPONENT:
type: code_block
props: {
  "language": "python",
  "code": "def binary_search(arr, target):\\n    left, right = 0, len(arr) - 1\\n    while left <= right:\\n        mid = (left + right) // 2\\n        if arr[mid] == target:\\n            return mid\\n        elif arr[mid] < target:\\n            left = mid + 1\\n        else:\\n            right = mid - 1\\n    return -1",
  "explanation": "Binary search divides the search space in half with each iteration, yielding O(log n) complexity."
}

- For table:
COMPONENT:
type: table
props: {
  "headers": ["Comparison Criteria", "Option A", "Option B"],
  "rows": [
    ["Direct Feature X", "Supported natively", "Requires plugin"],
    ["Performance Impact", "Low overhead (<5ms)", "High overhead (>150ms)"]
  ]
}

- For quiz:
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

- For comparison_widget:
COMPONENT:
type: comparison_widget
props: {
  "left_title": "Option A",
  "right_title": "Option B",
  "metrics": [
    {"name": "Execution Overhead", "left": "Near-zero native speed", "right": "Instruction translation layers"}
  ]
}

- For roadmap:
COMPONENT:
type: roadmap
props: {
  "title": "Your DSA Interview Preparation Path",
  "steps": [
    {"label": "Arrays & Hashing", "description": "Build foundational pattern recognition with frequency maps and prefix sums."},
    {"label": "Two Pointers & Sliding Window", "description": "Learn pointer manipulation for sorted arrays and subarray problems."}
  ]
}"""

FEW_SHOT_EXAMPLE = """FEW-SHOT EXEMPLAR (representing the high structural and prose quality expected):

## Why Consistent Hashing Outperforms Modular Hashing at Scale

When a distributed cache cluster grows from 5 to 50 nodes, traditional modular hashing (`key % N`) forces a near-complete redistribution of cached data. With 50 nodes, adding a single server invalidates approximately 98% of existing key mappings, triggering a thundering herd of cache misses that can saturate the backend database within seconds.

Consistent hashing solves this by mapping both keys and servers onto a virtual ring of 2^32 positions. When a node joins or leaves, only the keys in the affected arc — roughly `K/N` keys where K is total keys and N is total nodes — need to migrate. In practice, systems like Amazon DynamoDB and Apache Cassandra use 150–256 virtual nodes per physical server to ensure uniform distribution across the ring, keeping variance below 10% even during rolling deployments [AWS Documentation](https://docs.aws.amazon.com/dynamodb).

COMPONENT:
type: comparison_widget
props: {
  "left_title": "Modular Hashing",
  "right_title": "Consistent Hashing",
  "metrics": [
    {"name": "Key Redistribution on Node Add", "left": "~98% of all keys", "right": "~1/N of all keys"},
    {"name": "Lookup Complexity", "left": "O(1) modulo", "right": "O(log N) ring search"},
    {"name": "Hot Spot Risk", "left": "Low (uniform mod)", "right": "Managed via virtual nodes"}
  ]
}

This architectural difference becomes critical at scale..."""

def clean_llm_markdown(text: str) -> str:
    """Removes leading/trailing codeblock wrappers if generated by the LLM."""
    clean = text.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:markdown|text)?\n", "", clean)
        clean = re.sub(r"\n```$", "", clean)
        clean = clean.strip()
    return clean

async def async_write_section(
    llm, 
    brief: dict, 
    verified_facts: list, 
    roadmap_data: dict, 
    idx: int, 
    category: str = "", 
    word_count_target: int = 2000,
    writer_template: str = "standard_template",
    blog_format: str = "deep_dive",
    persona_instructions: str = ""
) -> str:
    """Async helper to write a single section in parallel."""
    print(f"Async Writing Section {idx}: '{brief.get('title')}' (Target: {brief.get('target_word_count')} words)...")
    template_guidelines = WRITER_TEMPLATES.get(writer_template, WRITER_TEMPLATES["standard_template"])
    
    # Scope facts to this section
    assigned_refs = brief.get("assigned_facts", [])
    section_facts = []
    for ref in assigned_refs:
        try:
            fact_idx = int(ref.replace("fact_", "")) - 1
            if 0 <= fact_idx < len(verified_facts):
                section_facts.append(verified_facts[fact_idx])
        except (ValueError, IndexError):
            pass
            
    banned_str = "\n".join(f"- \"{p}\"" for p in config.BANNED_PHRASES)
    format_rules = FORMAT_PROMPTS.get(blog_format, FORMAT_PROMPTS["deep_dive"])
    
    core_prompt = WRITER_CORE_PROMPT.format(
        banned_phrases=banned_str,
        section_title=brief.get("title", "")
    )
    
    dynamic_prompt = f"""
---
Blog Category: {category}
Overall Blog Word Target: {word_count_target}

Section Brief to Write:
- Title: {brief.get('title')}
- Section Type: {brief.get('section_type', 'conceptual')}
- Target Word Count: {brief.get('target_word_count')}
- Key Points to Cover: {', '.join(brief.get('key_points', []))}
- Assigned Keywords: {', '.join(brief.get('assigned_keywords', []))}
- Component Directives: {', '.join(brief.get('component_directives', []))}
- Include Table: {brief.get('include_table', False)}
- Include Code Block: {brief.get('include_code_block', False)}
- Maps to PAA Question: {brief.get('maps_to_paa')}
- Is Final Section: {brief.get('is_final_section', False)}

Section Facts (Grounding Database — use ONLY these):
{json.dumps(section_facts, indent=2) if section_facts else "None — rely on established technical knowledge only."}

Roadmap Raw Steps Data (Grounding Database):
{json.dumps(roadmap_data, indent=2) if roadmap_data else "None"}

Section Markdown Text:"""

    prompt = f"""{core_prompt}

{format_rules}

WRITING PERSONA:
{persona_instructions}

{template_guidelines}

{COMPONENT_SPEC_RULES}

{FEW_SHOT_EXAMPLE}

{dynamic_prompt}"""
    
    try:
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
    roadmap_data = retrieved_ctx.get("roadmap_data", None)
    category = state.get("category", "")
    word_count_target = state.get("word_count_target", 2000)
    blog_format = state.get("blog_format", "deep_dive")
    writer_template_name = state.get("writer_template", "standard_template")
    
    # Select persona randomly for consistency throughout parallel run
    persona_key = random.choice(list(config.WRITING_PERSONAS.keys()))
    persona_instructions = config.WRITING_PERSONAS[persona_key]
    print(f"Writing Persona selected: {persona_key}")
    
    llm = get_llm("large", temperature=0.7)
    
    tasks = [
        async_write_section(
            llm, 
            brief, 
            verified_facts, 
            roadmap_data, 
            i, 
            category, 
            word_count_target,
            writer_template_name,
            blog_format,
            persona_instructions
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


