import pytest

from app.ai.orchestrator import AIOrchestrator


@pytest.mark.ai_regression
@pytest.mark.parametrize(
    ("content", "expected_intent", "expected_urgency"),
    [
        ("Need pricing for 50 users this month", "pricing", "medium"),
        ("Book a demo asap for our team", "demo_request", "high"),
        ("We have a support issue that is urgent", "support", "high"),
    ],
)
def test_ai_fallback_regression(content: str, expected_intent: str, expected_urgency: str) -> None:
    orchestrator = AIOrchestrator()
    analyzed = orchestrator._fallback_analysis(content)
    assert analyzed["intent"] == expected_intent
    assert analyzed["urgency"] == expected_urgency
