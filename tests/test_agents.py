import os
import time
import random
import pytest
from unittest.mock import MagicMock
from dotenv import load_dotenv

# Load env variables
load_dotenv()

class MockAgent:
    """A simple mock class to test the retry logic without needing the real API."""
    def __init__(self, role):
        self.role = role
        self.call_count = 0

    def _run_with_retry(self, prompt):
        retries = 0
        base_backoff = 0.01 
        while retries < 5:
            try:
                self.call_count += 1
                # Simulate a 503 error on the first two attempts
                if self.call_count < 3:
                    raise Exception("503 UNAVAILABLE: Server Busy")
                return "success"
            except Exception as e:
                error_str = str(e)
                if "503" in error_str or "429" in error_str or "500" in error_str:
                    retries += 1
                    time.sleep(base_backoff)
                else:
                    raise e
        return "failed"

def test_retry_logic_on_api_error():
    """Verify that the agent retries when a 503 error occurs."""
    agent = MockAgent("Mock")
    result = agent._run_with_retry("test prompt")
    
    assert result == "success"
    assert agent.call_count == 3

def test_agent_initialization_logic():
    """Basic check to ensure role and setup works."""
    from src.agents.core import ContentGenerator
    gen = ContentGenerator("Test Generator")
    assert gen.role == "Test Generator"
