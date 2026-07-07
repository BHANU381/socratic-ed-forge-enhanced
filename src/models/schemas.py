from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Optional, Any, Dict, Literal

# Legacy models must NOT use extra="forbid" and must NOT have blank-text validators
# to preserve 100% backward compatibility with legacy payloads and tests.
class Submodule(BaseModel):
    title: str
    content_context: str

class ToolStack(BaseModel):
    tools: List[str] = Field(default_factory=list)
    tech_stack: List[str] = Field(default_factory=list)

class Module(BaseModel):
    title: str
    module_context: str
    submodules: List[Submodule] = Field(default_factory=list)

class QualityProfile(str, Enum):
    LIGHT = "light"
    STANDARD = "standard"
    TEXTBOOK = "textbook"

# API response and telemetry models must inherit from BaseModel (not StrictBaseModel)
# to prevent Pydantic from generating "additionalProperties: False" in their JSON schemas,
# which the Gemini API rejects with a 400 INVALID_ARGUMENT error.
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
    target_words: Optional[int] = None
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
    code_example_style: Literal["none", "minimal", "practical", "progressive_production", "production_first"] = "progressive_production"
    explanation_depth: Literal["concise", "balanced", "deep"] = "balanced"
    enable_google_search: Optional[bool] = True


# Strict base model for modern/new models
class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class TelemetryData(BaseModel):
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
    per_agent_tokens: Dict[str, int] = Field(default_factory=dict)
    patch_attempts: int = 0
    patch_attempts_log: List[str] = Field(default_factory=list)
    failure_reasons: List[str] = Field(default_factory=list)
    course_structure: List[Dict[str, Any]] = Field(default_factory=list)
    submodule_telemetry: Dict[str, Dict[str, Dict[str, str]]] = Field(default_factory=dict)

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
    course_id: Optional[str] = None
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


# Modern models for Course Structure configuration
class Topic(StrictBaseModel):
    # Required fields
    topic_title: str
    concept: str

    # Optional fields (can be missing, null, or contain value)
    breakdown: Optional[str] = ""
    constraints: Optional[str] = ""
    edge_cases: Optional[str] = ""
    evaluation_path: Optional[str] = ""
    expert_heuristic: Optional[str] = ""
    expert_story: Optional[str] = None
    inference_rationale: Optional[str] = None
    inferred: Optional[bool] = None

    # Optional list fields
    action_items: List[str] = Field(default_factory=list)
    common_mistakes: List[str] = Field(default_factory=list)
    reference_guides: Optional[List[str]] = None
    topic_material_ids: List[str] = Field(default_factory=list)

    @field_validator("topic_title", "concept")
    @classmethod
    def required_text_must_not_be_blank(cls, value: str) -> str:
        if value is None or not str(value).strip():
            raise ValueError("Required text fields must not be empty.")
        return value

    @field_validator("action_items", "common_mistakes", "topic_material_ids", mode="before")
    @classmethod
    def default_none_to_list(cls, v):
        return [] if v is None else v

    @field_validator("breakdown", "constraints", "edge_cases", "evaluation_path", "expert_heuristic", mode="before")
    @classmethod
    def default_none_to_empty_str(cls, v):
        return "" if v is None else v

class ModuleStructure(StrictBaseModel):
    # Required fields
    module_title: str
    module_context: str
    topics: List[Topic]  # Required but can be empty list

    # Optional fields
    learning_outcomes: List[str] = Field(default_factory=list)
    module_constraints: List[str] = Field(default_factory=list)
    module_material_ids: List[str] = Field(default_factory=list)

    @property
    def submodules(self) -> List[Topic]:
        return self.topics

    @field_validator("module_title", "module_context")
    @classmethod
    def required_text_must_not_be_blank(cls, value: str) -> str:
        if value is None or not str(value).strip():
            raise ValueError("Required text fields must not be empty.")
        return value

    @field_validator("learning_outcomes", "module_constraints", "module_material_ids", mode="before")
    @classmethod
    def default_none_to_list(cls, v):
        return [] if v is None else v

class StudentPersona(StrictBaseModel):
    name: str
    context: str

    @field_validator("name", "context")
    @classmethod
    def required_text_must_not_be_blank(cls, value: str) -> str:
        if value is None or not str(value).strip():
            raise ValueError("Required text fields must not be empty.")
        return value

class CourseStructure(StrictBaseModel):
    # Required fields
    course_title: str
    course_context: str
    modules: List[ModuleStructure]  # Required but can be empty list

    # Optional course-level fields
    duration_weeks: Optional[int] = None
    prompt_theme: str = Field("default", pattern=r"^[a-zA-Z0-9_-]+$")
    quality_profile: QualityProfile = QualityProfile.STANDARD
    learner_level: Literal["beginner", "intermediate", "advanced"] = "beginner"
    code_example_style: Literal["none", "minimal", "practical", "progressive_production", "production_first"] = "progressive_production"
    explanation_depth: Literal["concise", "balanced", "deep"] = "balanced"
    student_personas: List[StudentPersona] = Field(default_factory=list)
    lesson_contract: Optional[LessonContract] = None
    enable_google_search: Optional[bool] = True

    # Optional grounding/material fields
    tool_stack: Optional[ToolStack] = None
    course_material_ids: List[str] = Field(default_factory=list)
    material_bank: Dict[str, str] = Field(default_factory=dict)

    @field_validator("course_title", "course_context")
    @classmethod
    def required_text_must_not_be_blank(cls, value: str) -> str:
        if value is None or not str(value).strip():
            raise ValueError("Required text fields must not be empty.")
        return value

    @field_validator("student_personas", "course_material_ids", mode="before")
    @classmethod
    def default_none_to_list(cls, v):
        return [] if v is None else v

    @field_validator("material_bank", mode="before")
    @classmethod
    def default_none_to_dict(cls, v):
        return {} if v is None else v

    @field_validator("prompt_theme", "quality_profile", "learner_level", "code_example_style", "explanation_depth", "enable_google_search", mode="before")
    @classmethod
    def default_none_to_str_defaults(cls, v, info):
        if v is None:
            defaults = {
                "prompt_theme": "default",
                "quality_profile": QualityProfile.STANDARD,
                "learner_level": "beginner",
                "code_example_style": "progressive_production",
                "explanation_depth": "balanced",
                "enable_google_search": True
            }
            return defaults.get(info.field_name)
        return v

def normalize_course_input(payload: dict) -> CourseStructure:
    if not isinstance(payload, dict):
        raise ValueError("Payload must be a dictionary")
    
    # 1. Tutor wrapper check
    if "tutor" in payload or "tutor.course_structure" in str(list(payload.keys())):
        raise ValueError("Expected current course JSON format with course_name, topic, modules, and submodules. Do not pass tutor.course_structure for this migration task.")
        
    # 2. Root-level new format check -> Support directly!
    if "course_title" in payload or "course_context" in payload:
        return CourseStructure.model_validate(payload)
        
    # 3. Required fields checking
    if "course_name" not in payload:
        raise ValueError("course_name is required")
    if "topic" not in payload:
        raise ValueError("topic is required")
    if "modules" not in payload or not isinstance(payload["modules"], list):
        raise ValueError("modules is required")
        
    modules_list = []
    for m_idx, mod in enumerate(payload["modules"]):
        if not isinstance(mod, dict):
            raise ValueError(f"modules[{m_idx}] must be a dictionary")
        if "title" not in mod:
            raise ValueError(f"modules[{m_idx}].title is required")
        if "module_context" not in mod:
            raise ValueError(f"modules[{m_idx}].module_context is required")
        if "submodules" not in mod or not isinstance(mod["submodules"], list):
            raise ValueError(f"modules[{m_idx}].submodules is required")
             
        topics_list = []
        for s_idx, sub in enumerate(mod["submodules"]):
            if not isinstance(sub, dict):
                raise ValueError(f"modules[{m_idx}].submodules[{s_idx}] must be a dictionary")
            if "title" not in sub:
                raise ValueError(f"modules[{m_idx}].submodules[{s_idx}].title is required")
            if "content_context" not in sub:
                raise ValueError(f"modules[{m_idx}].submodules[{s_idx}].content_context is required")
                 
            topics_list.append(Topic(
                topic_title=sub["title"],
                concept=sub["content_context"],
                topic_material_ids=sub.get("topic_material_ids", [])
            ))
             
        modules_list.append(ModuleStructure(
            module_title=mod["title"],
            module_context=mod["module_context"],
            topics=topics_list,
            module_material_ids=mod.get("module_material_ids", [])
        ))
        
    return CourseStructure(
        course_title=payload["course_name"],
        course_context=payload["topic"],
        duration_weeks=payload.get("duration_weeks"),
        modules=modules_list,
        prompt_theme=payload.get("prompt_theme", "default"),
        quality_profile=payload.get("quality_profile", QualityProfile.STANDARD),
        learner_level=payload.get("learner_level", "beginner"),
        code_example_style=payload.get("code_example_style", "progressive_production"),
        explanation_depth=payload.get("explanation_depth", "balanced"),
        lesson_contract=payload.get("lesson_contract"),
        tool_stack=payload.get("tool_stack"),
        course_material_ids=payload.get("course_material_ids", []),
        material_bank=payload.get("material_bank", {})
    )
