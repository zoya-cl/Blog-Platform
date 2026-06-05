import re
import json
from typing import List, Dict, Any, Tuple
from providers.llm_factory import get_llm
import config
from agents.utils import parse_json_robustly

SYSTEM_PROMPT = """You are an elite, highly thorough technical research agent preparing data for a placement preparation blog.
Your goal is to collect concrete, verifiable facts — specific numbers, real interview experiences, actual salary figures, and deep technical mechanisms.
You must NOT collect vague opinions, generic advice, or surface-level summaries.

For salary and compensation figures, you MUST prioritize and explicitly search for India-specific metrics (e.g., in INR, Lakhs Per Annum or LPA, like '6-12 LPA'). Only if India-specific data is completely unavailable or not found, search for and retrieve international or US-specific salary figures (in USD).

YOUR STRATEGIC RESEARCH OBJECTIVES:
You MUST aggressively search for and gather comprehensive data to answer the following {num_objectives} specific research objectives:
{research_objectives}

GUIDELINES FOR MAXIMIZING RESEARCH DEPTH:
1. FOCUS EXCLUSIVELY ON THE {num_objectives} STRATEGIC OBJECTIVES: Do NOT stop the ReAct loops or output 'Final Answer' until you have successfully collected concrete data (verifiable stats, latency/execution metrics, cost differences, and architectural trade-offs) for EVERY SINGLE ONE of the {num_objectives} objectives listed above.
2. EXECUTE TARGETED, SEPARATE SEARCHES: Do NOT try to search for everything in a single massive query. Instead, execute separate, highly-targeted queries across iterations. For example, do one search for cold start and latency metrics, another search for cost calculations and formulas, and a third search for real-world migration stories.
3. NO LAZY TERMINATION: You are strictly prohibited from declaring your work done or outputting 'Final Answer' after only 1 or 2 search queries. You must exhaustively search and scrape. Use your iterations to drill down into the details of the objectives.
4. DEEP SCRAPING (webpage_scraper): When a general search query returns a highly relevant URL containing full-text technical articles, comparison details, or specific benchmarks, call 'webpage_scraper' immediately on that URL to read the rich full text. Do not settle for brief, truncated search snippets.
5. STRICT NEWS SEARCH RESTRICTION: Only use 'news_api_search' if an objective explicitly demands recent time-sensitive events (such as 2026 layoff news, hiring announcements, or recent salary changes). NEVER use 'news_api_search' for general architectural patterns, cost models, or pros/cons. For general technical comparison concepts, 'news_api_search' returns irrelevant update logs or press releases. Use 'tavily_search' and 'webpage_scraper' instead.
6. AVOID GENERIC DEFINITIONS: Do not waste iterations searching for or explaining simple high-level definitions (like "what is serverless" or "what is cloud-native"). The writing agent is already expert in the definitions. Spend your loops on finding deep operational comparisons, specific features, tradeoffs, and metrics.
7. GROUNDING CITATIONS: For every single fact you record, you must capture its exact, valid 'source_url' and 'retrieved_at' so the writing agent can cite it.

You have access to the following tools:
{tools_description}

You must execute a ReAct-style loop. For each iteration, output:
Thought: <your reasoning about what facts you still need to find to answer the objectives, which tool to use next, and why>
Action: <the exact name of the tool to invoke>
Action Input: <the query string or parameter for the tool>

After the tool runs, you will see:
Observation: <the raw tool output>

When you have answered all {num_objectives} research objectives thoroughly (typically requiring 6 to 8 iterations), finish with:
Thought: I have gathered all required facts.
Final Answer: <summarize the research results, explicitly listing each detailed technical fact with its source URL>

Let's begin!"""

JOB_ROLE_CAREER_TRENDS_PROMPT = """You are a Lead Research Director specializing in Job Roles and Career Trends.
Given the target blog title and category, your task is to compile a list of highly specific research objectives that a research agent must investigate.
Do NOT hardcode this to exactly 7 objectives; instead, dynamically determine how many objectives are needed (typically between 4 to 6) to cover the topic deeply without filler.

Ensure the objectives capture:
1. Role Definition & Industry Evolution (foundational responsibilities, 2026 market demand shifts).
2. Key Competency & Skills Mapping (exact tools, languages, certifications, or competencies required).
3. Market Salaries & Compensation Scales: You MUST explicitly prioritize India-specific salary metrics (in INR or Lakhs Per Annum / LPA, e.g. 6-12 LPA). Include objectives to search for India-specific entry-level and senior numbers first, and only search for international/US salaries (in USD) as a fallback if India is not found.
4. Career Trajectory & Growth (milestones, transition options, long-term outlook).
5. Hiring Patterns & Interview Hurdles (common filters, hiring bar changes in 2026).

Adhere to these rules:
- Only output a raw JSON array of strings containing the objectives.
- Do NOT mix system architecture details (like latency, vm billings, or workload orchestration) into career trend topics.
- Example JSON Output:
[
  "Objective 1",
  "Objective 2",
  ...
]"""

RESUME_WRITING_PROMPT = """You are a Lead Research Director specializing in Resume Writing and Portfolio Building.
Given the target blog title and category, your task is to compile a list of highly specific research objectives that a research agent must investigate.
Do NOT hardcode this to exactly 7 objectives; dynamically determine how many objectives are needed (typically between 4 to 6) to cover the topic deeply.

Ensure the objectives capture:
1. ATS (Applicant Tracking System) Optimization (exact keyword strategies, parser formatting limits, ranking algorithms).
2. Resume Anatomy & Structure (ideal layout, section hierarchy, S.T.A.R. methodology alignment for bullet points).
3. Project & Experience Packaging (verifiable metrics, scale of projects, how to present Github portfolios/contributions).
4. SDE-Specific Pitching (how to tailor resumes for frontend/backend/devops, what projects grab recruiters' attention).
5. Target Industry Demands & Salary Impact: Search for how resume optimizations impact starting compensation. Prioritize India-specific placement salary impacts (LPA/INR) first, falling back to international data if India isn't found.

Adhere to these rules:
- Only output a raw JSON array of strings containing the objectives.
- Do NOT mix system architecture details (like latency, vm billings, or workload orchestration) into resume writing.
- Example JSON Output:
[
  "Objective 1",
  "Objective 2",
  ...
]"""

PLACEMENT_ROADMAPS_PROMPT = """You are a Lead Research Director specializing in SDE Placements and Learning Roadmaps.
Given the target blog title and category, your task is to compile a list of highly specific research objectives that a research agent must investigate.
Do NOT hardcode this to exactly 7 objectives; dynamically determine how many objectives are needed (typically between 4 to 6) to cover the topic deeply.

Ensure the objectives capture:
1. Core Roadmap Milestones (step-by-step learning progression, recommended phases, key topics).
2. Preparation Timelines & Hours (ideal timeline in months, daily/weekly hour commitments, mock interviews).
3. Essential Resources & Frameworks (curated platforms like roadmap.sh, specific courses, tools, active Github repos).
4. DSA vs Practical Projects balance (how to allocate time between problem-solving and app building).
5. Placement Entry Salaries: Prioritize SDE entry-level package details in India (LPA/INR) for companies hiring from these roadmaps. Only fall back to US/International packages (USD) if India is not found.

Adhere to these rules:
- Only output a raw JSON array of strings containing the objectives.
- Do NOT mix system architecture details (like latency, vm billings, or workload orchestration) into learning roadmaps.
- Example JSON Output:
[
  "Objective 1",
  "Objective 2",
  ...
]"""

INTERVIEW_QUESTION_COLLECTIONS_PROMPT = """You are a Lead Research Director specializing in Tech Interview Question Collections.
Given the target blog title and category, your task is to compile a list of highly specific research objectives that a research agent must investigate.
Do NOT hardcode this to exactly 7 objectives; dynamically determine how many objectives are needed (typically between 4 to 6) to cover the topic deeply.

Ensure the objectives capture:
1. Target List Requirements: If the target blog title specifies a list count or specific number of items (e.g. 'Top 20 Graph Algorithms', 'Top 50 Arrays Questions'), you MUST formulate Objective 1 to specifically demand that the research agent finds, lists, and gathers the complete list of exactly that target number of items to satisfy the title's promise.
2. Coding Standards & Complexity Bounds (time and space complexity expectations, optimal patterns like two-pointer, sliding window, DFS/BFS).
3. Evaluation Criteria & Mock Rubrics (what interviewers look for: dry runs, edge case handling, clean code structure).
4. Company Recency & Target Placements: Specific FAANG or top product company interview trends in 2026.
5. Salary & Level Expectations: Prioritize salary scales for levels clearing these questions in India (LPA/INR), falling back to international USD if not found.

Adhere to these rules:
- Only output a raw JSON array of strings containing the objectives.
- Do NOT mix system architecture details (like latency, vm billings, or workload orchestration) into interview collections.
- Example JSON Output:
[
  "Objective 1",
  "Objective 2",
  ...
]"""

DSA_CODING_PROMPT = """You are a Lead Research Director specializing in Data Structures, Algorithms, and SDE Coding Prep.
Given the target blog title and category, your task is to compile a list of highly specific research objectives that a research agent must investigate.
Do NOT hardcode this to exactly 7 objectives; dynamically determine how many objectives are needed (typically between 4 to 6) to cover the topic deeply.

Ensure the objectives capture:
1. Target List Requirements: If the title specifies a list count (e.g., 'Top 20 Graph Algorithms'), Objective 1 MUST demand finding, listing, and gathering the complete list of exactly that target number of items.
2. Algorithmic Patterns & Mathematical Bounds (foundational data structure concepts, core proof/mechanics, worst/average case complexity analysis).
3. Problem Solving Framework (how to map problems to patterns, common pitfalls, optimization strategies).
4. Industry Coding Round Expectations (live coding expectations, whiteboard vs IDE, test case generation).
5. SDE Placement Rewards: Compensation expectations for candidates mastering these DSA topics. Prioritize India placement salary metrics (LPA/INR), falling back to USD/International only if not found.

Adhere to these rules:
- Only output a raw JSON array of strings containing the objectives.
- Do NOT mix system architecture details (like latency, vm billings, or workload orchestration) into DSA topics.
- Example JSON Output:
[
  "Objective 1",
  "Objective 2",
  ...
]"""

COMPARISON_ARTICLES_PROMPT = """You are a Lead Research Director specializing in Technical and Architectural Comparisons.
Given the target blog title and category, your task is to compile a list of highly specific research objectives that a research agent must investigate.
Do NOT hardcode this to exactly 7 objectives; dynamically determine how many objectives are needed (typically between 4 to 6) to cover the topic deeply.

Ensure the objectives capture:
1. Foundational Architecture & Mechanics (core definitions, setups, basic components, execution lifecycle).
2. Pros, Cons & Structural Design Trade-offs (concrete architectural advantages, limitations, operational friction).
3. Resource Billing & Cost Models (provisioned sizing vs pay-per-execution triggers, idle compute penalties, cold start costs).
4. Latency & Performance Speed Profiles (latency bounds, cold start times, scaling speed, warm container pooling, benchmarks).
5. Setup, Operational & Deployment Complexity (maintenance overhead, configuration, pipeline deployment, team size requirement).
6. Production Cases & 2026 Adoption Trends (documented migration metrics, modern ecosystem shifts, 2026 industry cases).

Adhere to these rules:
- Only output a raw JSON array of strings containing the objectives.
- Do NOT mention resume formatting, placement guides, or job role trends here. Keep the focus entirely technical and architectural.
- Example JSON Output:
[
  "Objective 1",
  "Objective 2",
  ...
]"""

AI_TECHNOLOGY_PROMPT = """You are a Lead Research Director specializing in Artificial Intelligence and Machine Learning Technology.
Given the target blog title and category, your task is to compile a list of highly specific research objectives that a research agent must investigate.
Do NOT hardcode this to exactly 7 objectives; dynamically determine how many objectives are needed (typically between 4 to 6) to cover the topic deeply.

Ensure the objectives capture:
1. Model & Pipeline Architecture (core mechanism, training/fine-tuning setups, prompt caching, agentic loop design).
2. Inference Latency & Scale Performance (tokens/sec, time-to-first-token, batching, GPU/TPU resource constraints).
3. Compute Costs & API Pricing Models (input/output token costs, model host costs, fine-tuning expense comparisons).
4. Tool Integration & Framework Setup (LangChain/LlamaIndex, vector DB setups, model orchestration tools, deployment pipeline).
5. Real-World AI Case Studies & 2026 Trends (production implementations, optimization metrics, recent architectural shifts).

Adhere to these rules:
- Only output a raw JSON array of strings containing the objectives.
- Do NOT mix in placement guides or resume tips. Focus purely on deep AI architecture, operations, and pricing.
- Example JSON Output:
[
  "Objective 1",
  "Objective 2",
  ...
]"""

DEVELOPER_TECHNOLOGY_PROMPT = """You are a Lead Research Director specializing in Developer Frameworks, Tools, and Infrastructure.
Given the target blog title and category, your task is to compile a list of highly specific research objectives that a research agent must investigate.
Do NOT hardcode this to exactly 7 objectives; dynamically determine how many objectives are needed (typically between 4 to 6) to cover the topic deeply.

Ensure the objectives capture:
1. Core Techstack Mechanics (fundamental engine, design patterns, lifecycle, key features, syntax/semantics).
2. Pros, Cons & Practical Trade-offs (operational efficiency, community size, feature velocity, tooling quality).
3. Deployment, Hosting & Uptime Cost Models (cloud provider setup, hosting fees, developer licensing, scaling expenses).
4. Performance & Scalability Benchmarks (memory footprint, startup speeds, execution speeds, profiling statistics).
5. Ecosystem Integration & 2026 Shifts (compatibility with main cloud setups, version upgrades, modern developer adoption).

Adhere to these rules:
- Only output a raw JSON array of strings containing the objectives.
- Keep the focus entirely technical and developer-centric.
- Example JSON Output:
[
  "Objective 1",
  "Objective 2",
  ...
]"""

CATEGORY_PROMPTS = {
    "Job Role and Career Trends": JOB_ROLE_CAREER_TRENDS_PROMPT,
    "Resume Writing": RESUME_WRITING_PROMPT,
    "Placement Roadmaps": PLACEMENT_ROADMAPS_PROMPT,
    "Interview Question Collections": INTERVIEW_QUESTION_COLLECTIONS_PROMPT,
    "DSA and Coding": DSA_CODING_PROMPT,
    "Comparison Articles": COMPARISON_ARTICLES_PROMPT,
    "AI Technology": AI_TECHNOLOGY_PROMPT,
    "Developer Technology": DEVELOPER_TECHNOLOGY_PROMPT
}

def generate_research_objectives(title: str, category: str) -> List[str]:
    """
    Calls the medium LLM model to dynamically generate technical research objectives for the topic.
    """
    print(f"Generating structured research objectives for topic: '{title}' in category: '{category}'...")
    llm = get_llm("medium", temperature=0.0)
    
    # Resolve category-specific prompt template, falling back dynamically
    base_prompt = CATEGORY_PROMPTS.get(category)
    if not base_prompt:
        if any(c in category for c in ["Comparison", "Technology", "AI"]):
            base_prompt = COMPARISON_ARTICLES_PROMPT
        else:
            base_prompt = PLACEMENT_ROADMAPS_PROMPT
            
    prompt = base_prompt + f"\n\nTarget Blog Title: {title}\nBlog Category: {category}\nObjectives JSON Array:"
    
    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        
        objectives = parse_json_robustly(content)
        if isinstance(objectives, list) and len(objectives) >= 3:
            print(f"Successfully generated {len(objectives)} structured research objectives.")
            return objectives
    except Exception as e:
        print(f"Warning: Failed to generate dynamic research objectives: {e}. Falling back to default objectives.")
        
    # Standard static fallbacks if LLM call fails
    if any(c in category for c in ["Comparison", "Technology", "AI"]):
        return [
            f"Identify core definitions, foundational concepts, and key mechanics for: '{title}'.",
            f"Identify specific pros, cons, and critical trade-offs for: '{title}'.",
            f"Find concrete cost-model differences, resource overheads, or financial/compute implications for: '{title}'.",
            f"Find latency profiles, execution speed metrics, scaling behaviors, or performance limits for: '{title}'.",
            f"Identify operational complexity, team size requirements, deployment overhead, or maintenance needs for: '{title}'.",
            f"Identify real-world industry adoption stories, migration metrics, and modern 2026 shifts for: '{title}'."
        ]
    return [
        f"Identify role definitions, career outlook, and foundational competency expectations for: '{title}'.",
        f"Identify specific pros, cons, and career path trade-offs associated with: '{title}'.",
        f"Find concrete India-specific salary trends (LPA/INR) for entry-level and senior roles in 2026 related to: '{title}' (fallback to international if not found).",
        f"Identify technical skills, DSA complexity bounds, framework masteries, or system design expectations for: '{title}'.",
        f"Identify active portfolio setup, resume formatting rules, and packaging strategies for: '{title}'."
    ]

def format_tools_description(tools: List[Any]) -> str:
    desc = []
    for t in tools:
        doc = t.description or "No description provided."
        desc.append(f"- Name: {t.name}\n  Description: {doc}")
    return "\n".join(desc)

def parse_action(llm_output: str) -> Tuple[str, str, str]:
    """
    Parses LLM output for Action and Action Input.
    Returns (action_name, action_input, final_answer).
    """
    # Check for Final Answer
    final_match = re.search(r"Final\s+Answer\s*:\s*(.*)", llm_output, re.DOTALL | re.IGNORECASE)
    if final_match:
        return "", "", final_match.group(1).strip()
        
    # Search for Action and Action Input
    action_match = re.search(r"Action\s*:\s*([a-zA-Z0-9_-]+)", llm_output, re.CASEINSENSENSITIVE if hasattr(re, 'CASEINSENSENSITIVE') else re.IGNORECASE)
    action_input_match = re.search(r"Action\s+Input\s*:\s*(.*)", llm_output, re.CASEINSENSENSITIVE if hasattr(re, 'CASEINSENSENSITIVE') else re.IGNORECASE)
    
    action = action_match.group(1).strip() if action_match else ""
    action_input = action_input_match.group(1).strip() if action_input_match else ""
    
    # Strip quotes if action_input was wrapped
    if action_input.startswith(("'", '"')) and action_input.endswith(("'", '"')):
        action_input = action_input[1:-1]
        
    return action, action_input, ""

def run_retrieval_agent(title: str, category: str, seo_context: Dict[str, Any], tools: List[Any], depth: str) -> str:
    """
    Executes the ReAct research loop.
    Returns a string containing the raw execution transcript (thoughts, actions, and observations).
    """
    max_iterations = config.RETRIEVAL_ITERATION_CAPS.get(depth, 8)
    if max_iterations <= 0 or not tools:
        print(f"Skipping retrieval agent execution (depth={depth}, iteration cap={max_iterations})")
        return "No retrieval performed."
        
    # 1. Dynamically generate structured research objectives
    objectives = generate_research_objectives(title, category)
    objectives_str = "\n".join([f"  {idx}. {obj}" for idx, obj in enumerate(objectives, 1)])
    
    print("\n--- Structured Research Objectives Generated ---")
    print(objectives_str)
    print("------------------------------------------------\n")
    
    llm = get_llm("medium", temperature=0.1)
    tools_map = {t.name: t for t in tools}
    tools_description = format_tools_description(tools)
    
    # Dynamic context block
    dynamic_prompt = f"""
---
Target Blog Title: {title}
Blog Category: {category}
SEO Intent Signals: {json.dumps(seo_context.get('intent_signals', {}))}
Primary Keyword: {seo_context.get('primary_keyword')}
Secondary Keywords: {', '.join(seo_context.get('secondary_keywords', []))}
"""
    
    # Initialize history
    # Initialize history and termination override state
    history = []
    has_blocked_premature = False
    
    print(f"Starting ReAct retrieval agent for '{title}' (depth={depth}, max_iter={max_iterations})...")
    
    for i in range(1, max_iterations + 1):
        print(f"\n--- ReAct Iteration {i}/{max_iterations} ---")
        
        # Build prompt from system instructions with injected objectives, tools, and history
        system_instructions = SYSTEM_PROMPT.format(
            num_objectives=len(objectives),
            research_objectives=objectives_str,
            tools_description=tools_description
        )
        prompt = system_instructions + dynamic_prompt
        if history:
            prompt += "\n" + "\n".join(history)
        prompt += f"\nThought:"
        
        try:
            # Invoke LLM with stop sequence to prevent generating observations
            response = llm.invoke(prompt, stop=["Observation:", "\nObservation:"])
            output = response.content if hasattr(response, "content") else str(response)
            output_full = f"Thought: {output}"
            
            # Print agent thoughts
            first_lines = output_full.split("\n")[:2]
            print(f"Agent Output snippet:\n  " + "\n  ".join(first_lines))
            
            # Parse actions
            action, action_input, final_answer = parse_action(output_full)
            
            # Append output to history
            history.append(output_full)
            
            if final_answer:
                if i < 5 and not has_blocked_premature:
                    has_blocked_premature = True
                    print(f"Agent attempted premature termination at iteration {i}. Blocking once to force deeper research...")
                    objectives_list_str = "\n".join([f"  - {obj}" for obj in objectives])
                    reminder = (
                        f"System Reminder: You attempted to complete the research with 'Final Answer' at iteration {i}. "
                        f"However, you have NOT yet performed sufficient targeted searches or scraped detailed webpages for all {len(objectives)} strategic objectives.\n"
                        "Specifically, make sure you have gathered concrete, verifiable facts for the following objectives:\n"
                        f"{objectives_list_str}\n"
                        "Do NOT stop early unless you have executed targeted searches/scrapes for these remaining objectives. "
                        "Execute another highly-targeted 'tavily_search' or use 'webpage_scraper' to get deep data."
                    )
                    history.append(f"Observation: {reminder}")
                    print(f"System: Injected generalized early termination block reminder.")
                    continue
                else:
                    if has_blocked_premature:
                        print(f"Agent insisted on termination after receiving early reminder. Allowing termination.")
                    else:
                        print(f"Agent finished with Final Answer.")
                    break
                
            if not action:
                print("Warning: Agent failed to specify action. Ending loop.")
                break
                
            print(f"Agent decided to invoke tool '{action}' with input '{action_input}'")
            
            # Execute tool
            if action in tools_map:
                try:
                    tool_func = tools_map[action]
                    observation = tool_func.invoke(action_input)
                except Exception as tool_err:
                    observation = f"Error executing tool {action}: {tool_err}"
            else:
                observation = f"Error: Tool '{action}' does not exist in registry. Available tools are: {list(tools_map.keys())}"
                
            # Log observation snippet (display up to 15 lines for clear terminal visibility)
            obs_lines = observation.split("\n")
            obs_snippet = obs_lines[:15]
            snippet_text = "\n  ".join(obs_snippet)
            if len(obs_lines) > 15 or len(observation) > 800:
                snippet_text += "\n  ... [Truncated for console display]"
            print(f"Tool Observation snippet:\n  {snippet_text}")
            
            # Append observation to history
            history.append(f"Observation: {observation}")
            
        except Exception as e:
            print(f"Error in ReAct loop iteration {i}: {e}")
            break
            
    # Return full execution log
    return "\n".join(history)
