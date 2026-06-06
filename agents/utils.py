import json
import re

def parse_json_robustly(text: str) -> dict:
    """
    Extracts the first valid JSON object or array from a string and parses it robustly.
    Handles markdown wrappers, leading/trailing conversation text, trailing commas,
    unescaped control characters, and unescaped quotes.
    """
    text_clean = text.strip()
    
    # Try parsing directly
    try:
        return json.loads(text_clean)
    except json.JSONDecodeError:
        pass
    
    # Remove markdown code block wrappers
    if text_clean.startswith("```"):
        text_clean = re.sub(r"^```(?:json)?\n", "", text_clean)
        text_clean = re.sub(r"\n```$", "", text_clean)
        text_clean = text_clean.strip()
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
                
                # 2. Escape control characters (newlines, carriage returns, tabs) inside string values
                def fix_json_strings(text):
                    # Replace raw newlines/tabs in string values (not in escaped form)
                    # This regex processes strings character by character
                    result = []
                    in_string = False
                    i = 0
                    while i < len(text):
                        char = text[i]
                        if char == '"' and (i == 0 or text[i-1] != '\\'):
                            in_string = not in_string
                            result.append(char)
                        elif in_string and char == '\n':
                            result.append('\\n')
                        elif in_string and char == '\r':
                            result.append('\\r')
                        elif in_string and char == '\t':
                            result.append('\\t')
                        elif in_string and char == '"' and (i == 0 or text[i-1] != '\\'):
                            # Unescaped quote inside string - escape it
                            result.append('\\"')
                        else:
                            result.append(char)
                        i += 1
                    return ''.join(result)
                
                try:
                    candidate_fixed = fix_json_strings(candidate_cleaned)
                    return json.loads(candidate_fixed)
                except Exception:
                    pass
                
                # 3. Additional fix: handle improperly escaped quotes before colons/commas
                try:
                    # This catches cases where a quote appears but isn't properly escaped
                    candidate_quote_fixed = re.sub(r'(?<!\\)"(?=[,\]\}])', '\\"', candidate_cleaned)
                    candidate_quote_fixed = fix_json_strings(candidate_quote_fixed)
                    return json.loads(candidate_quote_fixed)
                except Exception:
                    pass
    
    # Final fallback - try to parse what we have with aggressive fixes
    try:
        fixed = fix_json_strings(text_clean)
        return json.loads(fixed)
    except Exception as e:
        # Re-raise with diagnostic info
        raise json.JSONDecodeError(
            f"Failed to parse JSON after multiple repair attempts. Original error: {str(e)}",
            text_clean,
            0
        )
