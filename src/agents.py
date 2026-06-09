import os
import time
import random
from google import genai
from google.genai import errors
from dotenv import load_dotenv

# Load env variables
load_dotenv()

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
MODEL_ID = "gemini-3.1-flash-lite"

class AgentBase:
    """Base class for all agents with built-in error handling and pacing."""
    def __init__(self, role, model_id="gemini-3.1-flash-lite"):
        self.role = role
        self.model_id = model_id
        self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        self.system_instruction = f"You are an expert {role} in a high-end textbook production team. Your output must be academic, precise, and free of any conversational fluff."

    def _run_with_retry(self, prompt):
        retries = 0
        base_backoff = 10 

        while retries < 10:
            try:
                return self.client.models.generate_content(
                    model=self.model_id,
                    contents=prompt,
                    config={"system_instruction": self.system_instruction}
                ).text
            except (errors.ServerError, errors.APIError) as e:
                error_str = str(e)
                if any(code in error_str for code in ["429", "500", "503", "RESOURCE_EXHAUSTED", "UNAVAILABLE", "INTERNAL"]):
                    jitter = random.uniform(0, 5)
                    sleep_time = (base_backoff * (1.5 ** retries)) + jitter
                    print(f"[{self.role}] API Busy/Error. Retrying in {sleep_time:.1f}s...")
                    time.sleep(sleep_time)
                    retries += 1
                else:
                    raise e
        raise Exception(f"[{self.role}] Failed after {retries} retries.")

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
