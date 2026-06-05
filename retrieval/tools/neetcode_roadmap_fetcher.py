import json
import urllib.request
from typing import List, Dict, Any
from langchain_core.tools import tool

# Mapping query terms to NeetCode official patterns
NEETCODE_PATTERNS = {
    "array": "Arrays & Hashing",
    "hash": "Arrays & Hashing",
    "two pointers": "Two Pointers",
    "sliding window": "Sliding Window",
    "stack": "Stack",
    "binary search": "Binary Search",
    "linked list": "Linked List",
    "tree": "Trees",
    "trees": "Trees",
    "trie": "Tries",
    "tries": "Tries",
    "heap": "Heap / Priority Queue",
    "priority queue": "Heap / Priority Queue",
    "backtracking": "Backtracking",
    "graph": "Graphs",
    "graphs": "Graphs",
    "advanced graph": "Advanced Graphs",
    "advanced graphs": "Advanced Graphs",
    "dynamic programming": "1-D Dynamic Programming",
    "1d dp": "1-D Dynamic Programming",
    "2d dp": "2-D Dynamic Programming",
    "greedy": "Greedy",
    "interval": "Intervals",
    "intervals": "Intervals",
    "math": "Math & Geometry",
    "geometry": "Math & Geometry",
    "bit": "Bit Manipulation",
    "bit manipulation": "Bit Manipulation"
}

# Offline fallback dataset for main categories in case GitHub API fails
NEETCODE_FALLBACK = [
    {
        "problem": "Contains Duplicate",
        "pattern": "Arrays & Hashing",
        "link": "contains-duplicate/",
        "difficulty": "Easy",
        "neetcode150": True,
        "blind75": True
    },
    {
        "problem": "Valid Anagram",
        "pattern": "Arrays & Hashing",
        "link": "valid-anagram/",
        "difficulty": "Easy",
        "neetcode150": True,
        "blind75": True
    },
    {
        "problem": "Two Sum",
        "pattern": "Arrays & Hashing",
        "link": "two-sum/",
        "difficulty": "Easy",
        "neetcode150": True,
        "blind75": True
    },
    {
        "problem": "Valid Palindrome",
        "pattern": "Two Pointers",
        "link": "valid-palindrome/",
        "difficulty": "Easy",
        "neetcode150": True,
        "blind75": True
    },
    {
        "problem": "Container With Most Water",
        "pattern": "Two Pointers",
        "link": "container-with-most-water/",
        "difficulty": "Medium",
        "neetcode150": True,
        "blind75": True
    },
    {
        "problem": "Best Time to Buy and Sell Stock",
        "pattern": "Sliding Window",
        "link": "best-time-to-buy-and-sell-stock/",
        "difficulty": "Easy",
        "neetcode150": True,
        "blind75": True
    },
    {
        "problem": "Longest Substring Without Repeating Characters",
        "pattern": "Sliding Window",
        "link": "longest-substring-without-repeating-characters/",
        "difficulty": "Medium",
        "neetcode150": True,
        "blind75": True
    },
    {
        "problem": "Invert Binary Tree",
        "pattern": "Trees",
        "link": "invert-binary-tree/",
        "difficulty": "Easy",
        "neetcode150": True,
        "blind75": True
    },
    {
        "problem": "Maximum Depth of Binary Tree",
        "pattern": "Trees",
        "link": "maximum-depth-of-binary-tree/",
        "difficulty": "Easy",
        "neetcode150": True,
        "blind75": True
    }
]

@tool
def neetcode_roadmap_fetcher(topic: str) -> str:
    """Fetch practice coding problem lists, pattern tracks, and difficulties from NeetCode's official practice question collection. Best for DSA preparation blogs, Blind 75 / NeetCode 150 content, and coding interview pattern articles.
    
    Args:
        topic: The coding topic or pattern. You MUST query using one of these exact available pattern keys: 'array', 'hash', 'two pointers', 'sliding window', 'stack', 'binary search', 'linked list', 'tree', 'trie', 'heap', 'priority queue', 'backtracking', 'graph', 'dynamic programming', 'greedy', 'interval', 'math', 'bit'.
    """
    import re
    input_str = topic.strip()
    
    # Try parsing topic clean name from potential concatenated string
    topic_match = re.search(r"topic\s*=\s*['\"]?([^'\"]+)['\"]?", input_str, re.IGNORECASE)
    if topic_match:
        topic_clean = topic_match.group(1).strip().lower()
    else:
        topic_clean = re.sub(r"^['\"]|['\"]$", "", input_str).strip().lower()
        
    print(f"  [Tool: neetcode_roadmap_fetcher] Querying NeetCode practice questions for topic: '{topic_clean}'...")
    
    # Match search term to a standard NeetCode pattern
    target_pattern = None
    for key, val in NEETCODE_PATTERNS.items():
        if key in topic_clean:
            target_pattern = val
            break
            
    if not target_pattern:
        error_msg = (
            f"Error: Could not map query topic '{topic}' to a valid NeetCode pattern track. "
            f"Please query using one of the exact available pattern keys: "
            f"{', '.join(sorted(list(set(NEETCODE_PATTERNS.keys()))))}"
        )
        print(f"  [Tool: neetcode_roadmap_fetcher] Error: {error_msg}")
        return json.dumps({"error": error_msg}, indent=2)
            
    # 1. Fetch from NeetCode's open-source repository on GitHub
    try:
        url = "https://raw.githubusercontent.com/neetcode-gh/leetcode/main/.problemSiteData.json"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        import ssl
        context = ssl._create_unverified_context()
        
        with urllib.request.urlopen(req, timeout=10.0, context=context) as response:
            if response.status == 200:
                raw_data = json.loads(response.read().decode("utf-8"))
                
                # Filter by matched pattern
                filtered_problems = []
                for item in raw_data:
                    if item.get("pattern") == target_pattern:
                        filtered_problems.append({
                            "problem": item.get("problem"),
                            "difficulty": item.get("difficulty"),
                            "neetcode150": item.get("neetcode150", False),
                            "blind75": item.get("blind75", False),
                            "url": f"https://leetcode.com/problems/{item.get('link')}"
                        })
                
                if filtered_problems:
                    return json.dumps({
                        "neetcode_pattern": target_pattern,
                        "problems": filtered_problems
                    }, indent=2)
    except Exception as e:
        print(f"Warning: Failed to fetch live NeetCode data from GitHub: {e}. Using offline fallback...")
        
    # 2. Offline fallback
    filtered_fallback = []
    for item in NEETCODE_FALLBACK:
        if item.get("pattern") == target_pattern:
            filtered_fallback.append({
                "problem": item.get("problem"),
                "difficulty": item.get("difficulty"),
                "neetcode150": item.get("neetcode150", False),
                "blind75": item.get("blind75", False),
                "url": f"https://leetcode.com/problems/{item.get('link')}"
            })
            
    # If no fallback matched the specific pattern, return a subset of fallback
    if not filtered_fallback:
        filtered_fallback = [
            {
                "problem": item.get("problem"),
                "difficulty": item.get("difficulty"),
                "neetcode150": item.get("neetcode150", False),
                "blind75": item.get("blind75", False),
                "url": f"https://leetcode.com/problems/{item.get('link')}"
            } for item in NEETCODE_FALLBACK[:3]
        ]
        
    return json.dumps({
        "neetcode_pattern": target_pattern,
        "problems": filtered_fallback,
        "note": "Returned from offline mock database fallback"
    }, indent=2)
