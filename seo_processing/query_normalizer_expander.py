from typing import List
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from providers.llm_factory import get_llm


# this normalizer is specifically tailored to tech blogs because we want to structure queries
# around software developer career paths (interviews, code syntax, technical differences) rather
# than generic consumer topics. this keeps our seo research highly relevant to technical readers.
class ExpandedQueries(BaseModel):
    beginner_intent: List[str] = Field(description="1-2 queries targeting beginners, basics, or introductory concepts")
    placement_intent: List[str] = Field(description="1-2 queries targeting tech interview preparation or job recruitment rounds")
    comparison_intent: List[str] = Field(description="1-2 queries comparing options (e.g., vs, differences, pros/cons)")
    freshness_intent: List[str] = Field(description="1-2 queries targeting recent trends, roadmaps, or year-specific details")
    technology_intent: List[str] = Field(description="1-2 queries targeting framework features, syntax, or technical code setup")


class QueryExpansionOutput(BaseModel):
    primary_query: str = Field(description="single normalized core search query in natural human phrasing")
    expanded_queries: ExpandedQueries


def normalize_and_expand_query(blog_title: str, category: str = "") -> dict:
    """uses a small llm with structured output to normalize a blog title and expand search queries"""
    system_instructions = (
        "You are a tech blog search intent analyst. Your task is to normalize a blog title into a single search query "
        "and generate relevant keyword expansions categorized by intent (beginner, placement, comparison, freshness, technology).\n\n"
        "CRITICAL INSTRUCTIONS:\n"
        "- Expansions must be hyper-specific to the actual core topic. Do NOT use generic query templates like 'latest developments in {{topic}}' or 'new developments in {{topic}}' if they drift from the query context.\n"
        "- Expansions must represent real terms that developers actually search on Google to find articles or tutorials.\n"
        "- Ensure the queries stay closely aligned with the category if provided."
    )

    user_prompt = "Blog Title: {title}"
    if category:
        user_prompt += "\nCategory Context: {category}"

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_instructions),
        ("user", user_prompt)
    ])

    # we use langchain's structured output tool to guarantee the response matches our pydantic schema.
    # this saves us from writing complex parsing, regex, or code block stripping logic.
    small_llm = get_llm(tier="small", temperature=0.0)
    structured_llm = small_llm.with_structured_output(QueryExpansionOutput)
    execution_chain = prompt_template | structured_llm
    
    fallback_query = blog_title.replace("?", "").replace(":", "").strip()
    fallback_structure = {
        "primary_query": fallback_query,
        "expanded_queries": {
            "beginner_intent": [fallback_query + " basics"],
            "placement_intent": [fallback_query + " interview questions"],
            "comparison_intent": [fallback_query + " vs alternatives"],
            "freshness_intent": [fallback_query + " 2026"],
            "technology_intent": [fallback_query + " tutorial"]
        }
    }

    try:
        inputs = {"title": blog_title}
        if category:
            inputs["category"] = category
        result = execution_chain.invoke(inputs)
        return result.model_dump()
    except Exception as parse_error:
        print(f"Warning: Failed to retrieve structured output from query normalizer. Error: {parse_error}")

    return fallback_structure

