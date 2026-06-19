from pydantic import BaseModel, Field
from typing import List, Optional, Any

class Submodule(BaseModel):
    title: str
    content_context: str

class Module(BaseModel):
    title: str
    module_context: str
    submodules: List[Submodule] = Field(default_factory=list)

class CourseInput(BaseModel):
    course_name: str
    topic: str
    duration_weeks: int
    modules: List[Module] = Field(default_factory=list)
    prompt_theme: str = Field("default", pattern=r"^[a-zA-Z0-9_-]+$")

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

class EvalResult(BaseModel):
    eval_name: str
    passed: bool
    score: int
    critical_issues: List[str]
    minor_issues: List[str]
    fix_recommendations: List[str]
    failure_owner: str
