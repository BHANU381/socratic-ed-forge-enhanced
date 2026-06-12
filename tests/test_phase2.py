import os
import json
import time
import pytest
from src.agents.core import StyleSynthesizer, AgentBase
from src.utils.rate_limiter import RateLimiter
from src.utils.learning_engine import save_style_guide_rule_internal, STYLE_GUIDE_FILE

def test_rate_limiter_pacing():
    # Test that the rate limiter correctly paces requests when limit is reached
    limiter = RateLimiter(rpm_limit=2, tpm_limit=1000)
    
    # First request
    limiter.wait_if_needed(100)
    limiter.record_request(100)
    
    # Second request
    limiter.wait_if_needed(100)
    limiter.record_request(100)
    
    # Third request: mock the history timestamps to speed up testing
    # oldest is 59.5 seconds ago, newest is 59.0 seconds ago
    limiter.history = [(time.time() - 59.5, 100), (time.time() - 59.0, 100)]
    
    t_before = time.time()
    limiter.wait_if_needed(100)
    t_after = time.time()
    
    # It should have slept for around 0.5 - 0.7 seconds (60 - 59.5 + 0.1)
    elapsed = t_after - t_before
    assert elapsed >= 0.4

def test_style_synthesizer_mock(monkeypatch):
    # Mock _run_with_retry of StyleSynthesizer to return a static rule
    synthesizer = StyleSynthesizer()
    
    monkeypatch.setattr(AgentBase, "_run_with_retry", lambda self, prompt: "Ensure all code imports numpy as np.")
    
    rule = synthesizer.synthesize_rule("Use numpy import", "import numpy as np")
    assert rule == "Ensure all code imports numpy as np."

def test_semantic_deduplication(monkeypatch):
    synthesizer = StyleSynthesizer()
    
    # Mock find_duplicate_rule behavior
    monkeypatch.setattr(StyleSynthesizer, "find_duplicate_rule", lambda self, existing, new: "Ensure numpy is imported as np." if any("numpy" in x.lower() for x in existing) else "NEW")
    
    # Clean file first
    if os.path.exists(STYLE_GUIDE_FILE):
        try:
            os.remove(STYLE_GUIDE_FILE)
        except:
            pass
            
    # 1. Add new rule
    save_style_guide_rule_internal("Ensure numpy is imported as np.", synthesizer)
    
    with open(STYLE_GUIDE_FILE, 'r') as f:
        data = json.load(f)
    assert len(data["rules"]) == 1
    assert data["rules"][0]["text"] == "Ensure numpy is imported as np."
    assert data["rules"][0]["count"] == 1
    
    # 2. Add duplicate rule
    save_style_guide_rule_internal("Make sure numpy imports as np.", synthesizer)
    
    with open(STYLE_GUIDE_FILE, 'r') as f:
        data = json.load(f)
    assert len(data["rules"]) == 1
    assert data["rules"][0]["count"] == 2
