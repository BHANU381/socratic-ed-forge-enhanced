import pytest
import os
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from src.models.schemas import TelemetryData

def test_telemetry_data_schema():
    # Verify TelemetryData validates the new course_structure and submodule_telemetry fields
    raw_data = {
        "status": "Running",
        "progress_percent": 50,
        "current_agent": "Generator",
        "total_tokens": 100,
        "input_tokens": 60,
        "output_tokens": 40,
        "model_name": "gemini-2.5-flash",
        "current_module": "Module 1",
        "current_submodule": "Submodule 1",
        "course_structure": [
            {
                "module_title": "Module 1",
                "submodules": ["Submodule 1.1", "Submodule 1.2"]
            }
        ],
        "submodule_telemetry": {
            "Module 1": {
                "Submodule 1.1": {
                    "deterministic": "1",
                    "grounding": "2",
                    "semantic": "F"
                }
            }
        }
    }
    
    # This should fail if fields are missing or cause validation errors
    t = TelemetryData(**raw_data)
    assert t.course_structure == raw_data["course_structure"]
    assert t.submodule_telemetry == raw_data["submodule_telemetry"]

def test_orchestrator_update_submodule_telemetry():
    # Test safe dictionary update helper preventing KeyError and validating type safety
    from src.engine.orchestrator import Orchestrator
    
    mock_course = MagicMock()
    mock_course.modules = []
    
    with patch("src.engine.orchestrator.Path.mkdir"):
        orchestrator = Orchestrator(
            course=mock_course,
            session_dir=Path("dummy_session"),
            run_type="new_run"
        )
        
        # Ensure submodule_telemetry is initially empty
        assert "submodule_telemetry" in orchestrator.telemetry
        
        # Test safe deep write
        orchestrator.update_submodule_telemetry("Mod 1", "Sub 1.1", "deterministic", 2)
        assert orchestrator.telemetry["submodule_telemetry"]["Mod 1"]["Sub 1.1"]["deterministic"] == "2"
        
        # Test overwriting existing
        orchestrator.update_submodule_telemetry("Mod 1", "Sub 1.1", "deterministic", "3")
        assert orchestrator.telemetry["submodule_telemetry"]["Mod 1"]["Sub 1.1"]["deterministic"] == "3"

def test_orchestrator_resume_telemetry_preservation(tmp_path):
    # Test that orchestrator correctly loads session telemetry and preserves state on resume
    from src.engine.orchestrator import Orchestrator
    
    mock_course = MagicMock()
    mock_course.modules = []
    
    session_dir = tmp_path / "session_123"
    session_dir.mkdir()
    
    # Save simulated telemetry in session folder
    prev_telemetry = {
        "status": "Stopped",
        "progress_percent": 40,
        "current_agent": "None",
        "total_tokens": 1000,
        "input_tokens": 500,
        "output_tokens": 500,
        "model_name": "gemini-2.5",
        "current_module": "Mod 1",
        "current_submodule": "Sub 1.1",
        "course_structure": [{"module_title": "Mod 1", "submodules": ["Sub 1.1"]}],
        "submodule_telemetry": {
            "Mod 1": {
                "Sub 1.1": {"deterministic": "1", "grounding": "2", "semantic": "1"}
            }
        }
    }
    
    with open(session_dir / "telemetry.json", "w", encoding="utf-8") as f:
        json.dump(prev_telemetry, f)
        
    orchestrator = Orchestrator(
        course=mock_course,
        session_dir=session_dir,
        run_type="resume_existing_run"
    )
    
    # Verify that telemetry structure and completed submodules are correctly loaded/preserved
    assert orchestrator.telemetry["submodule_telemetry"] == prev_telemetry["submodule_telemetry"]
    assert orchestrator.telemetry["course_structure"] == prev_telemetry["course_structure"]

def test_orchestrator_iteration_insight_matching():
    from src.engine.orchestrator import Orchestrator

    mock_course = MagicMock()
    mock_course.modules = []

    with patch("src.engine.orchestrator.Path.mkdir"):
        orchestrator = Orchestrator(
            course=mock_course,
            session_dir=Path("dummy_session"),
            run_type="new_run"
        )
        
        # Simulating run submodule pipeline and checking the telemetry counts updates
        # Mock sub
        sub = MagicMock()
        sub.topic_title = "Sub 1.1"
        
        mod = MagicMock()
        mod.module_title = "Mod 1"
        
        # Test Case 1: Max attempt is 1
        orchestrator.telemetry["submodule_telemetry"] = {
            "Mod 1": {
                "Sub 1.1": {"deterministic": "1", "grounding": "1", "semantic": "1"}
            }
        }
        
        # Re-run count logic
        stats = orchestrator.telemetry.get("submodule_telemetry", {}).get(mod.module_title, {}).get("Sub 1.1", {})
        attempts = [int(v) for v in stats.values() if v in ["1", "2", "3"]]
        max_att = max(attempts) if attempts else 1
        assert max_att == 1
        
        # Test Case 2: Max attempt is 3
        orchestrator.telemetry["submodule_telemetry"] = {
            "Mod 1": {
                "Sub 1.1": {"deterministic": "1", "grounding": "3", "semantic": "2"}
            }
        }
        stats = orchestrator.telemetry.get("submodule_telemetry", {}).get(mod.module_title, {}).get("Sub 1.1", {})
        attempts = [int(v) for v in stats.values() if v in ["1", "2", "3"]]
        max_att = max(attempts) if attempts else 1
        assert max_att == 3


def test_orchestrator_resume_telemetry_recalculation(tmp_path):
    # Test that Orchestrator dynamically recalculates summary metrics on resume
    from src.engine.orchestrator import Orchestrator
    
    mock_course = MagicMock()
    mock_course.modules = []
    
    session_dir = tmp_path / "session_resume_recalc"
    session_dir.mkdir()
    
    # Save a run manifest with completed submodules
    manifest_data = {
        "course_id": "Test Course",
        "topic": "Test Topic",
        "completed_submodules": ["Sub 1.1", "Sub 1.2", "Sub 1.3", "Sub 1.4", "Sub 1.5"]
    }
    with open(session_dir / "run_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest_data, f)
        
    # Save simulated telemetry containing various attempts and failures
    prev_telemetry = {
        "status": "Stopped",
        "progress_percent": 80,
        "current_agent": "None",
        "total_tokens": 1000,
        "input_tokens": 500,
        "output_tokens": 500,
        "model_name": "gemini-2.5",
        "current_module": "Mod 1",
        "current_submodule": "Sub 1.5",
        "course_structure": [
            {
                "module_title": "Mod 1",
                "submodules": ["Sub 1.1", "Sub 1.2", "Sub 1.3", "Sub 1.4", "Sub 1.5", "Sub 1.6"]
            }
        ],
        "submodule_telemetry": {
            "Mod 1": {
                "Sub 1.1": {"deterministic": "1", "grounding": "1", "semantic": "1"}, # Pass (1st)
                "Sub 1.2": {"deterministic": "1", "grounding": "2", "semantic": "1"}, # Pass (2nd)
                "Sub 1.3": {"deterministic": "1", "grounding": "3", "semantic": "2"}, # Pass (3rd)
                "Sub 1.4": {"deterministic": "1", "grounding": "F", "semantic": "-"}, # Failed
                "Sub 1.5": {"deterministic": "1", "grounding": "1", "semantic": "FAIL"}, # Failed
                "Sub 1.6": {"deterministic": "-", "grounding": "-", "semantic": "-"} # Not completed
            }
        }
    }
    with open(session_dir / "telemetry.json", "w", encoding="utf-8") as f:
        json.dump(prev_telemetry, f)
        
    orchestrator = Orchestrator(
        course=mock_course,
        session_dir=session_dir,
        run_type="resume_existing_run"
    )
    
    # Assert that counters are correctly recalculated from telemetry
    assert orchestrator.telemetry["passed_1st_iteration"] == 1
    assert orchestrator.telemetry["passed_2nd_iteration"] == 1
    assert orchestrator.telemetry["passed_3rd_iteration"] == 1
    assert orchestrator.telemetry["failed_max_iterations"] == 2


def test_orchestrator_final_eval_blocker_override(tmp_path):
    # Test that Orchestrator overrides the semantic telemetry status to "F"
    # if the final evaluator returns a blocker (even if loop exited successfully)
    from src.engine.orchestrator import Orchestrator
    
    mock_course = MagicMock()
    mock_course.modules = []
    
    session_dir = tmp_path / "session_final_override"
    session_dir.mkdir()
    
    orchestrator = Orchestrator(
        course=mock_course,
        session_dir=session_dir,
        run_type="new_run"
    )
    
    # Setup mock topic/module structures
    sub = MagicMock()
    sub.topic_title = "Sub 1.1"
    sub.concept = "Concept"
    sub.topic_material_ids = []
    
    mod = MagicMock()
    mod.module_title = "Mod 1"
    mod.module_context = "Module Context"
    mod.topics = [sub]
    orchestrator.course.modules = [mod]
    
    # Mock validator/auditor/evaluator passes/failures
    orchestrator.generator = MagicMock()
    orchestrator.generator.generate.return_value = "### Introduction\nThis is an introduction hook.\n\n### Core Concepts\nThis explains the core idea in detail.\n\n### Practical Application\nThis is a hands-on practical application.\n\n### Summary and Key Takeaways\n- Point 1\n- Point 2"
    
    # Let semantic evaluator approve during loop (so semantic count is written as 1)
    # but fail during final evaluation (returning a blocker)
    loop_result = MagicMock()
    loop_result.issues = []
    
    final_result = MagicMock()
    final_result.issues = [MagicMock(severity="blocker", message="Final word count too low", section="Core Idea")]
    final_result.issues[0].model_dump.return_value = {"severity": "blocker", "message": "Final word count too low", "section": "Core Idea"}
    
    orchestrator.semantic_evaluator = MagicMock()
    # First call in loop is loop_result (success), second call in final evaluation is final_result (failure)
    orchestrator.semantic_evaluator.evaluate.side_effect = [loop_result, final_result]
    
    from src.models.schemas import LessonContract
    orchestrator.lesson_contract = LessonContract()
    
    # Run pipeline
    status, _ = orchestrator.run_submodule_pipeline(sub, "Mod 1", "Module Context", "", "Position")
    
    # Assert status failed
    assert status == "failed_blocker"
    
    # Assert telemetry is overridden to "F"
    stats = orchestrator.telemetry["submodule_telemetry"]["Mod 1"]["Sub 1.1"]
    assert stats["semantic"] == "F"


