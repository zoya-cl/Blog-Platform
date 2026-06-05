import urllib.request
import urllib.parse
from langchain_core.tools import tool

@tool
def webpage_scraper(url: str) -> str:
    """Scrape and read the full text content of a specific webpage URL. Use this to follow up on promising links returned by web search tools to gather deep facts."""
    print(f"  [Tool: webpage_scraper] Scraping URL: '{url}'...")
    
    url_clean = url.strip()
    if url_clean.startswith(("'", '"')) and url_clean.endswith(("'", '"')):
        url_clean = url_clean[1:-1].strip()
        
    # Prepend Jina Reader API URL
    jina_url = f"https://r.jina.ai/{url_clean}"
    
    try:
        import ssl
        context = ssl._create_unverified_context()
        
        req = urllib.request.Request(
            jina_url, 
            headers={
                "User-Agent": "Mozilla/5.0",
                "X-Return-Format": "markdown"  # Request clean markdown format from Jina
            }
        )
        with urllib.request.urlopen(req, timeout=15.0, context=context) as response:
            if response.status == 200:
                content = response.read().decode("utf-8", errors="ignore")
                # Cap the content to 8000 characters to keep context windows reasonable
                return content[:8000]
            else:
                return f"Error: Failed to fetch webpage content. Status code: {response.status}"
    except Exception as e:
        return f"Error: Failed to scrape URL '{url_clean}' due to: {str(e)}"
