import json
import urllib.request
from typing import List, Dict, Any
from langchain_core.tools import tool

# Tag mapping for search terms
TAG_MAPS = {
    "array": "array",
    "string": "string",
    "two pointers": "two-pointers",
    "sliding window": "sliding-window",
    "stack": "stack",
    "linked list": "linked-list",
    "tree": "tree",
    "trees": "tree",
    "graph": "graph",
    "graphs": "graph",
    "dynamic programming": "dynamic-programming",
    "dp": "dynamic-programming",
    "greedy": "greedy",
    "binary search": "binary-search",
    "backtracking": "backtracking"
}

@tool
def leetcode_fetcher(topic: str, limit: int = 15) -> str:
    """Fetch problem lists, topic tags, and frequency data from LeetCode. Best for DSA preparation blogs, Blind 75 content, and coding interview pattern blogs.
    
    Args:
        topic: The coding topic or pattern. You MUST query using one of these exact available keywords: 'array', 'string', 'two pointers', 'sliding window', 'stack', 'linked list', 'tree', 'graph', 'dynamic programming', 'greedy', 'binary search', 'backtracking'.
        limit: The maximum number of problems to fetch (default is 15, maximum is 50).
    """
    import re
    input_str = topic.strip()
    limit_val = limit
    
    # Try parsing limit from input string (e.g. limit=50 or , 50)
    limit_match = re.search(r"limit\s*=\s*(\d+)", input_str, re.IGNORECASE)
    if limit_match:
        limit_val = int(limit_match.group(1))
    elif "," in input_str:
        parts = input_str.split(",")
        if len(parts) == 2 and parts[1].strip().isdigit():
            input_str = parts[0].strip()
            limit_val = int(parts[1].strip())
            
    # Try parsing topic clean name
    topic_match = re.search(r"topic\s*=\s*['\"]?([^'\"]+)['\"]?", input_str, re.IGNORECASE)
    if topic_match:
        topic_clean = topic_match.group(1).strip().lower()
    else:
        topic_clean = re.sub(r"^['\"]|['\"]$", "", input_str).strip().lower()
        
    safe_limit = max(1, min(int(limit_val), 50))
    print(f"  [Tool: leetcode_fetcher] Querying coding problems for: '{topic_clean}' (limit: {safe_limit})...")
    
    # Map the search term to a standard LeetCode tag slug
    leetcode_tag = None
    for key, slug in TAG_MAPS.items():
        if key in topic_clean:
            leetcode_tag = slug
            break
            
    if not leetcode_tag:
        error_msg = (
            f"Error: Could not map query topic '{topic}' to a valid LeetCode tag. "
            f"Please query using one of the exact available keywords: "
            f"{', '.join(sorted(list(set(TAG_MAPS.keys()))))}"
        )
        print(f"  [Tool: leetcode_fetcher] Error: {error_msg}")
        return json.dumps({"error": error_msg}, indent=2)

    # 1. Try hitting LeetCode's public GraphQL endpoint
    try:
        url = "https://leetcode.com/graphql"
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        gql_query = """
        query itemLoop($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {
          problemsetQuestionList: questionList(
            categorySlug: $categorySlug
            limit: $limit
            skip: $skip
            filters: $filters
          ) {
            questions: data {
              title
              titleSlug
              difficulty
              acRate
            }
          }
        }
        """
        
        payload = {
            "query": gql_query,
            "variables": {
              "categorySlug": "",
              "limit": safe_limit,
              "skip": 0,
              "filters": {"tags": [leetcode_tag]}
            }
        }
        
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
        
        import ssl
        context = ssl._create_unverified_context()
        with urllib.request.urlopen(req, timeout=10.0, context=context) as response:
            if response.status == 200:
                raw_data = json.loads(response.read().decode("utf-8"))
                q_list = raw_data.get("data", {}).get("problemsetQuestionList", {}).get("questions", [])
                
                if not q_list:
                    return f"Error: No questions found for LeetCode tag '{leetcode_tag}'."
                
                formatted_questions = []
                for q in q_list[:safe_limit]:
                    ac_rate = round(q.get("acRate", 0), 1)
                    formatted_questions.append({
                        "title": q.get("title"),
                        "difficulty": q.get("difficulty"),
                        "acceptance_rate": f"{ac_rate}%",
                        "url": f"https://leetcode.com/problems/{q.get('titleSlug')}/"
                    })
                return json.dumps({
                    "leetcode_tag": leetcode_tag,
                    "problems": formatted_questions
                }, indent=2)
            else:
                return f"Error: LeetCode GraphQL API returned status code {response.status}."
    except Exception as e:
        return f"Error: LeetCode GraphQL query failed: {str(e)}."

