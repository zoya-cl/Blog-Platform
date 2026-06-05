import json
import re

def parse_json_robustly(text: str) -> dict:
    """
    Extracts the first valid JSON object or array from a string and parses it robustly.
    Handles markdown wrappers, leading/trailing conversation text, trailing commas,
    and unescaped control characters.
    """
    text_clean = text.strip()
    
    # Try parsing directly
    try:
        return json.loads(text_clean)
    except json.JSONDecodeError:
        pass
        
    # Attempt to locate the first '{' or '[' and last '}' or ']'
    first_brace = text_clean.find('{')
    first_bracket = text_clean.find('[')
    
    # Determine the starting position and expected end character
    start_idx = -1
    end_char = ''
    
    if first_brace != -1 and (first_bracket == -1 or first_brace < first_bracket):
        start_idx = first_brace
        end_char = '}'
    elif first_bracket != -1:
        start_idx = first_bracket
        end_char = ']'
        
    if start_idx != -1:
        end_idx = text_clean.rfind(end_char)
        if end_idx != -1 and end_idx > start_idx:
            candidate = text_clean[start_idx:end_idx + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                # 1. Clean trailing commas inside objects/arrays
                candidate_cleaned = re.sub(r',\s*([\]}])', r'\1', candidate)
                try:
                    return json.loads(candidate_cleaned)
                except json.JSONDecodeError:
                    pass
                
                # 2. Clean raw control characters/newlines inside string literals
                try:
                    # Basic regex helper to replace raw newlines within double-quoted JSON strings
                    # We match a double quote, then any non-quote character (allowing escaped quotes), then double quote
                    # and replace unescaped newlines in the matched content.
                    def escape_newlines(match):
                        s = match.group(0)
                        # escape actual newlines and carriage returns
                        return s.replace('\n', '\\n').replace('\r', '\\r')
                    
                    candidate_escaped = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', escape_newlines, candidate_cleaned)
                    return json.loads(candidate_escaped)
                except Exception:
                    pass

    # Fallback to standard cleaning and parsing if extraction failed
    if text_clean.startswith("```"):
        text_clean = re.sub(r"^```(?:json)?\n", "", text_clean)
        text_clean = re.sub(r"\n```$", "", text_clean)
        text_clean = text_clean.strip()
    return json.loads(text_clean)
