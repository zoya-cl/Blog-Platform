import os
import json
from datetime import datetime
from typing import Optional, Union, Dict, Any
from schemas import RetrievedContext

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache", "retrieval")

def load_retrieval_cache(trace_id: str) -> Optional[RetrievedContext]:
    """
    Checks if cache/retrieval/{trace_id}.json exists, loads and returns the parsed RetrievedContext,
    or None if it doesn't exist or is invalid.
    """
    cache_path = os.path.join(CACHE_DIR, f"{trace_id}.json")
    if not os.path.exists(cache_path):
        return None
    
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Extract the nested context fields
        context_data = data.get("retrieved_context", {})
        if not context_data:
            # Fallback if it was stored flat
            context_data = {
                k: v for k, v in data.items() 
                if k not in ["trace_id", "topic", "cached_at"]
            }
            
        return RetrievedContext(**context_data)
    except Exception as e:
        print(f"Warning: Failed to load retrieval cache for trace {trace_id}: {e}")
        return None

def save_retrieval_cache(trace_id: str, topic: str, retrieved_context: Union[RetrievedContext, Dict[str, Any]]) -> bool:
    """
    Serializes RetrievedContext to JSON with trace_id, topic, and cached_at fields,
    and writes to cache/retrieval/{trace_id}.json.
    """
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        cache_path = os.path.join(CACHE_DIR, f"{trace_id}.json")
        
        if isinstance(retrieved_context, RetrievedContext):
            context_dict = retrieved_context.model_dump() if hasattr(retrieved_context, "model_dump") else retrieved_context.dict()
        else:
            context_dict = retrieved_context

        cache_data = {
            "trace_id": trace_id,
            "topic": topic,
            "cached_at": datetime.utcnow().isoformat(),
            "retrieved_context": context_dict
        }
        
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Warning: Failed to save retrieval cache for trace {trace_id}: {e}")
        return False
