import pytest
import os
import sys
from pathlib import Path

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from verify_themes import run_verification

def test_theme_default():
    """Verify that default theme runs the orchestrator loop without crashes."""
    run_verification("default")

def test_theme_blueprint():
    """Verify that blueprint theme runs the orchestrator loop without crashes."""
    run_verification("blueprint")

def test_theme_beginner_friendly():
    """Verify that beginner_friendly theme runs the orchestrator loop without crashes."""
    run_verification("beginner_friendly")

def test_theme_general():
    """Verify that general theme runs the orchestrator loop without crashes."""
    run_verification("general")

def test_theme_ottolearn():
    """Verify that ottolearn theme runs the orchestrator loop without crashes."""
    run_verification("ottolearn")
