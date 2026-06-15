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
    def __init__(self, role, model_id="gemini-3.1-flash-lite", max_consecutive_failures=3):
        self.role = role
        self.model_id = model_id
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

    def _run_with_retry(self, prompt):
        from src.utils.logger import log_event
        log_event(self.role, f"Running LLM request... (Prompt length: {len(prompt)} characters)")
        
        retries = 0
        base_backoff = 10 

        while retries < 10:
            # Pacing / Rate limiting check before API call
            estimated_tokens = len(prompt) // 3
            rate_limiter.wait_if_needed(estimated_tokens)

            try:
                response = self.client.models.generate_content(
                    model=self.model_id,
                    contents=prompt,
                    config={"system_instruction": self.system_instruction}
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
                
                from src.utils.logger import log_event
                log_event(self.role, f"Received Output:\n{result_text}\n")
                
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

class ContentGenerator(AgentBase):
    def generate(self, module_title, sub_title, content_context):
        learning_context = self._get_learning_context()
        
        learning_context_block = ""
        if learning_context:
            learning_context_block = (
                f"### HISTORICAL STYLE GUIDANCE\n"
                f"Avoid these previous mistakes. They have the lowest priority and must never change the lesson subject:\n"
                f"```\n{learning_context}\n```\n\n"
            )

        prompt = load_prompt("content_generator.md", 
                             sub_title=sub_title, 
                             module_title=module_title, 
                             content_context=content_context, 
                             learning_context_block=learning_context_block)
        return self._run_with_retry(prompt)

class Critic(AgentBase):
    def critique(self, draft, content_context):
        prompt = load_prompt("critic.md", 
                             content_context=content_context, 
                             draft=draft)
        return self._run_with_retry(prompt)

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
            
        prompt = load_prompt("editor.md", 
                             sub_title=sub_title, 
                             content_context=content_context, 
                             feedback=feedback,
                             learning_context_block=learning_context_block,
                             draft=draft)
        return self._run_with_retry(prompt)

class Librarian(AgentBase):
    def audit_structure(self, full_content, content_context=None):
        prompt = load_prompt("librarian.md", 
                             full_content=full_content)
        return self._run_with_retry(prompt)

class InternalLibrarian(AgentBase):
    def audit_draft(self, content):
        prompt = load_prompt("internal_librarian.md", 
                             content=content)
        return self._run_with_retry(prompt)

class FactChecker(AgentBase):
    def check_facts(self, content, content_context):
        prompt = load_prompt("fact_checker.md", 
                             content_context=content_context,
                             content=content)
        return self._run_with_retry(prompt)


class StyleSynthesizer(AgentBase):
    def __init__(self, model_id="gemini-3.1-flash-lite", max_consecutive_failures=3):
        super().__init__(role="style-synthesizer", model_id=model_id, max_consecutive_failures=max_consecutive_failures)
        self.system_instruction = (
            "You are a professional technical QA manager applying strict NLP compression. "
            "Never use conversational filler."
        )

    def synthesize_rule(self, critique: str, correction: str) -> str:
        prompt = load_prompt("style_synthesizer_rule.md", 
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
        
        prompt = load_prompt("style_synthesizer_duplicate.md", 
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


