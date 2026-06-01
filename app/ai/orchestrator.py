import json
import logging
import re
from typing import Any

from openai import AsyncOpenAI

from app.ai.cache import AIResultCache
from app.ai.prompts import get_prompt
from app.ai.types import MessageUnderstanding, sanitize_understanding
from app.core.config import get_settings
from app.observability.metrics import ai_calls_total
from app.observability.tracing import traced_span

logger = logging.getLogger(__name__)


class AIOrchestrator:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.cache = AIResultCache(
            redis_url=self.settings.redis_url,
            ttl_seconds=self.settings.ai_cache_ttl_seconds,
        )
        self.client: AsyncOpenAI | None = None
        if self.settings.openai_api_key:
            self.client = AsyncOpenAI(api_key=self.settings.openai_api_key)

    def _select_model(self, content: str) -> str:
        if len(content) > 350:
            return self.settings.openai_model_full
        return self.settings.openai_model_mini

    def _cache_key(self, tenant_id: str, message_id: str, prompt_version: str, model: str) -> str:
        return f"ai:message:{tenant_id}:{message_id}:{prompt_version}:{model}"

    async def analyze_message(
        self,
        tenant_id: str,
        message_id: str,
        content: str,
    ) -> MessageUnderstanding:
        with traced_span("ai.analyze_message", {"tenant.id": tenant_id, "message.id": message_id}):
            prompt_version = self.settings.ai_prompt_version
            model = self._select_model(content)
            cache_key = self._cache_key(tenant_id, message_id, prompt_version, model)

            cached = await self.cache.get(cache_key)
            if cached:
                ai_calls_total.labels(model=model, outcome="cache_hit").inc()
                return sanitize_understanding(cached, model=model, prompt_version=prompt_version)

            raw: dict[str, Any]
            if self.client:
                raw = await self._analyze_with_openai(
                    content=content,
                    model=model,
                    prompt_version=prompt_version,
                )
                ai_calls_total.labels(model=model, outcome="openai").inc()
            else:
                raw = self._fallback_analysis(content)
                ai_calls_total.labels(model=model, outcome="fallback_no_client").inc()

            await self.cache.set(cache_key, raw)
            return sanitize_understanding(raw, model=model, prompt_version=prompt_version)

    async def _analyze_with_openai(
        self,
        content: str,
        model: str,
        prompt_version: str,
    ) -> dict[str, Any]:
        with traced_span(
            "ai.openai_call",
            {"ai.model": model, "ai.prompt_version": prompt_version},
        ):
            prompt = get_prompt(prompt_version)
            try:
                response = await self.client.chat.completions.create(  # type: ignore[union-attr]
                    model=model,
                    response_format={"type": "json_object"},
                    temperature=0.1,
                    messages=[
                        {"role": "system", "content": prompt.system},
                        {"role": "user", "content": prompt.user_template.format(message=content)},
                    ],
                )
                text = response.choices[0].message.content or "{}"
                parsed = json.loads(text)
                if isinstance(parsed, dict):
                    return parsed
                ai_calls_total.labels(model=model, outcome="fallback_parse").inc()
                return self._fallback_analysis(content)
            except Exception:  # noqa: BLE001
                logger.exception("OpenAI analysis failed, falling back to heuristic mode")
                ai_calls_total.labels(model=model, outcome="fallback_error").inc()
                return self._fallback_analysis(content)

    def _fallback_analysis(self, content: str) -> dict[str, Any]:
        lowered = content.lower()

        intent = "general"
        if any(token in lowered for token in ["price", "pricing", "cost"]):
            intent = "pricing"
        elif any(token in lowered for token in ["demo", "book call", "meeting"]):
            intent = "demo_request"
        elif any(token in lowered for token in ["help", "issue", "problem", "support"]):
            intent = "support"

        urgency = "low"
        if any(token in lowered for token in ["today", "urgent", "asap", "this week"]):
            urgency = "high"
        elif any(token in lowered for token in ["soon", "this month", "next week"]):
            urgency = "medium"

        sentiment = "neutral"
        if any(token in lowered for token in ["great", "love", "excellent", "interested"]):
            sentiment = "positive"
        elif any(token in lowered for token in ["bad", "frustrated", "angry", "terrible"]):
            sentiment = "negative"

        entities: dict[str, Any] = {}
        size_match = re.search(r"(\d{1,4})\s*(person|people|employees|seats|users)", lowered)
        if size_match:
            entities["company_size"] = int(size_match.group(1))

        money_match = re.search(r"\$\s*(\d+[\d,]*)", lowered)
        if money_match:
            entities["budget"] = money_match.group(1).replace(",", "")

        topics: list[str] = []
        if intent != "general":
            topics.append(intent)
        if "integration" in lowered:
            topics.append("integration")
        if "team" in lowered:
            topics.append("team")

        return {
            "intent": intent,
            "entities": entities,
            "sentiment": sentiment,
            "urgency": urgency,
            "topics": topics,
        }
