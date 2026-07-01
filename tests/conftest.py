import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture(autouse=True)
def mock_grounding_auditor_by_default(request):
    # Bypass default mock if executing the dedicated auditor test suite
    if "test_grounding_auditor_tdd" in request.node.fspath.strpath:
        yield
    else:
        with patch("src.agents.core.GroundingFaithfulnessAuditor.audit_grounding") as mock_audit:
            mock_audit.return_value = {
                "status": "APPROVED",
                "blockers": [],
                "warnings": [],
                "notes": []
            }
            yield
