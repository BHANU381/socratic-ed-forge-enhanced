import os
import sys
import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import schemas and other elements
from src.models.schemas import EvalResult

def setup_mock_client():
    # Mock genai.Client
    mock_client = MagicMock()
    
    # Mock models.generate_content
    # Depending on who is calling, return a mock response with usage_metadata and candidates
    def generate_content_side_effect(model, contents, config=None):
        mock_resp = MagicMock()
        mock_resp.usage_metadata.prompt_token_count = 10
        mock_resp.usage_metadata.candidates_token_count = 20
        
        # Determine agent role from system instruction
        system_instruction = config.get("system_instruction", "") if config else ""
        
        # Mock responses
        part = MagicMock()
        if "curriculum-judge-eval" in system_instruction or "course-quality-judge-eval" in system_instruction:
            # Return valid JSON matching EvalResult
            eval_res = EvalResult(
                eval_name="Mock Eval",
                passed=True,
                score=95,
                critical_issues=[],
                minor_issues=[],
                fix_recommendations=[],
                failure_owner="None"
            )
            part.text = eval_res.model_dump_json()
        elif "Content Generator" in system_instruction:
            part.text = "### Introduction\nThis is a mock introduction.\n\n### Core Concepts\nThis is a mock core concepts.\n\n### Practical Application\nThis is a mock practical application.\n\n### Summary and Key Takeaways\n- Socratic Ed-Forge is great.\n"
        elif "Fact-Checker" in system_instruction or "Librarian" in system_instruction or "Critic" in system_instruction or "Internal Librarian" in system_instruction:
            part.text = "APPROVED"
        elif "style-synthesizer" in system_instruction:
            part.text = "NEW"
        else:
            part.text = "Mocked Response"
            
        mock_resp.candidates = [MagicMock(content=MagicMock(parts=[part]))]
        return mock_resp
        
    mock_client.models.generate_content.side_effect = generate_content_side_effect
    
    # Mock chats.create
    mock_chat = MagicMock()
    def send_message_side_effect(message):
        mock_resp = MagicMock()
        mock_resp.usage_metadata.prompt_token_count = 5
        mock_resp.usage_metadata.candidates_token_count = 5
        part = MagicMock()
        part.text = "APPROVED"
        mock_resp.candidates = [MagicMock(content=MagicMock(parts=[part]))]
        return mock_resp
        
    mock_chat.send_message.side_effect = send_message_side_effect
    mock_client.chats.create.return_value = mock_chat
    
    return mock_client

def run_verification(theme: str):
    print(f"\n--- VERIFYING THEME: {theme} ---")
    
    # Paths
    input_path = PROJECT_ROOT / 'data' / 'input' / 'course_input.json'
    backup_path = PROJECT_ROOT / 'data' / 'input' / 'course_input_backup.json'
    
    # Backup existing input file
    if input_path.exists():
        shutil.copy2(input_path, backup_path)
        
    try:
        # Load existing inputs
        if backup_path.exists():
            with open(backup_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {
                "course_name": "Test Course",
                "topic": "Python Programming",
                "duration_weeks": 4,
                "modules": []
            }
            
        # Update theme
        data["prompt_theme"] = theme
        
        # Limit to 1 module and 1 submodule to make execution fast
        data["modules"] = [
            {
                "title": "Module 1: Test Module",
                "module_context": "Testing the loop",
                "submodules": [
                    {
                        "title": "1.1 Test Submodule",
                        "content_context": "Testing content context"
                    }
                ]
            }
        ]
        
        with open(input_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
            
        # Run main loop
        test_output_dir = PROJECT_ROOT / 'tests' / 'output'
        test_output_dir.mkdir(parents=True, exist_ok=True)
        
        mock_client = setup_mock_client()
        with patch('google.genai.Client', return_value=mock_client), \
             patch.dict(os.environ, {
                 "GEMINI_API_KEY": "test_api_key",
                 "RUN_EVALS": "true",
                 "OUTPUT_DIR": str(test_output_dir)
             }):
            from src.engine.orchestrator import main
            main()
            print(f"Theme {theme} executed successfully without crashes.")
            
    except Exception as e:
        print(f"CRASH DETECTED for theme {theme}: {e}")
        import traceback
        traceback.print_exc()
        raise e
    finally:
        # Restore backup
        if backup_path.exists():
            try:
                # Read backup and write to input to avoid WinError 32 sharing violations
                input_path.write_bytes(backup_path.read_bytes())
                try: os.remove(backup_path)
                except Exception: pass
            except Exception:
                # Fallback to standard move if possible
                try:
                    if input_path.exists():
                        try: os.remove(input_path)
                        except Exception: pass
                    shutil.move(backup_path, input_path)
                except Exception:
                    pass

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--theme", required=True, help="Theme to verify")
    args = parser.parse_args()
    
    run_verification(args.theme)
