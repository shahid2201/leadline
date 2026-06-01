from dataclasses import dataclass
from typing import Any


@dataclass
class MessageUnderstanding:
    intent: str
    entities: dict[str, Any]
    sentiment: str
    urgency: str
    topics: list[str]
    model: str
    prompt_version: str
    tokens_used: int = 0


def sanitize_understanding(
    raw: dict[str, Any],
    model: str,
    prompt_version: str,
) -> MessageUnderstanding:
    sentiment = str(raw.get("sentiment", "neutral")).lower()
    if sentiment not in {"positive", "neutral", "negative"}:
        sentiment = "neutral"

    urgency = str(raw.get("urgency", "low")).lower()
    if urgency not in {"low", "medium", "high"}:
        urgency = "low"

    topics_raw = raw.get("topics", [])
    topics: list[str] = []
    if isinstance(topics_raw, list):
        topics = [str(item).strip() for item in topics_raw if str(item).strip()]

    entities_raw = raw.get("entities", {})
    entities = entities_raw if isinstance(entities_raw, dict) else {}

    intent = str(raw.get("intent", "unknown")).strip().lower() or "unknown"

    tokens_used = int(raw.get("tokens_used", 0))

    return MessageUnderstanding(
        intent=intent,
        entities=entities,
        sentiment=sentiment,
        urgency=urgency,
        topics=topics,
        model=model,
        prompt_version=prompt_version,
        tokens_used=tokens_used,
    )
