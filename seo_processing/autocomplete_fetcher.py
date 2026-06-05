import json
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed


def fetch_suggestions_for_query(query: str, timeout: float = 5.0) -> list:
    """queries google suggest api to get search recommendations for a single query"""
    print(f"  [Autocomplete] Querying Google suggest API for: '{query}'...")
    
    # we url-encode the query to make it safe for a web request (like changing spaces to pluses)
    encoded_query = urllib.parse.quote_plus(query)
    url = f"https://suggestqueries.google.com/complete/search?client=chrome&q={encoded_query}"
    
    # standard headers to mimic a normal browser request so google doesn't block us
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    
    request_object = urllib.request.Request(url, headers=headers)
    try:
        # run the network call using python's built-in urllib tool
        with urllib.request.urlopen(request_object, timeout=timeout) as response:
            if response.status == 200:
                raw_response_bytes = response.read()
                raw_response_text = raw_response_bytes.decode("utf-8", errors="ignore")
                
                # google suggest api returns a json list where index 1 holds the list of suggestions
                parsed_json = json.loads(raw_response_text)
                if isinstance(parsed_json, list) and len(parsed_json) > 1:
                    suggestions_list = parsed_json[1]
                    if isinstance(suggestions_list, list):
                        cleaned_suggestions = []
                        # we limit to at most 8 suggestions per query to avoid bloating downstream context
                        for suggestion in suggestions_list[:8]:
                            cleaned_suggestions.append(str(suggestion).strip())
                            
                        print(f"  [Autocomplete] Found {len(cleaned_suggestions)} suggestions for: '{query}'")
                        return cleaned_suggestions
                        
    except Exception as network_error:
        print(f"Warning: Failed to fetch autocomplete suggestions for query '{query}': {network_error}")
        
    return []


def _fetch_batch_concurrently(queries: list, max_workers: int) -> dict:
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as thread_executor:
        future_to_query = {thread_executor.submit(fetch_suggestions_for_query, q): q for q in queries}
        for future in as_completed(future_to_query):
            q = future_to_query[future]
            try:
                results[q] = future.result()
            except Exception as e:
                print(f"Error fetching suggestions for '{q}': {e}")
                results[q] = []
    return results


def fetch_autocomplete_suggestions(expanded_queries_dict: dict, max_workers: int = 5) -> dict:
    """fetches suggestions for all categorized queries concurrently using threadpool, with pruning"""
    # divide queries into two batches to allow pruning if the success rate is too low
    batch_1 = []
    batch_2 = []
    
    for bucket_name, queries_list in expanded_queries_dict.items():
        if isinstance(queries_list, list) and queries_list:
            batch_1.append(queries_list[0])
            if len(queries_list) > 1:
                batch_2.extend(queries_list[1:])
                
    suggestions_by_query = {}
    
    # fetch batch 1
    if batch_1:
        batch_1_results = _fetch_batch_concurrently(batch_1, max_workers)
        suggestions_by_query.update(batch_1_results)
        
        # calculate success rate (queries that returned at least 1 suggestion)
        successful_queries = sum(1 for q in batch_1 if len(batch_1_results.get(q, [])) > 0)
        success_rate = successful_queries / len(batch_1)
        
        # if success rate is below 40%, we prune batch 2 to save latency and API calls
        if success_rate < 0.4:
            print(f"  [Autocomplete] Success rate {success_rate:.2f} is below 40% threshold. Pruning remaining expansions.")
        else:
            if batch_2:
                batch_2_results = _fetch_batch_concurrently(batch_2, max_workers)
                suggestions_by_query.update(batch_2_results)
                
    categorized_suggestions_result = {
        "beginner_intent": [],
        "placement_intent": [],
        "comparison_intent": [],
        "freshness_intent": [],
        "technology_intent": []
    }
    
    # keep track of lowercase versions of suggestions to prevent duplicates across all queries
    globally_seen_suggestions = set()
    
    for bucket_name in categorized_suggestions_result.keys():
        queries_in_this_bucket = expanded_queries_dict.get(bucket_name, [])
        
        for query_string in queries_in_this_bucket:
            if len(categorized_suggestions_result[bucket_name]) >= 8:
                break
            raw_suggestions = suggestions_by_query.get(query_string, [])
            
            for suggestion in raw_suggestions:
                if len(categorized_suggestions_result[bucket_name]) >= 8:
                    break
                suggestion_lower = suggestion.lower().strip()
                if suggestion_lower not in globally_seen_suggestions and suggestion_lower:
                    globally_seen_suggestions.add(suggestion_lower)
                    categorized_suggestions_result[bucket_name].append(suggestion)
                    
    return categorized_suggestions_result

