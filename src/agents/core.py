import os
import time
import random
import glob
import json
import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import errors

# Load env variables
load_dotenv()

# Define Project Root relative to this file's location
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

from src.utils.logger import log_event
from src.utils.learning_engine import get_learned_lessons
from src.utils.rate_limiter import RateLimiter
from src.utils.prompt_loader import load_prompt

try:
    rpm_limit = int(os.environ.get("RPM_LIMIT")) if os.environ.get("RPM_LIMIT") else None
except ValueError:
    rpm_limit = None

try:
    tpm_limit = int(os.environ.get("TPM_LIMIT")) if os.environ.get("TPM_LIMIT") else None
except ValueError:
    tpm_limit = None

rate_limiter = RateLimiter(rpm_limit=rpm_limit, tpm_limit=tpm_limit)

class AgentBase:
    """Base class for all agents with built-in error handling, pacing, and learning."""
    def __init__(self, role, model_id="gemini-3.1-flash-lite", max_consecutive_failures=3, theme="default"):
        self.role = role
        self.model_id = model_id
        self.theme = theme
        self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        self.system_instruction = f"You are an expert {role} in a high-end textbook production team. Your output must be academic, precise, and free of any conversational fluff."
        self.input_tokens = 0
        self.output_tokens = 0
        self.consecutive_failures = 0
        self.max_consecutive_failures = max_consecutive_failures
        self.last_error = ""

    @property
    def total_tokens(self):
        return self.input_tokens + self.output_tokens

    def _get_learning_context(self) -> str:
        """
        Returns historical quality guidance.

        Current implementation:
            Raw Experience Replay.

        Future implementation:
            Synthesized Style-Guide Engine.

        The returned content must never be treated as curriculum source material.
        """
        lessons = get_learned_lessons()
        if lessons:
            return lessons.strip()
        return ""

    def _run_with_retry(self, prompt, response_schema=None):
        from src.utils.logger import log_event
        
        retries = 0
        base_backoff = 10 

        while retries < 10:
            # Pacing / Rate limiting check before API call
            estimated_tokens = len(prompt) // 3
            rate_limiter.wait_if_needed(estimated_tokens)

            try:
                config = {"system_instruction": self.system_instruction}
                if hasattr(self, 'response_schema') and self.response_schema:
                    config["response_mime_type"] = "application/json"
                    config["response_schema"] = self.response_schema
                    
                response = self.client.models.generate_content(
                    model=self.model_id,
                    contents=prompt,
                    config=config
                )
                # Track specific token usage from metadata
                actual_prompt_tokens = 0
                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    self.input_tokens += response.usage_metadata.prompt_token_count
                    self.output_tokens += response.usage_metadata.candidates_token_count
                    actual_prompt_tokens = response.usage_metadata.prompt_token_count
                else:
                    actual_prompt_tokens = estimated_tokens
                
                # Record request into history
                rate_limiter.record_request(actual_prompt_tokens)
                
                # Reset consecutive failures on success
                self.consecutive_failures = 0
                
                # Explicitly extract text parts to avoid 'thought_signature' warnings from the SDK
                text_parts = [part.text for part in response.candidates[0].content.parts if part.text]
                result_text = "".join(text_parts)
                
                return result_text
            except (errors.ServerError, errors.APIError) as e:
                # Handle transient API errors
                self.consecutive_failures += 1
                self.last_error = str(e)
                
                if self.consecutive_failures >= self.max_consecutive_failures:
                    raise Exception(f"[{self.role}] Critical failure threshold reached ({self.consecutive_failures} consecutive errors). Last error: {self.last_error}")
                
                error_str = str(e)
                if any(code in error_str for code in ["429", "500", "503", "RESOURCE_EXHAUSTED", "UNAVAILABLE", "INTERNAL"]):
                    # Intelligent Quota Retry check: Parse from structured details or text
                    sleep_time = None
                    if hasattr(e, 'details') and e.details:
                        import re
                        for detail in e.details:
                            if isinstance(detail, dict) and 'retryDelay' in detail:
                                delay_str = detail['retryDelay']
                                match = re.search(r'([\d\.]+)', delay_str)
                                if match:
                                    sleep_time = float(match.group(1)) + 1.0
                                    break
                    if not sleep_time:
                        import re
                        match = re.search(r'Please retry in ([\d\.]+)s', error_str)
                        if match:
                            sleep_time = float(match.group(1)) + 1.0
                    
                    if not sleep_time:
                        jitter = random.uniform(0, 5)
                        sleep_time = (base_backoff * (1.5 ** retries)) + jitter
                        
                    log_event(self.role, f"API Busy/Error ({error_str}). Retrying in {sleep_time:.1f}s...")
                    time.sleep(sleep_time)
                    retries += 1
                else:
                    raise e
            except Exception as e:
                # Non-API errors
                self.consecutive_failures += 1
                self.last_error = str(e)
                if self.consecutive_failures >= self.max_consecutive_failures:
                    raise Exception(f"[{self.role}] Critical failure threshold reached ({self.consecutive_failures} consecutive errors). Last error: {self.last_error}")
                
                log_event(self.role, f"Unexpected error: {str(e)}. Retrying...")
                time.sleep(5)
                retries += 1
        raise Exception(f"[{self.role}] Failed after {retries} retries. Last error: {self.last_error}")

    def start_chat_session(self):
        """Initializes a stateful chat session for this agent."""
        config = {"system_instruction": self.system_instruction}
        if hasattr(self, 'response_schema') and self.response_schema:
            config["response_mime_type"] = "application/json"
            config["response_schema"] = self.response_schema
            
        return self.client.chats.create(
            model=self.model_id,
            config=config
        )

    def _send_message_with_retry(self, chat_session, message):
        """Sends a message to an existing chat session with intelligent retries and pacing."""
        from src.utils.logger import log_event
        
        retries = 0
        base_backoff = 10 

        while retries < 10:
            estimated_tokens = len(message) // 3
            rate_limiter.wait_if_needed(estimated_tokens)

            try:
                response = chat_session.send_message(message)
                
                # Track token usage from metadata
                actual_prompt_tokens = 0
                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    self.input_tokens += response.usage_metadata.prompt_token_count
                    self.output_tokens += response.usage_metadata.candidates_token_count
                    actual_prompt_tokens = response.usage_metadata.prompt_token_count
                else:
                    actual_prompt_tokens = estimated_tokens
                
                rate_limiter.record_request(actual_prompt_tokens)
                self.consecutive_failures = 0
                
                text_parts = [part.text for part in response.candidates[0].content.parts if part.text]
                return "".join(text_parts)
                
            except (errors.ServerError, errors.APIError) as e:
                self.consecutive_failures += 1
                self.last_error = str(e)
                
                if self.consecutive_failures >= self.max_consecutive_failures:
                    raise Exception(f"[{self.role}] Critical failure threshold reached. Last error: {self.last_error}")
                
                error_str = str(e)
                if any(code in error_str for code in ["429", "500", "503", "RESOURCE_EXHAUSTED", "UNAVAILABLE", "INTERNAL"]):
                    sleep_time = None
                    if hasattr(e, 'details') and e.details:
                        import re
                        for detail in e.details:
                            if isinstance(detail, dict) and 'retryDelay' in detail:
                                delay_str = detail['retryDelay']
                                match = re.search(r'([\d\.]+)', delay_str)
                                if match:
                                    sleep_time = float(match.group(1)) + 1.0
                                    break
                    if not sleep_time:
                        import re
                        match = re.search(r'Please retry in ([\d\.]+)s', error_str)
                        if match:
                            sleep_time = float(match.group(1)) + 1.0
                    
                    if not sleep_time:
                        jitter = random.uniform(0, 5)
                        sleep_time = (base_backoff * (1.5 ** retries)) + jitter
                        
                    log_event(self.role, f"API Busy/Error ({error_str}). Retrying in {sleep_time:.1f}s...")
                    time.sleep(sleep_time)
                    retries += 1
                else:
                    raise e
            except Exception as e:
                self.consecutive_failures += 1
                self.last_error = str(e)
                if self.consecutive_failures >= self.max_consecutive_failures:
                    raise Exception(f"[{self.role}] Critical failure threshold reached. Last error: {self.last_error}")
                
                log_event(self.role, f"Unexpected error: {str(e)}. Retrying...")
                time.sleep(5)
                retries += 1
        raise Exception(f"[{self.role}] Failed after {retries} retries. Last error: {self.last_error}")

class ContentGenerator(AgentBase):
    def generate(self, module_title, sub_title, content_context, running_summary=""):
        learning_context = self._get_learning_context()
        
        learning_context_block = ""
        if learning_context:
            learning_context_block = (
                f"### HISTORICAL STYLE GUIDANCE\n"
                f"Avoid these previous mistakes. They have the lowest priority and must never change the lesson subject:\n"
                f"```\n{learning_context}\n```\n\n"
            )

        prompt, self.required_headings = load_prompt("content_generator.md", 
                             theme=self.theme,
                             sub_title=sub_title, 
                             module_title=module_title, 
                             content_context=content_context, 
                             learning_context_block=learning_context_block,
                             running_summary=running_summary)
        return self._run_with_retry(prompt)

class Archivist(AgentBase):
    def compress_submodule(self, content):
        prompt, _ = load_prompt("archivist.md", 
                             theme=self.theme,
                             content=content)
        return self._run_with_retry(prompt)

class Critic(AgentBase):
    def critique(self, draft, content_context):
        prompt, _ = load_prompt("critic.md", 
                             theme=self.theme,
                             content_context=content_context, 
                             draft=draft)
        return self._run_with_retry(prompt)

    def critique_chat(self, chat_session, draft, content_context):
        prompt, _ = load_prompt("critic.md", 
                             theme=self.theme,
                             content_context=content_context, 
                             draft=draft)
        return self._send_message_with_retry(chat_session, prompt)

class Editor(AgentBase):
    def edit(self, draft, feedback, sub_title, content_context):
        learning_context = self._get_learning_context()
        learning_context_block = ""
        if learning_context:
            learning_context_block = (
                f"### HISTORICAL STYLE GUIDANCE\n"
                f"Avoid these previous mistakes. They must never change the lesson subject:\n"
                f"```\n{learning_context}\n```\n\n"
            )
            
        prompt, _ = load_prompt("editor.md", 
                             theme=self.theme,
                             sub_title=sub_title, 
                             content_context=content_context, 
                             feedback=feedback,
                             learning_context_block=learning_context_block,
                             draft=draft)
        return self._run_with_retry(prompt)

    def edit_chat(self, chat_session, draft, feedback, sub_title, content_context):
        learning_context = self._get_learning_context()
        learning_context_block = ""
        if learning_context:
            learning_context_block = (
                f"### HISTORICAL STYLE GUIDANCE\n"
                f"Avoid these previous mistakes. They must never change the lesson subject:\n"
                f"```\n{learning_context}\n```\n\n"
            )
            
        prompt, _ = load_prompt("editor.md", 
                             theme=self.theme,
                             sub_title=sub_title, 
                             content_context=content_context, 
                             feedback=feedback,
                             learning_context_block=learning_context_block,
                             draft=draft)
        return self._send_message_with_retry(chat_session, prompt)

class Librarian(AgentBase):
    def audit_structure(self, full_content, content_context=None):
        prompt, _ = load_prompt("librarian.md", 
                             theme=self.theme,
                             full_content=full_content)
        return self._run_with_retry(prompt)

class InternalLibrarian(AgentBase):
    def audit_draft(self, content):
        prompt, _ = load_prompt("internal_librarian.md", 
                             theme=self.theme,
                             content=content)
        return self._run_with_retry(prompt)

class FactChecker(AgentBase):
    def check_facts(self, content, content_context):
        prompt, _ = load_prompt("fact_checker.md", 
                             theme=self.theme,
                             content_context=content_context,
                             content=content)
        return self._run_with_retry(prompt)


class StyleSynthesizer(AgentBase):
    def __init__(self, model_id="gemini-3.1-flash-lite", max_consecutive_failures=3, theme="default"):
        super().__init__(role="style-synthesizer", model_id=model_id, max_consecutive_failures=max_consecutive_failures, theme=theme)
        self.system_instruction = (
            "You are a professional technical QA manager applying strict NLP compression. "
            "Never use conversational filler."
        )

    def synthesize_rule(self, critique: str, correction: str) -> str:
        prompt, _ = load_prompt("style_synthesizer_rule.md", 
                             theme=self.theme,
                             critique=critique,
                             correction=correction)
        rule = self._run_with_retry(prompt).strip()
        # Clean up any quotes, markdown bullet prefix, or newlines
        rule = rule.replace('"', '').replace("'", "").lstrip("-* ").strip()
        return rule

    def find_duplicate_rule(self, existing_rules: list, new_rule: str) -> str:
        """
        Check if the new_rule is semantically similar to any of the existing_rules.
        Returns the matching rule's exact text if found, or 'NEW' if it doesn't match any.
        """
        if not existing_rules:
            return "NEW"
            
        # Format existing rules for the prompt
        rules_formatted = "\n".join([f"- {r}" for r in existing_rules])
        
        prompt, _ = load_prompt("style_synthesizer_duplicate.md", 
                             theme=self.theme,
                             rules_formatted=rules_formatted,
                             new_rule=new_rule)
        
        response = self._run_with_retry(prompt).strip()
        # Clean up return value
        cleaned_response = response.replace('"', '').replace("'", "").lstrip("-* ").strip()
        
        # Double check if the cleaned response exactly matches one of the existing rules (ignoring case/whitespace)
        for r in existing_rules:
            if r.lower() == cleaned_response.lower():
                return r
        
        return "NEW"

class CurriculumJudgeEval(AgentBase):
    def __init__(self, model_id="gemini-3.1-flash-lite", max_consecutive_failures=3, theme="default"):
        super().__init__(role="curriculum-judge-eval", model_id=model_id, max_consecutive_failures=max_consecutive_failures, theme=theme)
        self.system_instruction = "You are a strict curriculum evaluator. You must return only valid JSON matching the exact schema."
        from src.models.schemas import EvalResult
        self.response_schema = EvalResult

    def evaluate(self, course_name, topic, duration_weeks, outline):
        prompt, _ = load_prompt("eval_curriculum_judge.md", 
                             theme=self.theme,
                             course_name=course_name,
                             topic=topic,
                             duration_weeks=str(duration_weeks),
                             outline=outline)
        return self._run_with_retry(prompt)

class CourseQualityJudgeEval(AgentBase):
    def __init__(self, model_id="gemini-3.1-flash-lite", max_consecutive_failures=3, theme="default"):
        super().__init__(role="course-quality-judge-eval", model_id=model_id, max_consecutive_failures=max_consecutive_failures, theme=theme)
        self.system_instruction = "You are a strict course quality evaluator. You must return only valid JSON matching the exact schema."
        from src.models.schemas import EvalResult
        self.response_schema = EvalResult

    def evaluate(self, compiled_course):
        prompt, _ = load_prompt("eval_course_quality.md", 
                             theme=self.theme,
                             compiled_course=compiled_course)
        return self._run_with_retry(prompt)

