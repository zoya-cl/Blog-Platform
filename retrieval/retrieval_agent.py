import json
import re
from typing import List
from providers.llm_factory import get_llm
from agents.utils import parse_json_robustly
from retrieval.tools.tavily_search import tavily_search
from retrieval.tools.webpage_scraper import webpage_scraper

QUERY_GEN_PROMPT = """Given a blog topic and category, generate exactly 3 highly specific web search queries to find concrete technical facts, benchmarks, architecture trade-offs, or real-world data.

Blog Topic: {topic}
Blog Category: {category}

Return ONLY a JSON array of 3 query strings. Example:
["query 1", "query 2", "query 3"]"""

def run_direct_search(topic: str, category: str) -> str:
    """
    Executes a simple 2-step direct search:
    1. Asks LLM for 3 targeted search queries.
    2. Runs Tavily search on each query + optionally scrapes top URLs.
    Returns combined raw search results text.
    """
    print(f"\n--- Running Direct Search for '{topic}' [{category}] ---")
    
    # 1. Generate search queries
    llm = get_llm("small", temperature=0.0)
    prompt = QUERY_GEN_PROMPT.format(topic=topic, category=category)
    
    queries = []
    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        parsed = parse_json_robustly(content)
        if isinstance(parsed, list):
            queries = [str(q) for q in parsed[:3]]
    except Exception as e:
        print(f"Warning: Query generation failed: {e}. Using fallback query.")
        
    if not queries:
        queries = [
            f"{topic} key concepts and architecture",
            f"{topic} performance benchmarks production trade-offs",
            f"{topic} best practices examples"
        ]

    # 2. Execute Tavily search queries
    results_text = []
    urls_to_scrape = []
    
    for idx, query in enumerate(queries, 1):
        print(f"  Search {idx}/{len(queries)}: '{query}'")
        try:
            search_output = tavily_search.invoke({"query": query})
            results_text.append(f"=== Search Query: {query} ===\n{search_output}")
            
            # Extract URLs from Tavily search output for optional deep scraping
            found_urls = re.findall(r"URL:\s*(https?://[^\s\n]+)", search_output)
            for u in found_urls:
                if u not in urls_to_scrape and not any(skip in u for skip in ["example.com"]):
                    urls_to_scrape.append(u)
        except Exception as e:
            print(f"  Warning: Search query '{query}' failed: {e}")

    # 3. Deep scrape top 1-2 unique URLs if available
    if urls_to_scrape:
        scrape_target = urls_to_scrape[:2]
        for url in scrape_target:
            print(f"  Scraping URL: {url[:60]}...")
            try:
                scraped = webpage_scraper.invoke({"url": url})
                if scraped and not scraped.startswith("Error"):
                    results_text.append(f"=== Scraped Content ({url}) ===\n{scraped[:4000]}")
            except Exception as e:
                print(f"  Warning: Scraping {url} failed: {e}")

    combined = "\n\n".join(results_text)
    print(f"Direct Search complete. Total raw content size: {len(combined)} chars.")
    return combined

def run_retrieval_agent(topic: str, category: str, *args, **kwargs) -> str:
    """Backward compatibility wrapper mapping to run_direct_search."""
    return run_direct_search(topic, category)
