import re
from typing import TypedDict, List, Dict, Optional, Any
from pydantic import BaseModel, Field, field_validator

class SEOContext(BaseModel):
    primary_keyword: str = Field(..., description="Single phrase, max 6 words, no commas")
    secondary_keywords: List[str] = Field(default_factory=list)
    faq_candidates: List[str] = Field(default_factory=list)
    intent_signals: Dict[str, Any] = Field(default_factory=dict)
    normalized_query: str = ""
    expanded_queries: List[str] = Field(default_factory=list)

    @field_validator("primary_keyword")
    @classmethod
    def validate_primary_keyword(cls, v: str) -> str:
        v = v.strip()
        if "," in v:
            v = v.split(",")[0].strip()
        words = v.split()
        if len(words) > 6:
            v = " ".join(words[:6])
        return v


class RetrievedContext(BaseModel):
    verified_facts: List[Dict[str, str]] = Field(
        default_factory=list,
        description="List of dicts, each with keys: 'claim', 'source_url', 'retrieved_at'"
    )
    skill_requirements: List[str] = Field(default_factory=list)
    tech_stacks: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list, description="All source URLs")


class SectionBrief(BaseModel):
    section_index: int
    title: str = Field(..., description="The H2 heading")
    section_type: str = Field(default="conceptual")
    target_word_count: int
    key_points: List[str] = Field(default_factory=list)
    assigned_facts: List[str] = Field(default_factory=list)
    assigned_keywords: List[str] = Field(default_factory=list)
    include_table: bool = False
    include_code_block: bool = False
    component_directives: List[str] = Field(default_factory=list)
    component_focus: Optional[str] = Field(None, description="Unique focus area for this section's component — must not overlap with other sections")
    maps_to_paa: Optional[str] = Field(None)
    is_final_section: bool = False


class BlogMetadata(BaseModel):
    title: str
    slug: str
    date: str
    category: str
    tags: List[str] = Field(default_factory=list)
    meta_description: str
    focus_keyword: str
    secondary_keywords: List[str] = Field(default_factory=list)
    word_count: int = 0
    quality_score: float = 0.0
    revision_count: int = 0
    prompt_version: int = 1
    blog_format: str = "deep_dive"
    seo_warnings: List[str] = Field(default_factory=list)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[a-z0-9_-]+$", v):
            raise ValueError(f"slug '{v}' must not contain spaces or special characters")
        return v

    @field_validator("meta_description")
    @classmethod
    def validate_meta_description(cls, v: str) -> str:
        if len(v) > 160:
            return v[:157] + "..."
        return v


class BlogState(TypedDict):
    trace_id: str
    topic: str
    category: str

    audience_level: str
    word_count_target: int
    section_count_target: int
    blog_format: str

    seo_context: Dict[str, Any]
    retrieved_context: Dict[str, Any]

    outline: Dict[str, Any]
    section_briefs: List[Dict[str, Any]]

    section_drafts: List[str]
    assembled_draft: str

    quality_scores: Dict[str, Any]
    quality_revision_count: int

    final_blog: str
    metadata: Dict[str, Any]
    prompt_version: int
    generated_images: List[Dict[str, Any]]
