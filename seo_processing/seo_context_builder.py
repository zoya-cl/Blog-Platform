from schemas import SEOContext


def trim_primary_keyword(keyword_string: str) -> str:
    """removes commas and chops the keyword to maximum 6 words to satisfy schema limits"""
    cleaned_string = keyword_string.replace(",", "").strip()
    words_list = cleaned_string.split()
    
    if len(words_list) > 6:
        return " ".join(words_list[:6])
        
    return cleaned_string


def build_seo_context(
    curated_seo_data: dict,
    normalized_query: str,
    expanded_queries_dict: dict
) -> SEOContext:
    """packs and cleans all seo data into a pydantic seocontext object for downstream stages"""
    # extract and clean focus keyword, replacing underscores with spaces
    raw_primary = curated_seo_data.get("primary_keyword", normalized_query)
    raw_primary = raw_primary.replace("_", " ")
    primary_keyword_sanitized = trim_primary_keyword(raw_primary)
    
    if not primary_keyword_sanitized:
        primary_keyword_sanitized = "software engineering placement prep"
        
    # extract secondary keywords, capping at max 5 and replacing underscores with spaces
    raw_secondary_list = curated_seo_data.get("secondary_keywords", [])
    secondary_keywords_sanitized = []
    
    for keyword in raw_secondary_list:
        keyword_clean = keyword.replace("_", " ").replace(",", "").strip()
        if keyword_clean:
            secondary_keywords_sanitized.append(keyword_clean)
            if len(secondary_keywords_sanitized) == 5:
                break
                
    # extract faq candidates, capping at max 6
    raw_faq_list = curated_seo_data.get("faq_candidates", [])
    faq_candidates_sanitized = []
    
    for faq_question in raw_faq_list:
        faq_clean = faq_question.strip()
        if faq_clean:
            faq_candidates_sanitized.append(faq_clean)
            if len(faq_candidates_sanitized) == 6:
                break
                
    # extract intent signals and clean tech keywords
    raw_intent_signals = curated_seo_data.get("intent_signals", {})
    
    tech_keywords = raw_intent_signals.get("technology_specific", [])
    tech_keywords_sanitized = []
    for tech in tech_keywords:
        tech_clean = trim_primary_keyword(tech.replace("_", " "))
        if tech_clean:
            tech_keywords_sanitized.append(tech_clean)
            if len(tech_keywords_sanitized) == 5:
                break
                
    intent_signals = {
        "beginner": bool(raw_intent_signals.get("beginner", False)),
        "placement_oriented": bool(raw_intent_signals.get("placement_oriented", False)),
        "technology_specific": tech_keywords_sanitized,
        "comparison": bool(raw_intent_signals.get("comparison", False)),
        "freshness": bool(raw_intent_signals.get("freshness", False))
    }
    
    # flatten the grouped expanded queries dictionary for schema compatibility
    flat_expanded_queries = []
    for bucket_name, queries_list in expanded_queries_dict.items():
        if isinstance(queries_list, list):
            for query_string in queries_list:
                flat_expanded_queries.append(query_string)
                
    # instantiate the pydantic model to trigger validation checks
    seo_context_object = SEOContext(
        primary_keyword=primary_keyword_sanitized,
        secondary_keywords=secondary_keywords_sanitized,
        faq_candidates=faq_candidates_sanitized,
        intent_signals=intent_signals,
        normalized_query=normalized_query,
        expanded_queries=flat_expanded_queries
    )
    
    return seo_context_object
