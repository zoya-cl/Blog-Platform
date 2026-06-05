import json
import urllib.request
from typing import List, Dict, Any
from langchain_core.tools import tool

# Valid slugs available on roadmap.sh
ROADMAP_SLUGS = [
    "ai-agents", "ai-data-scientist", "ai-engineer", "ai-product-builder",
    "ai-red-teaming", "android", "angular", "api-design", "aspnet-core",
    "aws", "backend", "bi-analyst", "blockchain", "claude-code", "cloudflare",
    "code-review", "computer-science", "cpp", "css", "cyber-security",
    "data-analyst", "data-engineer", "datastructures-and-algorithms",
    "design-system", "devops", "devrel", "devsecops", "django", "docker",
    "elasticsearch", "engineering-manager", "flutter", "frontend",
    "full-stack", "game-developer", "git-github", "golang", "graphql", "html",
    "ios", "java", "javascript", "kotlin", "kubernetes", "laravel", "leetcode",
    "linux", "machine-learning", "mlops", "mongodb", "nextjs", "nodejs",
    "openclaw", "php", "postgresql-dba", "product-manager", "prompt-engineering",
    "python", "qa", "react-native", "react", "redis", "rust", "shell-bash",
    "software-architect", "software-design-architecture", "spring-boot",
    "sql", "swift-ui", "system-design", "technical-writer", "terraform",
    "typescript", "ux-design", "vue", "wordpress"
]

@tool
def roadmap_sh_fetcher(query: str) -> str:
    """Fetch learning path and skill roadmap data from roadmap.sh for a specific role or technology. Best for roadmap and study plan blogs."""
    print(f"  [Tool: roadmap_sh_fetcher] Querying roadmap for: '{query}'...")
    
    # 1. Map query to correct roadmap slug
    slug = get_roadmap_slug(query)
    url = f"https://raw.githubusercontent.com/nilbuild/developer-roadmap/master/src/data/roadmaps/{slug}/{slug}.json"
    
    import ssl
    context = ssl._create_unverified_context()
    
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5.0, context=context) as response:
            if response.status == 200:
                raw_data = json.loads(response.read().decode("utf-8"))
                nodes = raw_data.get("nodes", [])
                steps = parse_nodes_to_steps(nodes)
                if steps:
                    roadmap = {
                        "title": f"Official Roadmap for {slug.replace('-', ' ').title()}",
                        "steps": steps
                    }
                    return json.dumps(roadmap, indent=2)
                else:
                    raise ValueError(f"No valid roadmap steps found in the source JSON for slug '{slug}'.")
    except Exception as e:
        error_msg = (
            f"Error: Could not retrieve roadmap for query '{query}' (slug: '{slug}'). Details: {str(e)}.\n"
            f"Please make a query with one of the following exact available roadmap.sh slugs:\n"
            f"{', '.join(ROADMAP_SLUGS)}"
        )
        print(f"  [Tool: roadmap_sh_fetcher] Error: {str(e)}")
        return json.dumps({"error": error_msg}, indent=2)

def get_roadmap_slug(query: str) -> str:
    query_clean = query.lower().strip()
    
    # Direct mappings for common synonyms and SDE roles (normalized keys)
    mappings = {
        "sde": "computer-science",
        "sdeinterviews": "datastructures-and-algorithms",
        "softwareengineer": "computer-science",
        "softwareengineering": "computer-science",
        "developer": "backend",
        "coding": "datastructures-and-algorithms",
        "programming": "datastructures-and-algorithms",
        "aiengineer": "ai-engineer",
        "artificialintelligence": "ai-engineer",
        "uxdesign": "ux-design",
        "uxdesigner": "ux-design",
        "uiux": "ux-design",
        "machinelearning": "machine-learning",
        "mlengineer": "machine-learning",
        "datascience": "machine-learning",
        "datascientist": "ai-data-scientist",
        "cybersecurity": "cyber-security",
        "cybersecurityspecialist": "cyber-security",
        "datastructures": "datastructures-and-algorithms",
        "dsa": "datastructures-and-algorithms",
        "algorithms": "datastructures-and-algorithms",
        "fullstack": "full-stack",
        "gamedev": "game-developer",
        "git": "git-github",
        "github": "git-github",
        "go": "golang",
        "shellscripting": "shell-bash",
        "bash": "shell-bash",
        "softwarearchitecture": "software-design-architecture",
        "swiftui": "swift-ui",
    }
    
    # Perform normalized lookup (ignore spaces, hyphens, and underscores)
    query_norm = query_clean.replace("-", "").replace("_", "").replace(" ", "")
    if query_norm in mappings:
        return mappings[query_norm]
        
    slugified = query_clean.replace(" ", "-").replace("/", "-")
    if slugified in ROADMAP_SLUGS:
        return slugified
        
    for s in ROADMAP_SLUGS:
        if s in slugified or slugified in s:
            return s
            
    return slugified

def parse_nodes_to_steps(nodes: list) -> list:
    steps = []
    seen = set()
    
    # 1. First Pass: Check if nodes of type "topic" exist (the main path yellow milestone boxes)
    topic_nodes = [n for n in nodes if n.get("type") == "topic"]
    
    if topic_nodes:
        # Extract labels from the main topic milestone nodes
        for node in topic_nodes:
            label = node.get("data", {}).get("label")
            if not label or not isinstance(label, str):
                continue
            label_clean = label.strip()
            # Ignore placeholder names
            if label_clean.lower() in ["topic", "untitled topic", "new topic"]:
                continue
            if label_clean not in seen:
                seen.add(label_clean)
                steps.append(label_clean)
                
    # 2. Fallback: If no topic-type nodes exist, use the generic sanitization loop
    if not steps:
        for node in nodes:
            label = node.get("data", {}).get("label")
            if not label or not isinstance(label, str):
                continue
                
            label_clean = label.strip()
            label_lower = label_clean.lower()
            
            # Skip UI elements and ads
            if label_lower.endswith("node") or label_lower in ["vertical", "horizontal"]:
                continue
            if label_lower.startswith("scrimba") or "offer" in label_lower or "discount" in label_lower or "coupon" in label_lower:
                continue
            if "pre-requisites" in label_lower or "one of these" in label_lower or "choose one" in label_lower or "or choose" in label_lower:
                continue
            if "link to" in label_lower or "check out" in label_lower or "click here" in label_lower:
                continue
            if "relevant tracks" in label_lower or "continue learning" in label_lower or "have a look" in label_lower:
                continue
            if len(label_clean) <= 2 or len(label_clean) > 100:
                continue
                
            if label_clean not in seen:
                seen.add(label_clean)
                steps.append(label_clean)
                
    structured_steps = []
    for idx, topic in enumerate(steps, 1):
        structured_steps.append({
            "step": idx,
            "topic": topic,
            "details": f"Learn the core fundamentals, practical applications, and best practices for {topic}."
        })
        
    return structured_steps
