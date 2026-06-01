from dataclasses import dataclass

from app.ai.types import MessageUnderstanding


@dataclass
class LeadScoreResult:
    fit_score: int
    engagement_score: int
    lead_score: int


def _bound(value: int) -> int:
    return max(0, min(100, value))


def compute_initial_scores(
    understanding: MessageUnderstanding,
    message_count: int,
) -> LeadScoreResult:
    fit = 40
    company_size = understanding.entities.get("company_size")
    if isinstance(company_size, int):
        if company_size >= 200:
            fit += 25
        elif company_size >= 50:
            fit += 20
        elif company_size >= 10:
            fit += 10

    intent_score = 20
    if understanding.intent in {"demo_request", "pricing"}:
        intent_score = 80
    elif understanding.intent in {"comparison", "evaluation"}:
        intent_score = 70
    elif understanding.intent == "support":
        intent_score = 25

    engagement = 25 + min(35, message_count * 7)
    if understanding.urgency == "high":
        engagement += 20
    elif understanding.urgency == "medium":
        engagement += 10

    if understanding.sentiment == "positive":
        engagement += 8
    elif understanding.sentiment == "negative":
        engagement -= 5

    fit_score = _bound(fit)
    engagement_score = _bound(engagement)
    weighted = int((0.4 * fit_score) + (0.3 * engagement_score) + (0.3 * intent_score))

    return LeadScoreResult(
        fit_score=fit_score,
        engagement_score=engagement_score,
        lead_score=_bound(weighted),
    )
