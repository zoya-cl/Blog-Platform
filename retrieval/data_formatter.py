import json
import re
from typing import Dict, Any
from providers.llm_factory import get_llm
from schemas import RetrievedContext
from agents.utils import parse_json_robustly

FORMATTER_PROMPT = """You are an expert Research Aggregator. Your task is to process raw research logs collected from web searches and webpage scraping, and extract a clean list of verified facts, key technical concepts, tools, and source URLs into a structured JSON object.

Rules:
1. VERIFIED FACTS ('verified_facts'):
   - Extract 4 to 8 distinct, factual paragraphs or claims.
   - Retain concrete details: metrics, formulas, code snippets, benchmarks, operational trade-offs, statistics, and official documentation claims.
   - Avoid generic high-level fluff ("X is popular").
   - Include the exact 'source_url' and 'retrieved_at' date for every fact.
2. TECH STACKS ('tech_stacks'):
   - Extract key tools, frameworks, databases, and technologies mentioned.
3. SKILL REQUIREMENTS ('skill_requirements'):
   - Extract core skills or prerequisite concepts required for this topic.
4. SOURCES ('sources'):
   - Extract all unique source URLs found in the logs.

Output schema:
{
  "verified_facts": [
    {
      "claim": "Concrete technical fact or benchmark paragraph...",
      "source_url": "http://example.com/source-url",
      "retrieved_at": "YYYY-MM-DD"
    }
  ],
  "skill_requirements": ["System Design", "Python"],
  "tech_stacks": ["Docker", "Kubernetes"],
  "sources": ["http://example.com/source-url"]
}

Return ONLY valid JSON."""

def format_retrieved_data(title: str, category: str, raw_research_log: str) -> RetrievedContext:
    """
    Parses and aggregates raw research logs into a Pydantic RetrievedContext.
    """
    print(f"\n--- Aggregating Research Data for '{title}' [{category}] ---")
    
    truncated_log = raw_research_log
    if len(raw_research_log) > 50000:
        truncated_log = raw_research_log[:50000] + "\n[Truncated...]"
        
    llm = get_llm("medium", temperature=0.0)
    
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
        
        # Backfill sources from verified_facts if missing
        if not parsed_dict.get("sources"):
            urls = set()
            for fact in parsed_dict.get("verified_facts", []):
                url = fact.get("source_url")
                if url:
                    urls.add(url)
            parsed_dict["sources"] = sorted(list(urls))
            
        retrieved_context = RetrievedContext(**parsed_dict)
        print(f"Successfully aggregated research data. Facts: {len(retrieved_context.verified_facts)}, Sources: {len(retrieved_context.sources)}.")
        return retrieved_context
        
    except Exception as e:
        print(f"Warning: Research Aggregator parsing failed: {e}. Returning minimal context.")
        return RetrievedContext(
            verified_facts=[],
            skill_requirements=[],
            tech_stacks=[],
            sources=[]
        )
