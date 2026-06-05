import json
import urllib.request
import urllib.parse
import config


def get_mock_paa_questions(query: str) -> list:
    """generates standard questions if serpapi is disabled or fails"""
    cleaned_query = query.strip().rstrip("?").replace("2026", "").replace("2025", "").strip()
    
    return [
        f"What is the core concept of {cleaned_query}?",
        f"How do I prepare for {cleaned_query} interview questions?",
        f"What are the most common coding challenges related to {cleaned_query}?",
        f"Why do tech companies ask about {cleaned_query} in SDE rounds?",
        f"What are the key design principles of {cleaned_query}?",
        f"What is the difference between {cleaned_query} and standard alternatives?"
    ]


def fetch_paa_questions(primary_query_string: str, timeout: float = 8.0) -> list:
    """tries to get people also ask questions using serpapi, otherwise uses mock fallback"""
    # check for serpapi key in our config module
    serpapi_key = getattr(config, "SERPAPI_API_KEY", "")
    
    if not serpapi_key:
        print("Warning: SERPAPI_API_KEY is not configured in .env. Falling back to mock PAA questions.")
        return get_mock_paa_questions(primary_query_string)
        
    encoded_query = urllib.parse.quote_plus(primary_query_string)
    serpapi_url = f"https://serpapi.com/search.json?q={encoded_query}&api_key={serpapi_key}"
    print(f"  [PAA] Sending request to SerpAPI for primary query: '{primary_query_string}'...")
    
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    
    request_object = urllib.request.Request(serpapi_url, headers=headers)
    try:
        with urllib.request.urlopen(request_object, timeout=timeout) as response:
            if response.status == 200:
                raw_response_bytes = response.read()
                raw_response_text = raw_response_bytes.decode("utf-8", errors="ignore")
                search_results_data = json.loads(raw_response_text)
                
                # serpapi structure stores people also ask questions inside 'related_questions'
                related_questions_list = search_results_data.get("related_questions", [])
                extracted_paa_questions = []
                
                for question_item in related_questions_list:
                    if isinstance(question_item, dict) and "question" in question_item:
                        question_text = str(question_item["question"]).strip()
                        extracted_paa_questions.append(question_text)
                        
                if extracted_paa_questions:
                    print(f"Successfully fetched {len(extracted_paa_questions)} PAA questions from SerpAPI.")
                    return extracted_paa_questions
                else:
                    print("Warning: SerpAPI returned no 'related_questions'. Falling back to mock PAA questions.")
            else:
                print(f"Warning: SerpAPI returned HTTP status {response.status}. Falling back to mock PAA questions.")
                
    except Exception as api_error:
        print(f"Warning: Failed to fetch PAA from SerpAPI: {api_error}. Falling back to mock PAA questions.")
        
    return get_mock_paa_questions(primary_query_string)

