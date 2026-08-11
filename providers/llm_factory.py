import os
from langchain_openai import ChatOpenAI
import config

def get_llm(tier: str = "medium", temperature: float = None) -> ChatOpenAI:
    """
    Returns the configured OpenRouter ChatOpenAI model based on requested tier.
    Tiers: 'small', 'medium', 'large'.
    """
    tier = tier.lower()
    if tier not in ["small", "medium", "large"]:
        raise ValueError(f"Invalid model tier: {tier}. Must be 'small', 'medium', or 'large'.")

    defaults = {
        "small": 0.0,
        "medium": 0.3,
        "large": 0.7
    }

    if temperature is None:
        temperature = defaults[tier]

    if not config.OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is not set in environment/config.")

    model_name = config.MODEL_TIERS["openrouter"].get(tier)
    if not model_name:
        raise ValueError(f"No OpenRouter model mapping found for tier '{tier}'.")

    return ChatOpenAI(
        model=model_name,
        temperature=temperature,
        openai_api_key=config.OPENROUTER_API_KEY,
        openai_api_base="https://openrouter.ai/api/v1",
        request_timeout=120.0,
        max_retries=3
    )

