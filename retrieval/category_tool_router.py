from typing import List, Any
# Import our tool functions
from retrieval.tools.tavily_search import tavily_search
from retrieval.tools.news_api_search import news_api_search
from retrieval.tools.roadmap_sh_fetcher import roadmap_sh_fetcher
from retrieval.tools.leetcode_fetcher import leetcode_fetcher
from retrieval.tools.neetcode_roadmap_fetcher import neetcode_roadmap_fetcher
from retrieval.tools.webpage_scraper import webpage_scraper

def get_tools_for_category(category: str, depth: str = "standard") -> List[Any]:
    """
    Returns the list of active LangChain @tool objects.
    All categories get equal tool access.
    """
    if depth == "none":
        return []
        
    return [
        tavily_search,
        news_api_search,
        webpage_scraper,
        roadmap_sh_fetcher,
        leetcode_fetcher,
        neetcode_roadmap_fetcher
    ]
