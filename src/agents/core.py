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

class AgentBase:
    """Base class for all agents with built-in error handling, pacing, and learning."""
    def __init__(self, role, model_id="gemini-3.1-flash-lite", max_consecutive_failures=3):
        self.role = role
        self.model_id = model_id
        self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        self.system_instruction = f"You are an expert {role} in a high-end textbook production team. Your output must be academic, precise, and free of any conversational fluff."
        self.tokens_used = 0
        self.consecutive_failures = 0
        self.max_consecutive_failures = max_consecutive_failures
        self.last_error = ""

    def _get_learning_context(self):
        """Fetget the most recent lessons learned to inject into the prompt."""
        lessons = get_learned_lessons()
        if lessons:
            return f"\n\n### IMPORTANT: PREVIOUS LESSONS LEARNED (DO NOT REPEAT THESE ERRORS):\n{lessons}"
        return ""

    def _run_with_retry(self, prompt):
        retries = 0
        base_backoff = 10 

        while retries < 10:
            try:
                # Inject learned lessons into the prompt
                enriched_prompt = prompt + self._get_learning_context()
                
                response = self.client.models.generate_content(
                    model=self.model_id,
                    contents=enriched_prompt,
                    config={"system_instruction": self.system_instruction}
                )
                # Track token usage if available in the response
                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    self.tokens_used += response.usage_metadata.total_token_count
                
                # Reset consecutive failures on success
                self.consecutive_failures = 0
                return response.text
            except (errors.ServerError, errors.APIError) as e:
                self.consecutive_failures += 1
                self.last_error = str(e)
                
                if self.consecutive_failures >= self.max_consecutive_failures:
                    raise Exception(f"[{self.role}] Critical failure threshold reached ({self.consecutive_failures} consecutive errors). Last error: {self.last_error}")
                
                error_str = str(e)
                if any(code in error_str for code in ["429", "500", "503", "RESOURCE_EXHAUSTED", "UNAVAILABLE", "INTERNAL"]):
                    jitter = random.uniform(0, 5)
                    sleep_time = (base_backoff * (1.5 ** retries)) + jitter
                    log_event(self.role, f"API Busy/Error ({error_str}). Retrying in {sleep_time:.1f}s...")
                    time.sleep(sleep_time)
                    retries += 1
                else:
                    raise e
            except Exception as e:
                # Non-API errors (like parsing errors) should also be logged and retried if they are transient
                self.consecutive_failures += 1
                self.last_error = str(e)
                if self.consecutive_failures >= self.max_consecutive_failures:
                    raise Exception(f"[{self.role}] Critical failure threshold reached ({self.consecutive_failures} consecutive errors). Last error: {self.last_error}")
                
                log_event(self.role, f"Unexpected error: {str(e)}. Retrying...")
                time.sleep(5)
                retries += 1
        raise Exception(f"[{self.role}] Failed after {retries} retries. Last error: {self.last_error}")

class ContentGenerator(AgentBase):
    def generate(self, module_title, sub_title):
        prompt = (
            f"Write a comprehensive, academic lesson for the submodule '{sub_title}' within the module '{module_title}'.\n\n"
            "Follow this exact structure:\n"
            "### Introduction\n(Define the topic and its importance in the context of data science/programming.)\n"
            "### Core Concepts\n(Deep dive into the technical theory. Use precise terminology.)\n"
            "### Practical Implementation\n(Provide a clear, production-ready Python code example with comments.)\n"
            "### Summary and Key Takeaways\n(Summarize the most critical points for a student to remember.)\n\n"
            "CRITICAL: Use strictly markdown. DO NOT include any top-level (#) or second-level (##) headers. "
            "Start directly with the ### headers. Do not include any conversational filler."
        )
        return self._run_with_retry(prompt)

class Critic(AgentBase):
    def critique(self, draft):
        prompt = (
            "Critique the following textbook content for: 1. Technical accuracy. 2. Academic tone. 3. Depth of explanation.\n"
            "If the content is perfect, return only the word 'APPROVED'. If it needs changes, provide a precise, bulleted list of required improvements.\n\n"
            f"CONTENT:\n{draft}"
        )
        return self._run_with_retry(prompt)

class Editor(AgentBase):
    def edit(self, draft, feedback):
        prompt = (
            "You are a professional textbook editor. Revise the provided draft according to the critique below. "
            "Maintain the high academic tone and ensure all technical concepts are clearly explained.\n\n"
            f"CRITIQUE:\n{feedback}\n\n"
            f"ORIGINAL DRAFT:\n{draft}"
        )
        return self._run_with_retry(prompt)

class Librarian(AgentBase):
    def audit_structure(self, full_content):
        prompt = (
            "You are a structural editor (Librarian). Review the following Markdown content for structural integrity:\n"
            "1. Are the headers correctly nested (### within ##, ## within #)?\n"
            "2. Is the Table of Contents aligned with the content structure?\n"
            "3. Are there any orphaned headers or broken Markdown links?\n\n"
            "If the structure is perfect, return only 'APPROVED'. If not, provide specific structural fixes.\n\n"
            f"CONTENT:\n{full_content}"
        )
        return self._run_with_retry(prompt)

class FactChecker(AgentBase):
    def check_facts(self, content):
        prompt = (
            "You are a professional technical fact-checker. Your goal is to identify any factual inaccuracies, "
            "technical hallucinations, or incorrect code snippets in the provided text.\n\n"
            "If the content is 100% factually correct, return only the word 'APPROVED'. "
            "If you find errors, provide a precise, bulleted list of the errors and the correct information.\n\n"
            f"CONTENT:\n{content}"
        )
        return self._run_with_retry(prompt)
