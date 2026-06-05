import re
from typing import TypedDict, List, Dict, Optional, Any
from pydantic import BaseModel, Field, field_validator

# -------------------------------------------------------------
# Pydantic v2 Sub-Models
# -------------------------------------------------------------

class SEOContext(BaseModel):
    primary_keyword: str = Field(..., description="Single phrase, max 6 words, no commas")
    secondary_keywords: List[str] = Field(default_factory=list)
    faq_candidates: List[str] = Field(default_factory=list)
    intent_signals: Dict[str, Any] = Field(
        default_factory=lambda: {
            "beginner": False,
            "placement_oriented": False,
            "technology_specific": [],
            "comparison": False,
            "freshness": False
        }
    )
    normalized_query: str
    expanded_queries: List[str] = Field(default_factory=list)

    @field_validator("primary_keyword")
    @classmethod
    def validate_primary_keyword(cls, v: str) -> str:
        v = v.strip()
        if "," in v:
            raise ValueError("primary_keyword must not contain commas")
        word_count = len(v.split())
        if word_count > 6:
            raise ValueError(f"primary_keyword must be max 6 words, got {word_count} words ('{v}')")
        return v


class RetrievedContext(BaseModel):
    verified_facts: List[Dict[str, str]] = Field(
        default_factory=list,
        description="List of dicts, each with keys: 'claim', 'source_url', 'retrieved_at'"
    )
    salary_ranges: Optional[Dict[str, str]] = Field(None, description="Mapping of roles to salary ranges")
    skill_requirements: List[str] = Field(default_factory=list)
    tech_stacks: List[str] = Field(default_factory=list)
    student_experiences: List[str] = Field(default_factory=list, description="Anonymized student quotes")
    sources: List[str] = Field(default_factory=list, description="All source URLs")
    leetcode_data: Optional[List[Dict[str, Any]]] = Field(default=None, description="Raw JSON data of problems from LeetCode")
    roadmap_data: Optional[Dict[str, Any]] = Field(default=None, description="Raw JSON data of roadmap steps")


class SectionBrief(BaseModel):
    section_index: int
    title: str = Field(..., description="The H2 heading")
    section_type: str = Field(default="conceptual", description="Type of the section (e.g. 'intro', 'conceptual', 'tutorial', 'comparison', 'roadmap', 'faq', 'summary', 'cta')")
    target_word_count: int
    key_points: List[str] = Field(default_factory=list)
    assigned_facts: List[str] = Field(default_factory=list, description="Fact reference IDs like ['fact_1', 'fact_2'] pointing to the 1-based index of facts in verified_facts")
    assigned_keywords: List[str] = Field(default_factory=list)
    include_table: bool = False
    include_code_block: bool = False
    component_directives: List[str] = Field(default_factory=list, description="List of component directives (e.g. 'table', 'code_block', 'comparison_widget', 'quiz', 'roadmap')")
    maps_to_paa: Optional[str] = Field(None, description="The PAA question this section answers")
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
    seo_warnings: List[str] = Field(default_factory=list)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        # validate no spaces or special characters, lowercase and hyphens/underscores only
        v = v.strip().lower()
        if not re.match(r"^[a-z0-9_-]+$", v):
            raise ValueError(f"slug '{v}' must not contain spaces or special characters")
        return v

    @field_validator("meta_description")
    @classmethod
    def validate_meta_description(cls, v: str) -> str:
        if len(v) > 160:
            raise ValueError(f"meta_description must be max 160 characters, got {len(v)}")
        return v

    @field_validator("focus_keyword")
    @classmethod
    def validate_focus_keyword(cls, v: str) -> str:
        v = v.strip()
        if "," in v:
            raise ValueError("focus_keyword must not contain commas")
        word_count = len(v.split())
        if word_count > 6:
            raise ValueError(f"focus_keyword must be max 6 words, got {word_count} words ('{v}')")
        return v


# -------------------------------------------------------------
# LangGraph TypedDict State
# -------------------------------------------------------------

class BlogState(TypedDict):
    # Meta / Identifiers
    trace_id: str
    topic: str
    category: str

    # Directives
    retrieval_required: bool
    retrieval_depth: str          # "none", "shallow", "deep"
    generation_mode: str          # "standard", "map-reduce"
    audience_level: str           # "fresher", "intermediate"
    word_count_target: int
    section_count_target: int
    writer_template: str
    hallucination_checklist: str

    # Contexts
    seo_context: Dict[str, Any]       # Serialized SEOContext
    retrieved_context: Dict[str, Any] # Serialized RetrievedContext

    # Plan
    outline: Dict[str, Any]           # Planner output structure
    section_briefs: List[Dict[str, Any]] # List of serialized SectionBriefs

    # Writing State
    section_drafts: List[str]
    running_context: str
    assembled_draft: str

    # Review & Revisions
    hallucination_report: Dict[str, Any]
    hallucination_revision_count: int
    quality_scores: Dict[str, Any]
    quality_revision_count: int
    seo_audit_results: Dict[str, Any]
    seo_revision_count: int
    seo_warnings: List[str]

    # Image Generation State
    image_plan: List[Dict[str, Any]]
    generated_images: List[Dict[str, Any]]

    # Outputs
    final_blog: str
    metadata: Dict[str, Any]          # Serialized BlogMetadata
    prompt_version: int









