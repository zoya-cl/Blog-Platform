import os
from langchain_openai import ChatOpenAI
try:
    from langchain_community.chat_models import ChatOllama
except ImportError:
    try:
        from langchain_community.chat_models.ollama import ChatOllama
    except ImportError:
        try:
            from langchain_ollama import ChatOllama
        except ImportError:
            ChatOllama = None

import config

def get_llm(tier: str, temperature: float = None):
    """
    Returns the configured LangChain chat model based on the provider and requested tier.
    Tiers are: "small", "medium", "large".
    
    Default temperatures:
    - small: 0.0 (near-zero for deterministic tasks like title generation/deduplication)
    - medium: 0.3 (reasoning, categorizing, structuring)
    - large: 0.7 (writing and revisions where creativity is valued)
    """
    tier = tier.lower()
    if tier not in ["small", "medium", "large"]:
        raise ValueError(f"Invalid model tier: {tier}. Must be 'small', 'medium', or 'large'.")

    # Determine default temperature if not specified
    if temperature is None:
        if tier == "small":
            temperature = 0.0
        elif tier == "medium":
            temperature = 0.3
        else:
            temperature = 0.7

    # Dynamic routing: Small tier defaults to Ollama unless an API provider is explicitly selected
    if tier == "small":
        if config.LLM_PROVIDER in ["nim", "groq", "openrouter"]:
            provider = config.LLM_PROVIDER
        else:
            provider = "ollama"
    else:
        # For medium and large, prioritize NIM, Groq, or OpenRouter if explicitly selected
        if config.LLM_PROVIDER in ["nim", "groq", "openrouter"]:
            provider = config.LLM_PROVIDER
        else:
            # Fall back to nim -> groq -> openrouter depending on keys
            if config.NVIDIA_API_KEY:
                provider = "nim"
            elif config.GROQ_API_KEY:
                provider = "groq"
            elif config.OPENROUTER_API_KEY:
                provider = "openrouter"
            else:
                provider = "ollama"

    model_name = config.MODEL_TIERS.get(provider, {}).get(tier)
    if not model_name:
        raise ValueError(f"No model mapping found for provider '{provider}' and tier '{tier}'.")

    if provider == "nim":
        if not config.NVIDIA_API_KEY:
            raise ValueError("NVIDIA_API_KEY is not set in the environment/config.")
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            openai_api_key=config.NVIDIA_API_KEY,
            openai_api_base="https://integrate.api.nvidia.com/v1"
        )
        
    elif provider == "groq":
        if not config.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not set in the environment/config.")
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            openai_api_key=config.GROQ_API_KEY,
            openai_api_base="https://api.groq.com/openai/v1"
        )
        
    elif provider == "openrouter":
        if not config.OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY is not set in the environment/config.")
        try:
            from langchain_openrouter import ChatOpenRouter
        except ImportError:
            raise ImportError(
                "Could not import ChatOpenRouter from langchain_openrouter. "
                "Ensure langchain-openrouter is installed: pip install langchain-openrouter"
            )
        return ChatOpenRouter(
            model=model_name,
            temperature=temperature,
            api_key=config.OPENROUTER_API_KEY
        )
        
    elif provider == "ollama":
        if ChatOllama is None:
            raise ImportError(
                "Could not import ChatOllama from standard LangChain paths. "
                "Ensure langchain-community or langchain-ollama is installed."
            )
        # ChatOllama supports model and temperature parameter natively
        return ChatOllama(
            model=model_name,
            temperature=temperature,
            base_url=config.OLLAMA_BASE_URL
        )
        
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
