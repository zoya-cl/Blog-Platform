import json
import re
from typing import Dict, Any
from providers.llm_factory import get_llm
from schemas import RetrievedContext
from agents.utils import parse_json_robustly

# Static prompt rules (first for caching)
FORMATTER_PROMPT = """You are the Research Aggregator. Your task is to process raw research logs collected by a retrieval agent and aggregate them into a structured JSON object to preserve their maximum richness and utility for the writing phase.

Apply these strict rules:
1. UNSTRUCTURED DATA (Tavily, News API, Webpage Scraper):
   - Extract massive, comprehensive technical paragraphs of AT LEAST 6 to 10+ full sentences (150 to 250 words) instead of short facts or simple lines.
   - Do NOT summarize or condense the observations into brief bullets. Copy-paste or extract the full, detailed technical paragraphs verbatim or with minimal editing from the 'Observation' sections to preserve their complete semantic depth.
   - Each paragraph in 'verified_facts' must retain detailed architectural setups, exact parameter metrics, CLI command structures, code snippets, execution constraints, and thorough technical context.
   - CRITICAL EVIDENCE-GROUNDING & CONTEXT PRESERVATION: You MUST capture the full, raw context of every finding to maximize trust. For salary figures or statistics, you are strictly REQUIRED to preserve:
     a) The exact region or location (e.g. India, United States, San Jose CA, London UK). You MUST prioritize India-specific compensation metrics (e.g., INR or Lakhs Per Annum / LPA, like '12-15 LPA'). If India-specific salaries are not present in the logs, only then capture international/US-specific compensation (e.g., in USD).
     b) The exact currency and bonuses (e.g. '₹12 LPA', '$133,334 USD base plus a $5,000 cash bonus').
     c) The exact data sample size or baseline metrics (e.g. 'based on a sample of 40.3k salaries' or 'benchmarked from AmbitionBox October 2025 data').
     d) The exact date or freshness metadata (e.g. 'Ravio Trends Report published October 2025' or 'BLS May 2024 survey').
     Under-specifying, losing sample sizes, or omitting the date/source parameters is a critical failure.
   - CRITICAL NOISE & OCR Graph Axis FILTERING: You MUST scan for and completely filter out all raw PDF-scraping or table-parsing artifacts, axis coordinates, coordinate scale sequences, or isolated axis months (such as '0.6 1.0 1.4 1.8 2.2 Dec-16 Jun-17 Dec-17'). These are random axis line metrics from visual charts in PDFs, not readable technical facts! You are strictly prohibited from leaking these coordinate sequences into your claims. Clean them out entirely.
   - ZERO FILLER POLICY (THE 'SO-WHAT' TEST): You must never extract basic, high-level, generic summaries or "filler" sentences (such as 'Software developers use programming and creative skills to build software', 'Job duties vary based on requirements', or 'Graphs are non-linear data structures with nodes and edges'). For every fact you select, ask yourself: *"Would removing this fact change the technical quality or credibility of the placement blog?"* If the fact is an obvious truism, generic advice, or high-level filler that the writer already knows, **DELETE IT**. Retain only deep operational parameters, algorithmic complexities, real interview processes/rounds, specific pricing calculations, or actual hiring stats.
   - CRITICAL NUMERICAL DATA RETENTION: You MUST retain all precise numerical data, cost pricing formulas, latency metrics, milliseconds, currency symbols ($/₹), exact decimal parameters, and specific percentages verbatim. If an observation contains specific numbers (e.g., '12 LPA', '$0.0000166667 per GB-second', '$1.00 per million requests', '$3.50 per million', or '60-70% reduction'), you are strictly FORBIDDEN from omitting, rounding, or generalizing them. Under-specifying or stripping exact figures is a critical failure.
   - For every extracted paragraph, you MUST carry on the correct 'source_url' and 'retrieved_at' so the writer agent can cite it in the final blog.
2. FACT DIVERSITY AND MULTI-DIMENSIONAL COVERAGE:
   - You MUST extract at least 5 to 7 highly diverse, comprehensive verified facts in the 'verified_facts' list.
   - Each fact must focus on a distinct technical or career dimension gathered in the logs (e.g. Core Concepts/Definitions, Pros/Cons Trade-offs, Cost Model Comparisons/Formulas, Scalability/Latency Metrics, Operational Complexity/Team Size, Traffic Patterns/Workload Use Cases, and Industry Examples/Trends).
   - Do NOT duplicate or cluster all facts around high-level concepts or simple definitions. Ensure all the different objectives researched by the agent are represented in the verified facts.
3. STRUCTURED DATA (LeetCode, NeetCode, Roadmap.sh):
   - Do NOT summarize or explain lists of programming questions or roadmaps into sentences.
   - If there is a list of coding problems returned by LeetCode or NeetCode in the logs, COPY and PASTE the raw array of problem dicts directly into the 'leetcode_data' field.
   - If there is a list of roadmap steps or learning paths returned by roadmap.sh in the logs, COPY and PASTE the raw roadmap dict directly into the 'roadmap_data' field.
4. GENERAL METADATA & PLACEHOLDER PREVENTION:
   - Extract actual salary ranges into 'salary_ranges'. You MUST prioritize capturing India-specific packages (INR/LPA) and fallback to USD/international only if India is not found in the raw logs.
   - Extract actual key skills into 'skill_requirements'.
   - Extract actual tools and frameworks into 'tech_stacks'.
   - Extract actual anonymized candidate interview quotes into 'student_experiences'.
   - CRITICAL WARNING: The values in the schema below (like 'Software Engineer (Fresher)', '6 - 8 LPA', 'Python', 'System Design', 'Docker', 'Kubernetes', or the anonymized candidate transaction locking quote) are PURELY ILLUSTRATIVE EXAMPLES. You MUST NOT copy, hallucinate, or echo these illustrative placeholder values in your response. If the raw research logs DO NOT contain relevant salary figures, skill lists, tech stacks, or candidate interview quotes, you MUST return empty fields (e.g., "salary_ranges": null, "skill_requirements": [], "tech_stacks": [], "student_experiences": []) rather than leaking example placeholders!

You must output valid JSON matching the following schema structure:
{{
  "verified_facts": [
    {{
      "claim": "A massive, highly detailed, context-rich 6-10+ line technical paragraph (150-250 words) outlining the complete technical mechanism, architectural setup, command structures, code details, and detailed background context verbatim from the research logs.",
      "source_url": "http://example.com/source-url",
      "retrieved_at": "YYYY-MM-DD"
    }}
  ],
  "salary_ranges": {{
    "Software Engineer (Fresher)": "6 - 8 LPA"
  }},
  "skill_requirements": ["Python", "System Design"],
  "tech_stacks": ["Docker", "Kubernetes"],
  "student_experiences": [
    "Anonymized candidate reported facing 3 rounds of technical interviews focusing on SQL and transaction locking."
  ],
  "sources": ["http://example.com/source-url"],
  "leetcode_data": [
    {{
      "title": "Median of Two Sorted Arrays",
      "difficulty": "Hard",
      "acceptance_rate": "46.6%",
      "url": "https://leetcode.com/problems/median-of-two-sorted-arrays/"
    }}
  ],
  "roadmap_data": {{
    "title": "Backend Developer",
    "steps": [
      {{
        "step": 1,
        "topic": "Internet",
        "details": "How does the internet work, HTTP, browsers"
      }}
    ]
  }}
}}

Return ONLY valid raw JSON. Do not include any explanations, markdown code blocks, or leading/trailing text."""

def format_retrieved_data(title: str, category: str, raw_research_log: str) -> RetrievedContext:
    """
    Calls the medium LLM model to parse and aggregate raw research logs into a Pydantic RetrievedContext.
    """
    print("Running Research Aggregator node: Aggregating raw research logs into RetrievedContext...")
    
    # 1. Clean raw log if too large to prevent context limits (increased to 100k)
    truncated_log = raw_research_log
    if len(raw_research_log) > 100000:
        print(f"Warning: Raw research log is very long ({len(raw_research_log)} chars). Truncating for model call...")
        truncated_log = raw_research_log[:100000] + "\n[Truncated due to size...]"
        
    # Upgrade to medium model for perfect rule-following and schema precision
    llm = get_llm("medium", temperature=0.0)
    
    # Dynamic context block
    dynamic_prompt = f"""
---
Target Blog Title: {title}
Blog Category: {category}

Raw Research Logs:
{truncated_log}

JSON Response:"""

    prompt = FORMATTER_PROMPT + dynamic_prompt
    
    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        
        parsed_dict = parse_json_robustly(content)
        
        # Backfill sources from verified_facts if missing or empty
        if not parsed_dict.get("sources"):
            urls = set()
            for fact in parsed_dict.get("verified_facts", []):
                url = fact.get("source_url")
                if url:
                    urls.add(url)
            parsed_dict["sources"] = sorted(list(urls))
        
        # Build Pydantic model for validation
        retrieved_context = RetrievedContext(**parsed_dict)
        print(f"Successfully validated RetrievedContext. Facts: {len(retrieved_context.verified_facts)}, Sources: {len(retrieved_context.sources)}.")
        return retrieved_context
        
    except Exception as e:
        print(f"Error in Research Aggregator node: {e}")
        raise RuntimeError(f"Research Aggregator failed to process research logs: {str(e)}") from e
