import os
import time
import datetime
import traceback
import json
import re
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

from dotenv import load_dotenv
from pydantic import ValidationError

from src.agents.core import ContentGenerator, SemanticEvaluator, PatchEditor, Archivist, GroundingFaithfulnessAuditor, AnalogyAgent, AnalogyEvaluator
from src.utils.logger import log_event, update_status, update_telemetry
from src.utils.learning_engine import record_lesson
from src.utils.string_utils import normalize_module_heading, normalize_submodule_heading, normalize_step_headings
from src.utils.cleanup_utils import final_markdown_cleanup
from src.utils.search_client import search_duckduckgo
from src.models.schemas import CourseStructure, ModuleStructure, Topic, TelemetryData, RunManifest, LessonContract, SectionRequirement, QualityProfile, normalize_course_input

# Load environment variables
load_dotenv(override=True)

# Define Project Root relative to this file's location
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STOP_FLAG = PROJECT_ROOT / "data" / "stop.flag"

def _check_stop(telemetry: Dict[str, Any], session_dir: Path) -> None:
    """Raise SystemExit if data/stop.flag exists. Stops token spend immediately."""
    if STOP_FLAG.exists():
        log_event("System", "Stop flag detected. Shutting down cleanly.", session_dir=str(session_dir))
        update_status("Stopped by user.", session_dir=str(session_dir))
        telemetry["status"] = "Stopped"
        telemetry["current_agent"] = "None"
        update_telemetry(telemetry, session_dir=str(session_dir))
        raise SystemExit(0)

def truncate_running_summary(summary: str) -> str:
    """Keep only the last 15 bullet points of the running summary to avoid prompt bloat."""
    lines = summary.splitlines()
    bullet_lines = [l for l in lines if l.strip().startswith("-")]
    if len(bullet_lines) > 15:
        target_bullets = bullet_lines[-15:]
        return "\n".join(target_bullets)
    return summary

def normalize_headings_dynamically(draft: str, required_headings: List[str]) -> str:
    if required_headings:
        for req in required_headings:
            match = re.match(r'^(#+)\s+(.+)$', req.strip())
            if match:
                expected_prefix = match.group(1)
                title = match.group(2).strip()
                if title.lower() == "hook":
                    draft = re.sub(r'^#+\s*Hook\s*:\s*(.*)$', f'{expected_prefix} Hook: \\1', draft, flags=re.MULTILINE | re.IGNORECASE)
                    draft = re.sub(r'^#+\s*Hook\s*$', f'{expected_prefix} Hook', draft, flags=re.MULTILINE | re.IGNORECASE)
                else:
                    draft = re.sub(r'^#+\s*' + re.escape(title) + r'\s*$', f'{expected_prefix} {title}', draft, flags=re.MULTILINE | re.IGNORECASE)
    return draft


def normalize_draft(draft: str, sub_title: str, required_headings: List[str]) -> str:
    # Normalize line endings and split
    lines = draft.replace('\r\n', '\n').split('\n')
    cleaned_lines = []
    
    clean_title = re.sub(r'^[\d\.]+\s+', '', sub_title).strip().lower()
    
    for line in lines:
        stripped = line.strip()
        
        # Skip empty lines at the very beginning
        if not cleaned_lines and not stripped:
            continue
            
        # Skip module/submodule headings
        if stripped.lower().startswith('# module') or stripped.lower().startswith('## submodule'):
            continue
            
        # Skip any headers containing the submodule title unless required
        if (stripped.startswith('#') or stripped.startswith('##') or stripped.startswith('###')) and clean_title in stripped.lower():
            clean_reqs = [req.replace("### ", "").strip().lower() for req in required_headings]
            if not any(header in stripped.lower() for header in clean_reqs):
                continue
                
        cleaned_lines.append(line)
        
    normalized = '\n'.join(cleaned_lines).strip()
    
    # Remove duplicate adjacent lines if they are headings
    lines = normalized.split('\n')
    deduped_lines = []
    for line in lines:
        if deduped_lines and line.strip().startswith('###') and line.strip() == deduped_lines[-1].strip():
            continue
        deduped_lines.append(line)
        
    normalized = '\n'.join(deduped_lines).strip()
    normalized = re.sub(r'\n{3,}', '\n\n', normalized)
    return normalized

def validate_draft(draft: str, required_headings: List[str]) -> List[str]:
    errors = []
    
    if required_headings and required_headings[0] in draft:
        prefix = draft[:draft.index(required_headings[0])]
        prefix_lines = [line.strip() for line in prefix.split('\n')]
        has_headings_in_prefix = any(line.startswith('#') for line in prefix_lines)
        if not has_headings_in_prefix:
            draft = draft[draft.index(required_headings[0]):]
        
    lines = [line.strip() for line in draft.split('\n')]
    
    for idx, line in enumerate(lines):
        if line.startswith('# ') or line.startswith('## '):
            errors.append(f"Line {idx+1}: Found illegal header level '{line}'. Only level 3 (###) and lower headers are allowed.")
            
    headings = [line for line in lines if line.startswith('### ')]
    
    for req in required_headings:
        if req not in headings:
            errors.append(f"Missing required major heading: '{req}'")
            
    for req in required_headings:
        if headings.count(req) > 1:
            errors.append(f"Duplicate required heading: '{req}' appears multiple times.")
            
    non_empty_lines = [l for l in lines if l]
    if non_empty_lines and required_headings and not non_empty_lines[0].startswith(required_headings[0]):
        errors.append(f"First line of draft must be exactly '{required_headings[0]}'.")
        
    indices = []
    for req in required_headings:
        try:
            indices.append(headings.index(req))
        except ValueError:
            pass
            
    if len(indices) == len(required_headings):
        if indices != sorted(indices):
            req_str = ", ".join([r.replace("### ", "") for r in required_headings])
            errors.append(f"Required headings are in the wrong order. Must be: {req_str}.")
            
    return errors

def sanitize_headings(draft: str, sub_title: str, required_headings: List[str]) -> str:
    if required_headings:
        first_heading = required_headings[0]
        if first_heading in draft:
            draft = draft[draft.index(first_heading):]
            
    return normalize_draft(draft, sub_title, required_headings)


def update_live_preview(session_dir: Optional[Path], master_file: Path, sub_title: Optional[str] = None, draft: Optional[str] = None, status: Optional[str] = None) -> None:
    if not session_dir:
        return
    live_preview_file = session_dir / "live_preview.md"
    try:
        content = ""
        if master_file and master_file.exists():
            content = master_file.read_text(encoding="utf-8")
        
        if draft and sub_title:
            status_suffix = f" [{status}]" if status else " [Drafting]"
            content = content.rstrip()
            draft_clean = draft.strip()
            content += f"\n\n## Submodule: {sub_title}{status_suffix}\n\n{draft_clean}\n"
            
        live_preview_file.write_text(content, encoding="utf-8")
    except Exception as e:
        print(f"Error updating live preview: {e}")

class Orchestrator:
    def __init__(self, course: Any, session_dir: Path, run_type: str = "new_run"):
        if course.__class__.__name__ == "CourseStructure":
            self.course = course
        elif isinstance(course, dict):
            self.course = normalize_course_input(course)
        else:
            try:
                if hasattr(course, "model_dump"):
                    self.course = normalize_course_input(course.model_dump())
                elif hasattr(course, "dict"):
                    self.course = normalize_course_input(course.dict())
                else:
                    self.course = course
            except Exception:
                self.course = course

        self.session_dir = session_dir
        self.run_type = run_type
        
        # File path setups
        safe_course_name = "".join([c if c.isalnum() else "_" for c in self.course.course_title])
        self.master_file = self.session_dir / f"{safe_course_name}.md"
        
        # Initialize modern agents
        self.generator = ContentGenerator("Content Generator", theme=self.course.prompt_theme)
        self.semantic_evaluator = SemanticEvaluator("Semantic Evaluator", theme=self.course.prompt_theme)
        self.grounding_auditor = GroundingFaithfulnessAuditor("Grounding Faithfulness Auditor", theme=self.course.prompt_theme)
        self.patch_editor = PatchEditor("Patch Editor", theme=self.course.prompt_theme)
        self.archivist = Archivist("Archivist", theme=self.course.prompt_theme)
        self.analogy_generator = AnalogyAgent("Analogy Generator", theme=self.course.prompt_theme)
        self.analogy_evaluator = AnalogyEvaluator("Analogy Evaluator", theme=self.course.prompt_theme)
        
        # Define lesson contract and quality profile with dynamic defaults
        self.quality_profile = self.course.quality_profile or QualityProfile.STANDARD
        
        contract_path = Path("src/prompts") / self.course.prompt_theme / "contract.json"
        
        if self.course.lesson_contract:
            self.lesson_contract = self.course.lesson_contract
        else:
            if not contract_path.exists():
                raise FileNotFoundError(f"contract.json not found in theme '{self.course.prompt_theme}'.")
            
            with open(contract_path, "r", encoding="utf-8") as f:
                contract_data = json.load(f)
                self.lesson_contract = LessonContract(**contract_data)
                
        # Calculate dynamic word limits if prompt theme is ottolearn
        self.core_idea_words = 100
        self.implementation_words = 150
        self.why_it_matters_words = 50
        if course.prompt_theme == "ottolearn":
            total_submodules = sum(len(mod.submodules) for mod in course.modules) if course.modules else 0
            if total_submodules > 0:
                # 8 hours of study time per week -> target words per submodule:
                target_words = int(((course.duration_weeks * 8) / total_submodules) * 2400)
                target_words = max(400, min(4000, target_words))
                
                # Distribute words: Hook (15 words)
                remaining = target_words - 15
                self.core_idea_words = max(100, int(remaining * 0.40))
                self.implementation_words = max(150, int(remaining * 0.45))
                self.why_it_matters_words = max(50, int(remaining * 0.15))
                
                # Dynamically update the lesson contract section requirements
                for sec in self.lesson_contract.sections:
                    if sec.title == "Hook":
                        sec.min_words = 15
                    elif sec.title == "Core Idea":
                        sec.min_words = self.core_idea_words
                    elif sec.title == "Implementation":
                        sec.min_words = self.implementation_words
                    elif sec.title == "Why it Matters":
                        sec.min_words = self.why_it_matters_words
        
        # Initialize structured telemetry
        self.telemetry = {
            "status": "Initializing",
            "current_agent": "System",
            "progress_percent": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "model_name": self.generator.model_id,
            "learner_level": getattr(self.course, "learner_level", "beginner"),
            "code_example_style": getattr(self.course, "code_example_style", "progressive_production"),
            "explanation_depth": getattr(self.course, "explanation_depth", "balanced"),
            "quality_profile": self.quality_profile.value,
            "module_position": "",
            "level_alignment_status": "none",
            "level_alignment_issues": [],
            "patch_mode": "none",
            "current_module": "",
            "current_submodule": "",
            "last_error_type": "None",
            "last_error_details": "",
            "active_iterations": 0,
            "passed_1st_iteration": 0,
            "passed_2nd_iteration": 0,
            "passed_3rd_iteration": 0,
            "failed_max_iterations": 0,
            "run_history": [],
            "per_agent_tokens": {},
            "patch_attempts": 0,
            "patch_attempts_log": [],
            "failure_reasons": [],
            "grounding_auditor_status": "passed",
            "grounding_auditor_attempts": 0,
            "grounding_auditor_blockers": [],
            "analogy_generator_attempts": 0,
            "analogy_evaluator_status": "none",
            "analogy_evaluator_blockers": [],
            "analogy_fallback_triggered": False
        }
        
        # Populate course structure
        self.telemetry["course_structure"] = [
            {
                "module_title": mod.module_title,
                "submodules": [t.topic_title for t in mod.topics]
            }
            for mod in self.course.modules
        ] if hasattr(self.course, "modules") and self.course.modules else []
        self.telemetry["submodule_telemetry"] = {}
        
        # Load from session directory telemetry.json if resuming
        if self.run_type == "resume_existing_run" and self.session_dir:
            session_tel_path = self.session_dir / "telemetry.json"
            if session_tel_path.exists():
                try:
                    with open(session_tel_path, "r", encoding="utf-8") as f:
                        session_tel = json.load(f)
                    if "course_structure" in session_tel:
                        self.telemetry["course_structure"] = session_tel["course_structure"]
                    if "submodule_telemetry" in session_tel:
                        self.telemetry["submodule_telemetry"] = session_tel["submodule_telemetry"]
                except Exception:
                    pass
            self._recalculate_telemetry_summaries()

    def _recalculate_telemetry_summaries(self):
        self.telemetry["passed_1st_iteration"] = 0
        self.telemetry["passed_2nd_iteration"] = 0
        self.telemetry["passed_3rd_iteration"] = 0
        self.telemetry["failed_max_iterations"] = 0
        
        completed = set()
        manifest_path = self.session_dir / "run_manifest.json"
        if manifest_path.exists():
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                completed = set(data.get("completed_submodules", []))
            except Exception:
                pass
                
        for mod_title, sub_data in self.telemetry.get("submodule_telemetry", {}).items():
            for sub_title, stats in sub_data.items():
                if sub_title not in completed:
                    continue
                
                is_failed = False
                for val in stats.values():
                    val_str = str(val).upper()
                    if "F" in val_str or "FAIL" in val_str:
                        is_failed = True
                        break
                        
                if is_failed:
                    self.telemetry["failed_max_iterations"] += 1
                else:
                    attempts = []
                    for val in stats.values():
                        val_str = str(val).strip()
                        if val_str.isdigit():
                            attempts.append(int(val_str))
                    max_att = max(attempts) if attempts else 1
                    if max_att == 1:
                        self.telemetry["passed_1st_iteration"] += 1
                    elif max_att == 2:
                        self.telemetry["passed_2nd_iteration"] += 1
                    elif max_att == 3:
                        self.telemetry["passed_3rd_iteration"] += 1

    def update_submodule_telemetry(self, module: str, sub: str, agent: str, val: Any):
        st = self.telemetry.setdefault("submodule_telemetry", {})
        mod_dict = st.setdefault(module, {})
        sub_dict = mod_dict.setdefault(sub, {})
        sub_dict[agent] = str(val)

    def _format_student_personas(self) -> str:
        from src.models.schemas import StudentPersona
        personas = getattr(self.course, "student_personas", []) or []
        
        # Build copy to avoid mutating the original
        active_personas = list(personas)
        
        # Generate default dynamic context
        course_context = getattr(self.course, "course_context", "") or ""
        default_context = f"A general learner seeking practical analogies related to: {course_context}."
        default_persona = StudentPersona(name="Default Student", context=default_context)
        active_personas.append(default_persona)
        
        formatted_list = []
        for p in active_personas:
            formatted_list.append(f"- Target Name: {p.name}\n  Target Context: {p.context}")
        return "\n".join(formatted_list)

    def adjust_contract_word_limits(self, num_personas: int) -> None:
        if not hasattr(self, "lesson_contract") or not self.lesson_contract:
            return
        persona_section = next(
            (sec for sec in self.lesson_contract.sections if sec.title == "Persona Analogies"),
            None
        )
        if persona_section:
            persona_section.min_words = 200 * num_personas
            persona_section.target_words = 350 * num_personas

    def load_or_create_manifest(self) -> RunManifest:
        manifest_path = self.session_dir / "run_manifest.json"
        if manifest_path.exists():
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Detect configuration mismatches
            if data.get("topic") != self.course.course_context or data.get("quality_profile") != self.quality_profile.value:
                raise ValueError(f"Configuration mismatch: Manifest topic '{data.get('topic')}' or quality_profile '{data.get('quality_profile')}' does not match current topic '{self.course.course_context}' or quality_profile '{self.quality_profile.value}'.")
            return RunManifest.model_validate(data)
        else:
            manifest = RunManifest(
                course_id=self.course.course_title,
                topic=self.course.course_context,
                lesson_contract=self.lesson_contract,
                quality_profile=self.quality_profile.value,
                completed_submodules=[]
            )
            self.save_manifest(manifest)
            return manifest

    def save_manifest(self, manifest: RunManifest):
        manifest_path = self.session_dir / "run_manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest.model_dump(), f, indent=2)

    def verify_manifest(self, manifest: RunManifest, master_content: str) -> Optional[str]:
        def clean_title(t: str) -> str:
            return re.sub(r'(?i)^module\s+\d+:\s*', '', t).strip().lower()

        # Count expected modules and submodules
        expected_module_count = len(self.course.modules)
        expected_submodule_count = sum(len(m.topics) for m in self.course.modules)
        
        # Check generated module and submodule headings in markdown
        gen_modules = re.findall(r'^# Module \d+:\s*(.*)$', master_content, re.MULTILINE)
        gen_submodules = re.findall(r'^## Submodule:\s*(.*)$', master_content, re.MULTILINE)
        
        if len(gen_modules) != expected_module_count:
            return f"Module count mismatch: expected {expected_module_count}, got {len(gen_modules)}"
            
        if len(gen_submodules) != expected_submodule_count:
            return f"Submodule count mismatch: expected {expected_submodule_count}, got {len(gen_submodules)}"
            
        # Verify final Markdown contains all expected module titles
        expected_modules_cleaned = {clean_title(mod.module_title) for mod in self.course.modules}
        gen_modules_cleaned = {clean_title(m) for m in gen_modules}
        for mod in self.course.modules:
            if clean_title(mod.module_title) not in gen_modules_cleaned:
                return f"Expected module title '{mod.module_title}' is missing from the generated book."
                
        # Verify final Markdown contains all expected submodule titles
        expected_submodules_lower = [sub.topic_title.strip().lower() for mod in self.course.modules for sub in mod.topics]
        for sub_title in expected_submodules_lower:
            if sub_title not in [s.strip().lower() for s in gen_submodules]:
                return f"Expected submodule title '{sub_title}' is missing from the generated book."
                
        # Verify final Markdown does not contain extra module/submodule titles
        for m in gen_modules:
            if clean_title(m) not in expected_modules_cleaned:
                return f"Extra module title found in generated book: '{m}'"
                
        for s in gen_submodules:
            if s.strip().lower() not in expected_submodules_lower:
                return f"Extra submodule title found in generated book: '{s}'"
                
        # Table of Contents matches active input JSON
        toc_match = re.search(r'# Table of Contents\s*(.*?)\s*\n---', master_content, re.DOTALL)
        if not toc_match:
            return "Table of Contents section is missing or malformed in the generated book."
            
        toc_text = toc_match.group(1).lower()
        for title in expected_modules_cleaned:
            if title not in toc_text:
                return f"TOC does not contain module: '{title}'"
        for title in expected_submodules_lower:
            if title not in toc_text:
                return f"TOC does not contain submodule: '{title}'"
                
        # No extra module appears before the first expected module
        for idx, m in enumerate(gen_modules):
            if clean_title(m) != clean_title(self.course.modules[idx].module_title):
                return f"Module order mismatch at index {idx+1}: expected '{self.course.modules[idx].module_title}', got '{m}'"
                
        # Flattened expected submodules list
        all_expected_subs = [sub.topic_title.strip().lower() for mod in self.course.modules for sub in mod.topics]
        for idx, s in enumerate(gen_submodules):
            if s.strip().lower() != all_expected_subs[idx]:
                return f"Submodule order mismatch at index {idx+1}: expected '{all_expected_subs[idx]}', got '{s}'"
                
        return None

    def run_submodule_pipeline(self, submodule: Any, module_title: str, module_context: str, running_summary: str = "", module_position: str = "") -> Tuple[str, str]:
        sub_title = ""
        t_title = getattr(submodule, "topic_title", None)
        if isinstance(t_title, str):
            sub_title = t_title
        else:
            t_title = getattr(submodule, "title", None)
            if isinstance(t_title, str):
                sub_title = t_title
            elif t_title is not None:
                sub_title = str(t_title)

        content_context = ""
        t_context = getattr(submodule, "concept", None)
        if isinstance(t_context, str):
            content_context = t_context
        else:
            t_context = getattr(submodule, "content_context", None)
            if isinstance(t_context, str):
                content_context = t_context
            elif t_context is not None:
                content_context = str(t_context)
        
        # Extract rich add-on fields
        breakdown = getattr(submodule, "breakdown", "")
        constraints = getattr(submodule, "constraints", "")
        edge_cases = getattr(submodule, "edge_cases", "")
        action_items = getattr(submodule, "action_items", [])
        common_mistakes = getattr(submodule, "common_mistakes", [])
        evaluation_path = getattr(submodule, "evaluation_path", "")
        expert_heuristic = getattr(submodule, "expert_heuristic", "")
        
        # Convert lists to markdown bullets
        action_items_str = "\n".join(f"- {item}" for item in action_items) if isinstance(action_items, list) else str(action_items)
        common_mistakes_str = "\n".join(f"- {mistake}" for mistake in common_mistakes) if isinstance(common_mistakes, list) else str(common_mistakes)

        personas_str = self._format_student_personas()
        num_personas = len(getattr(self.course, "student_personas", []) or []) + 1
        self.adjust_contract_word_limits(num_personas)

        addon_kwargs = {
            "breakdown": breakdown,
            "topic_constraints": constraints,
            "edge_cases": edge_cases,
            "action_items": action_items_str,
            "common_mistakes": common_mistakes_str,
            "evaluation_path": evaluation_path,
            "expert_heuristic": expert_heuristic,
            "student_personas": personas_str
        }
        
        # Reset per-agent local token counts
        self.generator.input_tokens = 0
        self.generator.output_tokens = 0
        self.semantic_evaluator.input_tokens = 0
        self.semantic_evaluator.output_tokens = 0
        self.grounding_auditor.input_tokens = 0
        self.grounding_auditor.output_tokens = 0
        self.patch_editor.input_tokens = 0
        self.patch_editor.output_tokens = 0
        
        # Initialize submodule telemetry status to pending/running
        self.update_submodule_telemetry(module_title, sub_title, "deterministic", "-")
        self.update_submodule_telemetry(module_title, sub_title, "grounding", "-")
        self.update_submodule_telemetry(module_title, sub_title, "semantic", "-")
        self.update_submodule_telemetry(module_title, sub_title, "analogy", "-")
        update_telemetry(self.telemetry, session_dir=str(self.session_dir))

        
        # Bounded learned rules (cap at 10)
        learned_rules = self.generator._get_learning_context()
        rules_list = [r.strip() for r in learned_rules.splitlines() if r.strip()]
        if len(rules_list) > 10:
            rules_list = rules_list[-10:]
        bounded_learned_rules = "\n".join(rules_list)
        
        # 1. Generator Initial Run
        self.telemetry["current_agent"] = "Content Generator"
        self.telemetry["active_iterations"] = 1
        update_telemetry(self.telemetry, session_dir=str(self.session_dir))

        # Resolve grounding context
        from src.engine.grounding_resolver import resolve_grounding_context
        curr_module_obj = None
        curr_topic_obj = None
        for m in getattr(self.course, "modules", []):
            if m.module_title == module_title:
                curr_module_obj = m
                for t in m.topics:
                    if t.topic_title == sub_title:
                        curr_topic_obj = t
                        break
                break
        
        resolved_context = resolve_grounding_context(
            self.course, 
            curr_module_obj or ModuleStructure(module_title=module_title, module_context=module_context, topics=[]), 
            curr_topic_obj or Topic(topic_title=sub_title, concept=content_context)
        )
        
        # Format tool_stack
        tool_stack_obj = getattr(self.course, "tool_stack", None)
        from unittest.mock import Mock
        if isinstance(tool_stack_obj, Mock):
            tool_stack_obj = None

        if tool_stack_obj:
            if isinstance(tool_stack_obj, dict):
                tools_list = tool_stack_obj.get("tools", []) or []
                tech_stack_list = tool_stack_obj.get("tech_stack", []) or []
            else:
                tools_list = getattr(tool_stack_obj, "tools", []) or []
                tech_stack_list = getattr(tool_stack_obj, "tech_stack", []) or []
                if isinstance(tools_list, Mock):
                    tools_list = []
                if isinstance(tech_stack_list, Mock):
                    tech_stack_list = []
        else:
            tools_list = []
            tech_stack_list = []
            
        tool_stack_str = (
            f"Tools: {', '.join(tools_list) if tools_list else 'None'}\n"
            f"Tech Stack: {', '.join(tech_stack_list) if tech_stack_list else 'None'}"
        )
        
        # Format grounding_context
        g_parts = []
        c_chunks = resolved_context.get("course_chunks", [])
        if c_chunks:
            g_parts.append("Course Chunks:")
            for chunk in c_chunks:
                g_parts.append(f"- [{chunk['chunk_id']}]: {chunk['text']}")
        m_chunks = resolved_context.get("module_chunks", [])
        if m_chunks:
            g_parts.append("Module Chunks:")
            for chunk in m_chunks:
                g_parts.append(f"- [{chunk['chunk_id']}]: {chunk['text']}")
        t_chunks = resolved_context.get("topic_chunks", [])
        if t_chunks:
            g_parts.append("Topic Chunks:")
            for chunk in t_chunks:
                g_parts.append(f"- [{chunk['chunk_id']}]: {chunk['text']}")
                
        if not g_parts:
            grounding_context_str = "Grounding Context: Empty"
        else:
            grounding_context_str = "\n".join(g_parts)

        # Retrieve and inject DuckDuckGo search context prior to generation
        enable_search = getattr(self.course, "enable_google_search", True)
        from unittest.mock import Mock
        if isinstance(enable_search, Mock):
            enable_search = False
        if enable_search is None:
            enable_search = True

        if enable_search:
            search_query = f"{sub_title} {self.course.course_context}"
            try:
                search_results = search_duckduckgo(search_query)
                if search_results:
                    if grounding_context_str == "Grounding Context: Empty":
                        grounding_context_str = search_results
                    else:
                        grounding_context_str += "\n\n" + search_results
            except Exception as e:
                log_event("Orchestrator", f"Search skipped due to error: {str(e)}")

        log_event("Content Generator", f"Drafting submodule '{sub_title}'...")

        draft = self.generator.generate(
            module_title=module_title,
            sub_title=sub_title,
            content_context=content_context,
            running_summary=running_summary,
            course_info=self.course,
            module_context=module_context,
            lesson_contract=json.dumps(self.lesson_contract.model_dump(), indent=2),
            quality_profile=self.quality_profile.value,
            learned_rules=bounded_learned_rules,
            learner_level=getattr(self.course, "learner_level", "beginner"),
            code_example_style=getattr(self.course, "code_example_style", "progressive_production"),
            explanation_depth=getattr(self.course, "explanation_depth", "balanced"),
            module_position=module_position,
            core_idea_words=getattr(self, "core_idea_words", 100),
            implementation_words=getattr(self, "implementation_words", 150),
            why_it_matters_words=getattr(self, "why_it_matters_words", 50),
            tool_stack=tool_stack_str,
            grounding_context=grounding_context_str,
            **addon_kwargs
        )
        self.update_agent_tokens("content_generator", self.generator)
        update_telemetry(self.telemetry, session_dir=str(self.session_dir))
        log_event("Content Generator", "Generated: Draft created successfully.")
        
        req_headings = [f"### {sec.title}" for sec in self.lesson_contract.sections]
        draft = normalize_draft(draft, sub_title, req_headings)
        
        known_sections = [sec.title for sec in self.lesson_contract.sections]
        draft = normalize_step_headings(draft, known_sections)
        
        update_live_preview(self.session_dir, self.master_file, sub_title, draft, "Drafting")
        
        # Unified validation, audit, and semantic evaluation repair loop
        from src.validators.markdown_validator import validate_markdown_structure
        from src.validators.lesson_contract_validator import validate_lesson_contract
        from src.utils.patch_utils import apply_section_patch

        deterministic_attempts = 0
        grounding_attempts = 0
        semantic_attempts = 0
        
        while True:
            # 1. Deterministic Validation
            self.telemetry["current_agent"] = "Deterministic Validator"
            update_telemetry(self.telemetry, session_dir=str(self.session_dir))
            log_event("Deterministic Validator", "Checking document structure and contract constraints...")
            struct_res = validate_markdown_structure(draft)
            contract_res = validate_lesson_contract(draft, self.lesson_contract)
            all_issues = struct_res.issues + contract_res.issues
            blockers = [i for i in all_issues if i.severity == "blocker"]
            
            if blockers:
                # Check for heading-related issues and normalize programmatically if possible
                heading_issues = [
                    i for i in blockers
                    if i.issue_type in ["invalid_heading_level", "missing_section"]
                    or "heading" in str(i.message).lower()
                    or "header" in str(i.message).lower()
                ]
                if heading_issues:
                    log_event("Deterministic Validator", "Heading level/format blocker detected. Running automatic heading normalization...")
                    draft = normalize_headings_dynamically(draft, req_headings)
                    # Re-run validators
                    struct_res = validate_markdown_structure(draft)
                    contract_res = validate_lesson_contract(draft, self.lesson_contract)
                    all_issues = struct_res.issues + contract_res.issues
                    blockers = [i for i in all_issues if i.severity == "blocker"]

            if blockers:
                if deterministic_attempts >= 2:
                    log_event("Deterministic Validator", f"Failed: Final blockers still present after patches: {blockers[0].message}")
                    self.update_submodule_telemetry(module_title, sub_title, "deterministic", "F")
                    update_telemetry(self.telemetry, session_dir=str(self.session_dir))
                    break
                    
                blocker = blockers[0]
                heading_to_patch = blocker.section or (struct_res.detected_headings[0] if struct_res.detected_headings else "Introduction")
                log_event("Deterministic Validator", f"Failed: Blocker found in '{heading_to_patch}': {blocker.message}")
                
                self.telemetry["patch_attempts"] += 1
                self.telemetry["patch_attempts_log"].append(f"Deterministic | {heading_to_patch} | {blocker.message}")
                self.telemetry["failure_reasons"].append(blocker.model_dump())
                
                self.telemetry["current_agent"] = "Patch Editor"
                total_att = deterministic_attempts + grounding_attempts + semantic_attempts
                self.telemetry["active_iterations"] = 1 + total_att + 1
                update_telemetry(self.telemetry, session_dir=str(self.session_dir))
                
                log_event("Orchestrator", f"--- Submodule Repair Attempt {self.telemetry['active_iterations']} ---")
                log_event("Patch Editor", f"Attempting structural repair on '{heading_to_patch}' ({deterministic_attempts + 1}/2)...")
                
                try:
                    patch_result = self.patch_editor.edit_patch(
                        draft=draft,
                        feedback=blocker.message,
                        heading=heading_to_patch,
                        course_topic=self.course.course_context,
                        submodule_title=sub_title,
                        grounding_context=grounding_context_str,
                        patch_mode="fix_structure",
                        learner_level=getattr(self.course, "learner_level", "beginner")
                    )
                    self.telemetry["patch_mode"] = "fix_structure"
                    
                    if patch_result.operation == "no_safe_patch":
                        log_event("Patch Editor", f"Declined: No safe patch available. {patch_result.reason}")
                    else:
                        log_event("Patch Editor", f"Edited: Patch generated and spliced successfully.")
                        if blocker.issue_type == "missing_section":
                            replacement = patch_result.replacement_markdown.strip()
                            if not replacement.lower().startswith(f"### {heading_to_patch.lower()}"):
                                replacement = f"### {heading_to_patch}\n\n{replacement}"
                            candidate_draft = draft + "\n\n" + replacement
                        else:
                            candidate_draft = apply_section_patch(draft, heading_to_patch, patch_result.replacement_markdown)
                            
                        candidate_draft = normalize_draft(candidate_draft, sub_title, req_headings)
                        candidate_draft = normalize_step_headings(candidate_draft, known_sections)
                        
                        temp_res = validate_markdown_structure(candidate_draft)
                        temp_blockers = [i for i in temp_res.issues if i.severity == "blocker"]
                        if temp_blockers:
                            log_event("Deterministic Validator", f"Patch verification failed! Reverting patch.")
                        else:
                            draft = candidate_draft
                            update_live_preview(self.session_dir, self.master_file, sub_title, draft, f"Repairing ({deterministic_attempts + 1}/2)")
                except Exception as e:
                    log_event("Patch Editor", f"Execution failed: {str(e)}")
                
                self.update_agent_tokens("patch_editor", self.patch_editor)
                update_telemetry(self.telemetry, session_dir=str(self.session_dir))
                deterministic_attempts += 1
                continue
                
            # 2. Grounding Faithfulness Audit
            self.update_submodule_telemetry(module_title, sub_title, "deterministic", str(deterministic_attempts + 1))
            self.telemetry["current_agent"] = "Grounding Faithfulness Auditor"
            self.telemetry["grounding_auditor_attempts"] += 1
            update_telemetry(self.telemetry, session_dir=str(self.session_dir))
            log_event("Grounding Faithfulness Auditor", "Auditing lesson draft grounding faithfulness...")
            
            tool_stack_dict = {"tools": tools_list, "tech_stack": tech_stack_list}
            audit_res = self.grounding_auditor.audit_grounding(
                content=draft,
                course_context=self.course.course_context,
                module_context=module_context,
                topic_context=content_context,
                tool_stack=tool_stack_dict,
                grounding_context=resolved_context
            )
            self.update_agent_tokens("grounding_auditor", self.grounding_auditor)
            
            if audit_res.get("status") != "APPROVED":
                if grounding_attempts >= 2:
                    log_event("Grounding Faithfulness Auditor", f"Failed: Blocker still present after 2 attempts.")
                    self.update_submodule_telemetry(module_title, sub_title, "grounding", "F")
                    update_telemetry(self.telemetry, session_dir=str(self.session_dir))
                    break
                    
                self.telemetry["grounding_auditor_status"] = "failed"
                blockers_list = audit_res.get("blockers", [])
                self.telemetry["grounding_auditor_blockers"] = [b.get("issue", "") for b in blockers_list]
                
                if blockers_list:
                    blocker = blockers_list[0]
                    heading_to_patch = blocker.get("section") or (struct_res.detected_headings[0] if struct_res.detected_headings else "Introduction")
                    feedback_msg = (
                        f"Grounding Faithfulness Auditor found unsupported claims:\n"
                        f"- Section: {heading_to_patch}\n"
                        f"  Issue: {blocker.get('issue')}\n"
                        f"  Suggested fix: {blocker.get('suggested_fix')}"
                    )
                else:
                    heading_to_patch = struct_res.detected_headings[0] if struct_res.detected_headings else "Introduction"
                    feedback_msg = "Grounding Faithfulness Auditor failed: Grounding check did not approve draft."
                
                log_event("Grounding Faithfulness Auditor", f"Failed: Blocker found in '{heading_to_patch}': {feedback_msg}")
                self.telemetry["patch_attempts"] += 1
                self.telemetry["patch_attempts_log"].append(f"Grounding | {heading_to_patch} | {feedback_msg}")
                
                self.telemetry["current_agent"] = "Patch Editor"
                total_att = deterministic_attempts + grounding_attempts + semantic_attempts
                self.telemetry["active_iterations"] = 1 + total_att + 1
                update_telemetry(self.telemetry, session_dir=str(self.session_dir))
                
                log_event("Orchestrator", f"--- Submodule Repair Attempt {self.telemetry['active_iterations']} ---")
                log_event("Patch Editor", f"Attempting grounding repair on '{heading_to_patch}' ({grounding_attempts + 1}/2)...")
                
                try:
                    patch_result = self.patch_editor.edit_patch(
                        draft=draft,
                        feedback=feedback_msg,
                        heading=heading_to_patch,
                        course_topic=self.course.course_context,
                        submodule_title=sub_title,
                        grounding_context=grounding_context_str,
                        patch_mode="fix_structure",
                        learner_level=getattr(self.course, "learner_level", "beginner")
                    )
                    self.telemetry["patch_mode"] = "fix_structure"
                    
                    if patch_result.operation == "no_safe_patch":
                        log_event("Patch Editor", f"Declined: No safe patch available. {patch_result.reason}")
                    else:
                        log_event("Patch Editor", f"Edited: Patch generated and spliced successfully.")
                        candidate_draft = apply_section_patch(draft, heading_to_patch, patch_result.replacement_markdown)
                        candidate_draft = normalize_draft(candidate_draft, sub_title, req_headings)
                        candidate_draft = normalize_step_headings(candidate_draft, known_sections)
                        
                        temp_res = validate_markdown_structure(candidate_draft)
                        temp_blockers = [i for i in temp_res.issues if i.severity == "blocker"]
                        if temp_blockers:
                            log_event("Deterministic Validator", f"Patch verification failed! Reverting patch.")
                        else:
                            draft = candidate_draft
                            update_live_preview(self.session_dir, self.master_file, sub_title, draft, f"Grounding Repair ({grounding_attempts + 1}/2)")
                except Exception as e:
                    log_event("Patch Editor", f"Execution failed: {str(e)}")
                    
                self.update_agent_tokens("patch_editor", self.patch_editor)
                update_telemetry(self.telemetry, session_dir=str(self.session_dir))
                grounding_attempts += 1
                continue
            else:
                self.telemetry["grounding_auditor_status"] = "passed"
                self.telemetry["grounding_auditor_blockers"] = []
                self.update_submodule_telemetry(module_title, sub_title, "grounding", str(grounding_attempts + 1))
                log_event("Grounding Faithfulness Auditor", "Passed: Grounding audit approved.")
                
            # 3. Semantic Evaluation
            self.telemetry["current_agent"] = "Semantic Evaluator"
            total_att = deterministic_attempts + grounding_attempts + semantic_attempts
            self.telemetry["active_iterations"] = 1 + total_att + 1
            update_telemetry(self.telemetry, session_dir=str(self.session_dir))
            log_event("Semantic Evaluator", "Evaluating pedagogical flow and tone...")
            
            eval_res = self.semantic_evaluator.evaluate(
                draft=draft,
                lesson_contract=json.dumps(self.lesson_contract.model_dump(), indent=2),
                course_topic=self.course.course_context,
                submodule_title=sub_title,
                running_summary=running_summary,
                learner_level=getattr(self.course, "learner_level", "beginner"),
                code_example_style=getattr(self.course, "code_example_style", "progressive_production"),
                explanation_depth=getattr(self.course, "explanation_depth", "balanced"),
                module_position=module_position,
                **addon_kwargs
            )
            self.update_agent_tokens("semantic_evaluator", self.semantic_evaluator)
            update_telemetry(self.telemetry, session_dir=str(self.session_dir))
            
            blockers = [i for i in eval_res.issues if i.severity == "blocker"]
            if blockers:
                if semantic_attempts >= 2:
                    log_event("Semantic Evaluator", f"Failed: Blocker still present after 2 attempts.")
                    self.update_submodule_telemetry(module_title, sub_title, "semantic", "F")
                    update_telemetry(self.telemetry, session_dir=str(self.session_dir))
                    break
                    
                blocker = blockers[0]
                heading_to_patch = blocker.section or (eval_res.detected_headings[0] if eval_res.detected_headings else "Introduction")
                log_event("Semantic Evaluator", f"Failed: Blocker found in '{heading_to_patch}': {blocker.message}")
                
                self.telemetry["patch_attempts"] += 1
                self.telemetry["patch_attempts_log"].append(f"Semantic | {heading_to_patch} | {blocker.message}")
                self.telemetry["failure_reasons"].append(blocker.model_dump())
                
                self.telemetry["current_agent"] = "Patch Editor"
                update_telemetry(self.telemetry, session_dir=str(self.session_dir))
                log_event("Patch Editor", f"Attempting semantic repair on '{heading_to_patch}' ({semantic_attempts + 1}/2)...")
                
                msg = blocker.message.lower()
                if any(k in msg for k in ["jargon", "too advanced", "complex", "formula", "abstract"]):
                    p_mode = "simplify_for_beginner"
                elif any(k in msg for k in ["basic", "shallow", "practical", "trade-off"]) and "advanced" not in msg:
                    p_mode = "practicalize_for_intermediate"
                elif any(k in msg for k in ["basic", "shallow", "toy", "internals", "architecture"]):
                    p_mode = "deepen_for_advanced"
                elif any(k in msg for k in ["code", "example", "production"]):
                    p_mode = "adjust_code_progression"
                else:
                    p_mode = "fix_structure"
                    
                try:
                    patch_result = self.patch_editor.edit_patch(
                        draft=draft,
                        feedback=blocker.message,
                        heading=heading_to_patch,
                        course_topic=self.course.course_context,
                        submodule_title=sub_title,
                        grounding_context=grounding_context_str,
                        patch_mode=p_mode,
                        learner_level=getattr(self.course, "learner_level", "beginner"),
                        **addon_kwargs
                    )
                    self.telemetry["patch_mode"] = p_mode
                    
                    if patch_result.operation == "no_safe_patch":
                        log_event("Patch Editor", f"Declined: No safe patch available. {patch_result.reason}")
                    else:
                        log_event("Patch Editor", f"Edited: Patch generated and spliced successfully.")
                        candidate_draft = apply_section_patch(draft, heading_to_patch, patch_result.replacement_markdown)
                        candidate_draft = normalize_draft(candidate_draft, sub_title, req_headings)
                        candidate_draft = normalize_step_headings(candidate_draft, known_sections)
                        
                        temp_res = validate_markdown_structure(candidate_draft)
                        temp_blockers = [i for i in temp_res.issues if i.severity == "blocker"]
                        if temp_blockers:
                            log_event("Deterministic Validator", f"Patch verification failed! Reverting patch.")
                        else:
                            draft = candidate_draft
                            update_live_preview(self.session_dir, self.master_file, sub_title, draft, f"Refining ({semantic_attempts + 1}/2)")
                except Exception as e:
                    log_event("Patch Editor", f"Execution failed: {str(e)}")
                    
                self.update_agent_tokens("patch_editor", self.patch_editor)
                update_telemetry(self.telemetry, session_dir=str(self.session_dir))
                semantic_attempts += 1
                continue
            else:
                self.update_submodule_telemetry(module_title, sub_title, "semantic", str(semantic_attempts + 1))
                log_event("Semantic Evaluator", "Passed: Semantic evaluation approved.")
                
            break

        # Final evaluation to check for warnings
        self.telemetry["current_agent"] = "Semantic Evaluator"
        update_telemetry(self.telemetry, session_dir=str(self.session_dir))
        log_event("Semantic Evaluator", "Performing final semantic evaluation...")
        
        final_eval = self.semantic_evaluator.evaluate(
            draft=draft,
            lesson_contract=json.dumps(self.lesson_contract.model_dump(), indent=2),
            course_topic=self.course.course_context,
            submodule_title=sub_title,
            running_summary=running_summary,
            learner_level=getattr(self.course, "learner_level", "beginner"),
            code_example_style=getattr(self.course, "code_example_style", "progressive_production"),
            explanation_depth=getattr(self.course, "explanation_depth", "balanced"),
            module_position=module_position,
            **addon_kwargs
        )
        self.update_agent_tokens("semantic_evaluator", self.semantic_evaluator)
        
        blockers = [i for i in final_eval.issues if i.severity == "blocker"]
        warnings = [i for i in final_eval.issues if i.severity == "warning"]
        if blockers:
            log_event("Semantic Evaluator", f"Failed: Final blockers still present: {blockers[0].message}")
            self.update_submodule_telemetry(module_title, sub_title, "semantic", "F")
            update_telemetry(self.telemetry, session_dir=str(self.session_dir))
        else:
            log_event("Semantic Evaluator", f"Passed: Evaluation passed. {len(warnings)} warnings found.")
        
        self.telemetry["current_agent"] = "None"
        self.telemetry["active_iterations"] = 0
        update_telemetry(self.telemetry, session_dir=str(self.session_dir))
        
        if blockers:
            return "failed_blocker", draft

        # Core technical content approved. Let's generate student-persona analogies if required.
        requires_analogies = False
        if hasattr(self, "lesson_contract") and self.lesson_contract and self.lesson_contract.sections:
            requires_analogies = any(sec.title == "Persona Analogies" for sec in self.lesson_contract.sections)

        if requires_analogies:
            log_event("Orchestrator", "Core technical content approved. Generating persona analogies...")
            self.telemetry["current_agent"] = "Analogy Generator"
            update_telemetry(self.telemetry, session_dir=str(self.session_dir))
            
            from src.models.schemas import StudentPersona
            personas_str = self._format_student_personas()
            
            self.telemetry["analogy_generator_attempts"] = 1
            analogies_text = self.analogy_generator.generate(
                final_lesson=draft,
                student_personas=personas_str
            )
            self.update_agent_tokens("analogy_generator", self.analogy_generator)
            update_telemetry(self.telemetry, session_dir=str(self.session_dir))
            
            # Audit generated analogies with Analogy Evaluator
            log_event("Orchestrator", "Auditing generated analogies with Analogy Evaluator...")
            self.telemetry["current_agent"] = "Analogy Evaluator"
            update_telemetry(self.telemetry, session_dir=str(self.session_dir))
            
            eval_result = self.analogy_evaluator.evaluate(
                final_lesson=draft,
                analogies=analogies_text,
                student_personas=personas_str
            )
            self.telemetry["analogy_evaluator_status"] = "passed" if eval_result.get("status") == "APPROVED" else "failed"
            self.telemetry["analogy_evaluator_blockers"] = eval_result.get("reasons", [])
            self.update_agent_tokens("analogy_evaluator", self.analogy_evaluator)
            
            if eval_result.get("status") == "APPROVED":
                self.update_submodule_telemetry(module_title, sub_title, "analogy", "1")
            update_telemetry(self.telemetry, session_dir=str(self.session_dir))
            
            # Repair loop (Retry once if rejected)
            if eval_result.get("status") != "APPROVED":
                log_event("Analogy Evaluator", f"Rejected: {', '.join(eval_result.get('reasons', []))}. Retrying repair...")
                self.telemetry["current_agent"] = "Analogy Generator"
                self.telemetry["analogy_generator_attempts"] = 2
                update_telemetry(self.telemetry, session_dir=str(self.session_dir))
                
                repair_prompt = f"The previous analogies were rejected for these reasons: {', '.join(eval_result.get('reasons', []))}. Please rewrite the analogies addressing these issues."
                analogies_text = self.analogy_generator.generate(
                    final_lesson=draft,
                    student_personas=personas_str,
                    feedback=repair_prompt
                )
                self.update_agent_tokens("analogy_generator", self.analogy_generator)
                update_telemetry(self.telemetry, session_dir=str(self.session_dir))
                
                # Re-evaluate
                log_event("Orchestrator", "Re-auditing repaired analogies...")
                self.telemetry["current_agent"] = "Analogy Evaluator"
                update_telemetry(self.telemetry, session_dir=str(self.session_dir))
                eval_result = self.analogy_evaluator.evaluate(
                    final_lesson=draft,
                    analogies=analogies_text,
                    student_personas=personas_str
                )
                self.telemetry["analogy_evaluator_status"] = "passed" if eval_result.get("status") == "APPROVED" else "failed"
                self.telemetry["analogy_evaluator_blockers"] = eval_result.get("reasons", [])
                self.update_agent_tokens("analogy_evaluator", self.analogy_evaluator)
                
                if eval_result.get("status") == "APPROVED":
                    self.update_submodule_telemetry(module_title, sub_title, "analogy", "2")
                update_telemetry(self.telemetry, session_dir=str(self.session_dir))
                
            # Fallback if still rejected or failed
            if eval_result.get("status") != "APPROVED":
                log_event("Analogy Evaluator", "Double validation failure. Falling back to pre-templated analogies.")
                self.telemetry["analogy_fallback_triggered"] = True
                self.update_submodule_telemetry(module_title, sub_title, "analogy", "F")
                update_telemetry(self.telemetry, session_dir=str(self.session_dir))
                
                fallback_parts = []
                active_personas = getattr(self.course, "student_personas", []) or []
                default_p = StudentPersona(
                    name="Default Student",
                    context=f"A general learner seeking practical analogies related to: {self.course.course_context}."
                )
                for p in list(active_personas) + [default_p]:
                    fallback_parts.append(f"##### {p.name}\nLearning {sub_title} is exactly like building a system from its fundamental parts, allowing you to connect raw theory directly to real-world experience.")
                analogies_text = "\n\n".join(fallback_parts)
                
            # Robust regex placeholder replacement
            pattern = re.compile(r'\[PLACEHOLDER\]', re.IGNORECASE)
            if pattern.search(draft):
                draft = pattern.sub(analogies_text, draft)
                log_event("Orchestrator", "Analogies successfully compiled into lesson draft.")
            else:
                log_event("Orchestrator", "WARNING: Analogy placeholder not found. Appending analogies to end.")
                draft += "\n\n" + analogies_text

        self.telemetry["current_agent"] = "None"
        self.telemetry["active_iterations"] = 0
        update_telemetry(self.telemetry, session_dir=str(self.session_dir))

        if warnings:
            return "completed_with_warnings", draft
        else:
            return "approved", draft

    def update_agent_tokens(self, agent_name: str, agent):
        current_val = self.telemetry["per_agent_tokens"].get(agent_name, 0)
        self.telemetry["per_agent_tokens"][agent_name] = current_val + agent.total_tokens
        
        self.telemetry["input_tokens"] += agent.input_tokens
        self.telemetry["output_tokens"] += agent.output_tokens
        self.telemetry["total_tokens"] += agent.total_tokens
        
        agent.input_tokens = 0
        agent.output_tokens = 0

    def run_course_pipeline(self) -> None:
        session_dir = self.session_dir
        
        # Load or create run manifest
        manifest = self.load_or_create_manifest()
        
        # Write Table of Contents if starting new
        if self.run_type != "resume_existing_run":
            # from src.utils.learning_engine import clear_style_guide
            # clear_style_guide()
            with open(self.master_file, 'w', encoding='utf-8') as f:
                f.write(f"# {self.course.course_title}\n\n")
                f.write(f"**Topic:** {self.course.course_context}\n\n")
                f.write("# Table of Contents\n\n")
                for m_idx, mod in enumerate(self.course.modules):
                    m_title = normalize_module_heading(mod.module_title)
                    f.write(f"{m_idx+1}. {m_title}\n")
                    for sub in mod.topics:
                        sub_title = normalize_submodule_heading(sub.topic_title)
                        f.write(f"   - {sub_title}\n")
                f.write("\n---\n\n")
        
        update_live_preview(self.session_dir, self.master_file)
        self.telemetry["status"] = "Running"
        update_telemetry(self.telemetry, session_dir=str(self.session_dir))
        
        total_submodules = sum(len(mod.topics) for mod in self.course.modules)
        running_summary = ""
        
        total_modules = len(self.course.modules)
        for m_idx, mod in enumerate(self.course.modules):
            _check_stop(self.telemetry, self.session_dir)
            total_submodules_in_mod = len(mod.topics)
            
            # Module header
            norm_mod_title = normalize_module_heading(mod.module_title)
            module_header = f"\n# Module {m_idx+1}: {norm_mod_title}\n\n"
            # Read master file and check if module title is already written
            master_content = self.master_file.read_text(encoding="utf-8")
            if f"# Module {m_idx+1}:" not in master_content:
                with open(self.master_file, 'a', encoding='utf-8') as f:
                    f.write(module_header)
                    
            self.telemetry["current_module"] = mod.module_title
            
            # Collect blocker issue types inside this module to detect repeated patterns
            module_blocker_types = []
            
            for s_idx, sub in enumerate(mod.topics):
                _check_stop(self.telemetry, self.session_dir)
                
                # Check if submodule is already completed in manifest (allowing safe resumes)
                if sub.topic_title in manifest.completed_submodules:
                    log_event("System", f"Submodule '{sub.topic_title}' already completed. Skipping.")
                    continue
                    
                update_status(f"Preparing {sub.topic_title}...", session_dir=str(session_dir))
                time.sleep(1)
                
                update_status(f"Generator Agent: Drafting '{sub.topic_title}'", session_dir=str(session_dir))
                log_event("Generator", f"Drafting submodule: {sub.topic_title}", session_dir=str(session_dir))
                
                self.telemetry["current_agent"] = "Generator"
                self.telemetry["current_submodule"] = sub.topic_title
                update_telemetry(self.telemetry, session_dir=str(session_dir))
                
                # Truncate summary if needed
                running_summary = truncate_running_summary(running_summary)
                
                module_position = f"Module {m_idx+1}/{total_modules}, Submodule {s_idx+1}/{total_submodules_in_mod}"
                self.telemetry["module_position"] = module_position
                
                status, draft = self.run_submodule_pipeline(sub, mod.module_title, mod.module_context, running_summary, module_position)
                
                # Check status
                if status == "failed_blocker":
                    # Emit structured error payload
                    failed_blockers = [r for r in self.telemetry["failure_reasons"] if r.get("severity") == "blocker"]
                    final_reason = failed_blockers[-1]["message"] if failed_blockers else "Unknown blocker"
                    
                    final_failure_payload = {
                        "failed_stage": "validation_pipeline",
                        "failure_reason": final_reason,
                        "remaining_blockers": failed_blockers
                    }
                    
                    import json
                    log_event("Orchestrator", f"Submodule '{sub.topic_title}' failed with blocker. Final blocker payload:\n{json.dumps(final_failure_payload, indent=2)}")
                    self.telemetry["failed_max_iterations"] += 1
                else:
                    # Determine computed submodule title
                    sub_title_comp = ""
                    t_title = getattr(sub, "topic_title", None)
                    if isinstance(t_title, str):
                        sub_title_comp = t_title
                    else:
                        t_title = getattr(sub, "title", None)
                        if isinstance(t_title, str):
                            sub_title_comp = t_title
                        elif t_title is not None:
                            sub_title_comp = str(t_title)

                    stats = self.telemetry.get("submodule_telemetry", {}).get(mod.module_title, {}).get(sub_title_comp, {})
                    attempts = [int(v) for v in stats.values() if v in ["1", "2", "3"]]
                    max_att = max(attempts) if attempts else 1
                    if max_att == 1:
                        self.telemetry["passed_1st_iteration"] += 1
                    elif max_att == 2:
                        self.telemetry["passed_2nd_iteration"] += 1
                    elif max_att == 3:
                        self.telemetry["passed_3rd_iteration"] += 1
                        
                # Append submodule content to master file anyway (preserving usability)
                with open(self.master_file, 'a', encoding='utf-8') as f:
                    norm_sub_title = normalize_submodule_heading(sub.topic_title)
                    f.write(f"\n## Submodule: {norm_sub_title}\n\n{draft}\n\n")
                    
                update_live_preview(self.session_dir, self.master_file)
                    
                # Mark as completed in manifest
                manifest.completed_submodules.append(sub.topic_title)
                manifest.per_agent_tokens = self.telemetry["per_agent_tokens"]
                manifest.total_tokens = self.telemetry["total_tokens"]
                self.save_manifest(manifest)
                
                # Telemetry update
                self.telemetry["progress_percent"] = int((len(manifest.completed_submodules) / total_submodules) * 100)
                update_telemetry(self.telemetry, session_dir=str(self.session_dir))
                
                # Run Archivist for this submodule
                log_event("Archivist", f"Summarizing {sub.topic_title}...", session_dir=str(self.session_dir))
                self.telemetry["current_agent"] = "Archivist"
                update_telemetry(self.telemetry, session_dir=str(self.session_dir))
                try:
                    self.archivist.input_tokens = 0
                    self.archivist.output_tokens = 0
                    summary_text = self.archivist.compress_submodule(
                        content=draft,
                        course_info=self.course,
                        module_title=mod.module_title,
                        sub_title=sub.topic_title,
                        running_summary=running_summary
                    )
                    running_summary += f"\n- {sub.topic_title}: {summary_text.strip()}"
                    self.update_agent_tokens("archivist", self.archivist)
                    log_event("Archivist", f"Processed: Submodule compressed successfully. Summary preview: {summary_text[:100]}...")
                except Exception as e:
                    log_event("Archivist", f"Failed: compression error: {str(e)}")
                self.telemetry["current_agent"] = "None"
                update_telemetry(self.telemetry, session_dir=str(self.session_dir))
                    
                # Store any blockers that occurred in this submodule run
                for reason in self.telemetry["failure_reasons"]:
                    if reason.get("severity") == "blocker":
                        module_blocker_types.append(reason["message"])
                    
            # End of module loop: Run Learning Engine if repeated blockers exist
            # Count repeated patterns (any specific failure reason occurring >= 2 times)
            from collections import Counter
            counts = Counter(module_blocker_types)
            repeated_blockers = [reason for reason, count in counts.items() if count >= 2]
            
            if repeated_blockers:
                log_event("LearningEngine", f"Repeated blocker patterns detected: {repeated_blockers}. Recording lesson.")
                for pattern in repeated_blockers:
                    record_lesson(mod.module_title, "Repeated_Pattern", pattern, "")
                    
            # Reset local submodule failure tracking for the next module
            self.telemetry["failure_reasons"] = []
            
        # Final cleanup to remove globally duplicated content
        if self.master_file.exists():
            final_content = final_markdown_cleanup(self.master_file.read_text(encoding="utf-8"))
            self.master_file.write_text(final_content, encoding="utf-8")
            
        update_live_preview(self.session_dir, self.master_file)

        # Export Guard Checks
        master_content = self.master_file.read_text(encoding="utf-8") if self.master_file.exists() else ""
        leakage_error = check_manifest_and_leakage(master_content, self.course)
        manifest_error = self.verify_manifest(manifest, master_content)
        
        if leakage_error or manifest_error:
            error_msg = leakage_error or manifest_error
            log_event("System", f"Export Guard Blocked Export: {error_msg}", session_dir=str(session_dir))
            update_status(f"Export Contaminated: {error_msg}", session_dir=str(session_dir))
            self.telemetry["status"] = "failed_export_contaminated"
            update_telemetry(self.telemetry, session_dir=str(session_dir))
            return

        # Complete
        manifest.per_agent_tokens = self.telemetry["per_agent_tokens"]
        manifest.total_tokens = self.telemetry["total_tokens"]
        self.save_manifest(manifest)
        update_status("Generation Complete! Book Created.", session_dir=str(session_dir))
        log_event("System", "Course generation pipeline finished successfully.", session_dir=str(session_dir))
        self.telemetry["status"] = "Completed"
        update_telemetry(self.telemetry, session_dir=str(session_dir))

def main() -> None:
    if not os.environ.get("GEMINI_API_KEY"):
        print("CRITICAL ERROR: GEMINI_API_KEY not found in environment. Please check your .env file.")
        return

    input_path = PROJECT_ROOT / 'data' / 'input' / 'course_input.json'
    output_dir_env = os.environ.get("OUTPUT_DIR")
    if output_dir_env:
        output_dir = Path(output_dir_env)
    else:
        output_dir = PROJECT_ROOT / 'data' / 'output'
    
    if not input_path.exists():
        print(f"ERROR: Input file not found at {input_path}")
        return

    try:
        data = json.loads(input_path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        print(f"CRITICAL ERROR: course_input.json is invalid JSON: {e}")
        return

    try:
        course = normalize_course_input(data)
    except (ValidationError, ValueError) as e:
        print(f"CRITICAL ERROR: Course Input Schema Validation Failed:\n{e}")
        return

    # Check for incomplete manifest to resume
    run_type = os.environ.get("RUN_TYPE", "new_run")
    latest_session_dir = None
    
    if run_type == "resume_existing_run":
        session_folders = sorted(output_dir.glob("session_*"))
        for s_dir in reversed(session_folders):
            manifest_file = s_dir / "run_manifest.json"
            if manifest_file.exists():
                try:
                    with open(manifest_file, "r", encoding="utf-8") as f:
                        m_data = json.load(f)
                    total_sub = sum(len(m.topics) for m in course.modules)
                    if m_data.get("topic") == course.course_context and len(m_data.get("completed_submodules", [])) < total_sub:
                        latest_session_dir = s_dir
                        print(f"Found incomplete session to resume: {latest_session_dir}")
                        break
                except Exception:
                    pass
                
    if latest_session_dir:
        session_dir = latest_session_dir
    else:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = output_dir / f"session_{timestamp}"
        session_dir.mkdir(parents=True, exist_ok=True)
        print(f"Initializing new session in: {session_dir}")

    orchestrator = Orchestrator(course, session_dir, run_type=run_type)
    orchestrator.run_course_pipeline()

def check_manifest_and_leakage(master_content: str, course: Any) -> Optional[str]:
    def clean_title(t: str) -> str:
        return re.sub(r'(?i)^module\s+\d+:\s*', '', t).strip().lower()

    # Extract expected module and submodule titles supporting both formats
    expected_modules = set()
    expected_submodules = set()
    
    modules = getattr(course, "modules", [])
    for mod in modules:
        m_title = getattr(mod, "module_title", getattr(mod, "title", ""))
        expected_modules.add(clean_title(m_title))
        
        topics = getattr(mod, "topics", getattr(mod, "submodules", []))
        for sub in topics:
            sub_title = getattr(sub, "topic_title", getattr(sub, "title", ""))
            expected_submodules.add(sub_title.strip().lower())

    lines = master_content.splitlines()
    in_code_block = False
    current_section = ""
    
    # Pre-compile matching boundaries and placeholder regexes
    todo_standalone = re.compile(r"^(?:#|\/\/|\/\*|<!--|\s)*TODO(?:\s*:\s*.*)?$|^\s*TODO\s*$|^\s*\[TODO\]\s*$|^\s*\{\{TODO\}\}\s*$")
    tbd_standalone = re.compile(r"^\s*TBD\s*$|^\s*\[TBD\]\s*$|^\s*TBD\s*:\s*.*$")
    bracket_placeholder = re.compile(r"(?i)\[Insert\s+[^\]]+\]|\[Placeholder\s+[^\]]+\]|\[Insert\]")
    
    generic_placeholders = [
        "mocked response",
        "this is a mock core concepts",
        "this is a mock practical application",
        "socratic ed-forge is great",
        "lorem ipsum"
    ]
    
    missing_content_phrases = [
        "coming soon",
        "fill this in",
        "replace this",
        "add details here"
    ]

    instructional_keywords = [
        "avoid", "remove", "clean", "hygiene", "cleanup", "example", 
        "template", "prompt", "explain", "explanation", "tutorial", 
        "guide", "debugging", "paste", "snippet", "comment", "anti-pattern"
    ]

    context_lines = []
    for idx, line in enumerate(lines):
        line_stripped = line.strip()
        line_lower = line.lower()
        
        if line_stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
            
        if not in_code_block and re.match(r"^#{1,6}\s+", line_stripped):
            current_section = line_stripped.lstrip("#").strip().lower()
            
        is_bad_example_section = any(k in current_section for k in ["bad example", "anti-pattern", "before cleanup", "poor practice", "poor", "before"])
        
        matched_term = None
        rule_id = None
        reason = None
        severity = "allow"
        
        from src.utils.placeholder_classifier import classify_placeholder
        res_class = classify_placeholder(line, context_lines, in_code_block=in_code_block)
        if res_class.get("is_blocked"):
            matched_term = res_class["matched_term"]
            rule_id = res_class["rule_id"]
            reason = res_class["reason"]
            severity = "blocker"
            
        context_lines.append(line)
        if len(context_lines) > 8:
            context_lines.pop(0)
                        
        if severity == "blocker":
            if in_code_block and is_bad_example_section:
                severity = "warning"
                continue
                
            if not in_code_block:
                is_quoted = line_stripped.startswith(">") or (line_stripped.startswith('"') and line_stripped.endswith('"')) or (line_stripped.startswith("'") and line_stripped.endswith("'"))
                is_instructional = any(k in line_lower for k in instructional_keywords) or any(k in current_section for k in instructional_keywords)
                if is_quoted or is_instructional:
                    severity = "warning"
                    continue
            
            line_no = idx + 1
            error_details = (
                f"Rule: {rule_id}\n"
                f"Artifact: final_markdown\n"
                f"Line: {line_no}\n"
                f"Snippet: \"{line_stripped}\"\n"
                f"Reason: {reason}"
            )
            return f"Contains placeholder: '{matched_term}'\n{error_details}"

    # Find generated module titles in the text
    # e.g., # Module 1: Introduction to Agents
    gen_modules = re.findall(r'^# Module \d+:\s*(.*)$', master_content, re.MULTILINE)
    for title in gen_modules:
        clean_t = clean_title(title)
        if clean_t not in expected_modules:
            return f"Found extra module title not in config: '{title}'"
            
    # Find generated submodule titles
    # e.g., ## Submodule: 1.1 What Is an AI Agent?
    gen_submodules = re.findall(r'^## Submodule:\s*(.*)$', master_content, re.MULTILINE)
    for title in gen_submodules:
        clean_title_sub = title.strip().lower()
        if clean_title_sub not in expected_submodules:
            return f"Found extra submodule title not in config: '{title}'"
            
    return None

if __name__ == "__main__":
    main()
