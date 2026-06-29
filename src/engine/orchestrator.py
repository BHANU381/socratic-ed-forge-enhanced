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

from src.agents.core import ContentGenerator, SemanticEvaluator, PatchEditor, Archivist
from src.utils.logger import log_event, update_status, update_telemetry
# from src.utils.learning_engine import record_lesson
from src.utils.string_utils import normalize_module_heading, normalize_submodule_heading, normalize_step_headings
from src.utils.cleanup_utils import final_markdown_cleanup
from src.models.schemas import CourseStructure, ModuleStructure, Topic, TelemetryData, RunManifest, LessonContract, SectionRequirement, QualityProfile, normalize_course_input

# Load environment variables
load_dotenv()

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
        self.patch_editor = PatchEditor("Patch Editor", theme=self.course.prompt_theme)
        self.archivist = Archivist("Archivist", theme=self.course.prompt_theme)
        
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
            "failure_reasons": []
        }

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

        addon_kwargs = {
            "breakdown": breakdown,
            "topic_constraints": constraints,
            "edge_cases": edge_cases,
            "action_items": action_items_str,
            "common_mistakes": common_mistakes_str,
            "evaluation_path": evaluation_path,
            "expert_heuristic": expert_heuristic
        }
        
        # Reset per-agent local token counts
        self.generator.input_tokens = 0
        self.generator.output_tokens = 0
        self.semantic_evaluator.input_tokens = 0
        self.semantic_evaluator.output_tokens = 0
        self.patch_editor.input_tokens = 0
        self.patch_editor.output_tokens = 0
        
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
        
        # 2. Deterministic Validation -> Patch (Max 2 retries)
        from src.validators.markdown_validator import validate_markdown_structure
        from src.validators.lesson_contract_validator import validate_lesson_contract
        from src.utils.patch_utils import apply_section_patch
        
        det_attempts = 0
        while det_attempts < 2:
            self.telemetry["current_agent"] = "Deterministic Validator"
            update_telemetry(self.telemetry, session_dir=str(self.session_dir))
            
            log_event("Deterministic Validator", "Checking document structure and contract constraints...")
            struct_res = validate_markdown_structure(draft)
            contract_res = validate_lesson_contract(draft, self.lesson_contract)
            
            all_issues = struct_res.issues + contract_res.issues
            blockers = [i for i in all_issues if i.severity == "blocker"]
            
            if not blockers:
                log_event("Deterministic Validator", "Passed: No structural blockers found.")
                break
                
            blocker = blockers[0]
            # Find which section we need to target
            heading_to_patch = blocker.section or (struct_res.detected_headings[0] if struct_res.detected_headings else "Introduction")
            
            log_event("Deterministic Validator", f"Failed: Blocker found in '{heading_to_patch}': {blocker.message}")
            self.telemetry["patch_attempts"] += 1
            self.telemetry["patch_attempts_log"].append(f"Deterministic | {heading_to_patch} | {blocker.message}")
            self.telemetry["failure_reasons"].append(blocker.model_dump())
            
            self.telemetry["current_agent"] = "Patch Editor"
            self.telemetry["active_iterations"] = 1 + det_attempts + 1
            update_telemetry(self.telemetry, session_dir=str(self.session_dir))
            
            log_event("Orchestrator", f"--- Submodule Attempt {self.telemetry['active_iterations']} ---")
            log_event("Patch Editor", f"Attempting structural repair on '{heading_to_patch}' ({det_attempts + 1}/2)...")

            try:
                patch_result = self.patch_editor.edit_patch(
                    draft=draft,
                    feedback=blocker.message,
                    heading=heading_to_patch,
                    course_topic=self.course.course_context,
                    submodule_title=sub_title,
                    patch_mode="fix_structure",
                    learner_level=getattr(self.course, "learner_level", "beginner")
                )
                self.telemetry["patch_mode"] = "fix_structure"
                
                if patch_result.operation == "no_safe_patch":
                    log_event("Patch Editor", f"Declined: No safe patch available. {patch_result.reason}")
                else:
                    log_event("Patch Editor", f"Edited: Patch generated and spliced successfully.")
                    previous_valid_draft = draft
                    
                    if blocker.issue_type == "missing_section":
                        # If the section is completely missing, append it rather than replace
                        replacement = patch_result.replacement_markdown.strip()
                        if not replacement.lower().startswith(f"### {heading_to_patch.lower()}"):
                            replacement = f"### {heading_to_patch}\n\n{replacement}"
                        candidate_draft = draft + "\n\n" + replacement
                    else:
                        candidate_draft = apply_section_patch(draft, heading_to_patch, patch_result.replacement_markdown)
                        
                    candidate_draft = normalize_draft(candidate_draft, sub_title, req_headings)
                    candidate_draft = normalize_step_headings(candidate_draft, known_sections)
                    
                    # Transactional verification: ensure patch didn't break markdown integrity
                    temp_res = validate_markdown_structure(candidate_draft)
                    temp_blockers = [i for i in temp_res.issues if i.severity == "blocker"]
                    if temp_blockers:
                        log_event("Deterministic Validator", f"Patch verification failed! New blocker introduced: '{temp_blockers[0].issue_type}'. Orchestrator reverting patch.")
                    else:
                        draft = candidate_draft
                        update_live_preview(self.session_dir, self.master_file, sub_title, draft, f"Repairing ({det_attempts + 1}/2)")
            except Exception as e:
                log_event("Patch Editor", f"Execution failed: {str(e)}")
                
            self.update_agent_tokens("patch_editor", self.patch_editor)
            update_telemetry(self.telemetry, session_dir=str(self.session_dir))
            det_attempts += 1
            
        # Re-verify deterministic validation
        log_event("Deterministic Validator", "Performing final structural verification...")
        struct_res = validate_markdown_structure(draft)
        contract_res = validate_lesson_contract(draft, self.lesson_contract)
        all_issues = struct_res.issues + contract_res.issues
        blockers = [i for i in all_issues if i.severity == "blocker"]
        
        if blockers:
            log_event("Deterministic Validator", f"Failed: Final blockers still present after patches: {blockers[0].message}")
            self.telemetry["current_agent"] = "None"
            self.telemetry["active_iterations"] = 0
            update_telemetry(self.telemetry, session_dir=str(self.session_dir))
            return "failed_blocker", draft
        
        log_event("Deterministic Validator", "Passed: No structural blockers found in final verification.")
            
        # 3. Semantic Evaluator -> Patch (Max 2 retries)
        sem_attempts = 0
        while sem_attempts < 2:
            if self.quality_profile == QualityProfile.LIGHT:
                break
            
            self.telemetry["current_agent"] = "Semantic Evaluator"
            self.telemetry["active_iterations"] = 1 + det_attempts + sem_attempts + 1
            update_telemetry(self.telemetry, session_dir=str(self.session_dir))

            log_event("Orchestrator", f"--- Submodule Attempt {self.telemetry['active_iterations']} ---")
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
            if not blockers:
                log_event("Semantic Evaluator", "Passed: No critical semantic blockers.")
                break
                
            blocker = blockers[0]
            heading_to_patch = blocker.section or (eval_res.detected_headings[0] if eval_res.detected_headings else "Introduction")
            
            log_event("Semantic Evaluator", f"Failed: Blocker found in '{heading_to_patch}': {blocker.message}")
            self.telemetry["patch_attempts"] += 1
            self.telemetry["patch_attempts_log"].append(f"Semantic | {heading_to_patch} | {blocker.message}")
            self.telemetry["failure_reasons"].append(blocker.model_dump())
            
            self.telemetry["current_agent"] = "Patch Editor"
            update_telemetry(self.telemetry, session_dir=str(self.session_dir))
            
            log_event("Patch Editor", f"Attempting semantic repair on '{heading_to_patch}' ({sem_attempts + 1}/2)...")

            # Determine semantic patch mode
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
                    patch_mode=p_mode,
                    learner_level=getattr(self.course, "learner_level", "beginner"),
                    **addon_kwargs
                )
                self.telemetry["patch_mode"] = p_mode
                
                if patch_result.operation == "no_safe_patch":
                    log_event("Patch Editor", f"Declined: No safe patch available. {patch_result.reason}")
                else:
                    log_event("Patch Editor", f"Edited: Patch generated and spliced successfully.")
                    previous_valid_draft = draft
                    candidate_draft = apply_section_patch(draft, heading_to_patch, patch_result.replacement_markdown)
                    candidate_draft = normalize_draft(candidate_draft, sub_title, req_headings)
                    candidate_draft = normalize_step_headings(candidate_draft, known_sections)
                    
                    # Transactional verification: ensure patch didn't break markdown integrity
                    temp_res = validate_markdown_structure(candidate_draft)
                    temp_blockers = [i for i in temp_res.issues if i.severity == "blocker"]
                    if temp_blockers:
                        log_event("Deterministic Validator", f"Patch verification failed! New blocker introduced: '{temp_blockers[0].issue_type}'. Orchestrator reverting patch.")
                    else:
                        draft = candidate_draft
                        update_live_preview(self.session_dir, self.master_file, sub_title, draft, f"Refining ({sem_attempts + 1}/2)")
            except Exception as e:
                log_event("Patch Editor", f"Execution failed: {str(e)}")
                
            self.update_agent_tokens("patch_editor", self.patch_editor)
            update_telemetry(self.telemetry, session_dir=str(self.session_dir))
            sem_attempts += 1
            
        # Final evaluation
        if self.quality_profile != QualityProfile.LIGHT:
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
            else:
                log_event("Semantic Evaluator", f"Passed: Evaluation passed. {len(warnings)} warnings found.")
        else:
            blockers = []
            warnings = []
        
        self.telemetry["current_agent"] = "None"
        self.telemetry["active_iterations"] = 0
        update_telemetry(self.telemetry, session_dir=str(self.session_dir))
        
        if blockers:
            return "failed_blocker", draft
        elif warnings:
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
                    if status == "approved":
                        self.telemetry["passed_1st_iteration"] += 1
                    elif status == "completed_with_warnings":
                        self.telemetry["passed_2nd_iteration"] += 1
                        
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
                update_telemetry(self.telemetry, session_dir=str(session_dir))
                
                # Run Archivist for this submodule
                log_event("Archivist", f"Summarizing {sub.topic_title}...", session_dir=str(session_dir))
                self.telemetry["current_agent"] = "Archivist"
                update_telemetry(self.telemetry, session_dir=str(session_dir))
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
                    # record_lesson(mod.module_title, "Repeated_Pattern", pattern, "")
                    pass
                    
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
    
    # Check for known mock/test placeholders case-insensitively
    placeholders = [
        "mocked response",
        "this is a mock core concepts",
        "this is a mock practical application",
        "socratic ed-forge is great",
        "lorem ipsum",
        "todo",
        "tbd",
        "[insert]"
    ]
    for p in placeholders:
        if p in master_content.lower():
            return f"Contains placeholder: '{p}'"
            
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
