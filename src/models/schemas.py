from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict, Literal

class Submodule(BaseModel):
    title: str
    content_context: str

class Module(BaseModel):
    title: str
    module_context: str
    submodules: List[Submodule] = Field(default_factory=list)

class QualityProfile(str, Enum):
    LIGHT = "light"
    STANDARD = "standard"
    TEXTBOOK = "textbook"

class ValidationIssue(BaseModel):
    severity: str  # e.g., "blocker", "warning", "suggestion"
    issue_type: str
    message: str
    section: Optional[str] = None

class ValidationResult(BaseModel):
    passed: bool
    issues: List[ValidationIssue] = Field(default_factory=list)
    detected_headings: List[str] = Field(default_factory=list)

class SectionRequirement(BaseModel):
    title: str
    aliases: List[str] = Field(default_factory=list)
    min_words: Optional[int] = None
    required: bool = True
    required_level: Optional[int] = None

class HeadingRuleMainContent(BaseModel):
    canonical: str
    required_level: int
    must_be_unique_per_submodule: bool

class HeadingRules(BaseModel):
    submodule_heading_level: int
    main_content_heading: HeadingRuleMainContent
    required_child_section_level: int
    optional_child_section_level: int
    walkthrough_step_level: int

class LessonContract(BaseModel):
    lesson_contract_name: str = "standard_lesson"
    heading_rules: Optional[HeadingRules] = None
    sections: List[SectionRequirement] = Field(default_factory=list)
    optional_sections: List[SectionRequirement] = Field(default_factory=list)

class CourseInput(BaseModel):
    course_name: str
    topic: str
    duration_weeks: int
    modules: List[Module] = Field(default_factory=list)
    prompt_theme: str = Field("default", pattern=r"^[a-zA-Z0-9_-]+$")
    lesson_contract: Optional[LessonContract] = None
    quality_profile: QualityProfile = QualityProfile.STANDARD
    learner_level: Literal["beginner", "intermediate", "advanced"] = "beginner"
    code_example_style: Literal["minimal", "practical", "progressive_production", "production_first"] = "progressive_production"
    explanation_depth: Literal["concise", "balanced", "deep"] = "balanced"

class TelemetryData(BaseModel):
    """
    Standardized schema for tracking agent run status and usage.
    """
    status: str
    progress_percent: int
    current_agent: str
    total_tokens: int
    input_tokens: int
    output_tokens: int
    model_name: str
    current_module: str
    current_submodule: str
    last_error_type: str = "None"
    last_error_details: str = ""
    active_iterations: int = 0
    passed_1st_iteration: int = 0
    passed_2nd_iteration: int = 0
    passed_3rd_iteration: int = 0
    failed_max_iterations: int = 0
    run_history: List[Any] = Field(default_factory=list)
    
    # Extended fields for refactored optimized pipeline
    per_agent_tokens: Dict[str, int] = Field(default_factory=dict)
    patch_attempts: int = 0
    patch_attempts_log: List[str] = Field(default_factory=list)
    failure_reasons: List[str] = Field(default_factory=list)

    # Learner level and guards telemetry
    learner_level: str = "beginner"
    code_example_style: str = "progressive_production"
    explanation_depth: str = "balanced"
    quality_profile: str = "standard"
    lesson_contract: str = "standard_lesson"
    level_alignment_status: str = "approved"
    level_alignment_warnings: List[str] = Field(default_factory=list)
    level_alignment_blockers: List[str] = Field(default_factory=list)
    mock_content_guard_status: str = "passed"
    export_contamination_status: str = "clean"
    run_manifest_match_status: str = "matched"

class PatchResult(BaseModel):
    operation: Literal["replace_section", "no_safe_patch"]
    target_heading: str
    replacement_markdown: str
    reason: str

class EvalResult(BaseModel):
    eval_name: str
    passed: bool
    score: int
    critical_issues: List[str]
    minor_issues: List[str]
    fix_recommendations: List[str]
    failure_owner: str

class ArchivistResponse(BaseModel):
    module_id: str
    submodule_id: str
    title: str
    covered_concepts: List[str] = Field(default_factory=list)
    introduced_terms: List[str] = Field(default_factory=list)
    important_examples: List[str] = Field(default_factory=list)
    dependencies_for_future_lessons: List[str] = Field(default_factory=list)
    summary: str

class RunManifest(BaseModel):
    session_id: Optional[str] = None
    course_id: Optional[str] = None  # Backwards compatibility
    course_name: Optional[str] = None
    topic: str
    duration_weeks: Optional[int] = None
    module_count: Optional[int] = None
    submodule_count: Optional[int] = None
    prompt_theme: str = "default"
    pipeline_mode: str = "optimized"
    learner_level: str = "beginner"
    code_example_style: str = "progressive_production"
    explanation_depth: str = "balanced"
    quality_profile: str = "standard"
    lesson_contract: Any = "standard_lesson"
    input_config_hash: Optional[str] = None
    started_at: Optional[str] = None
    run_type: str = "production_run"
    total_tokens: Optional[int] = 0
    per_agent_tokens: Optional[Dict[str, int]] = None
    completed_submodules: List[str] = Field(default_factory=list)
