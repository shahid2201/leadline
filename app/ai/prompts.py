from dataclasses import dataclass


@dataclass(frozen=True)
class PromptTemplate:
    version: str
    system: str
    user_template: str


PROMPTS: dict[str, PromptTemplate] = {
    "v1": PromptTemplate(
        version="v1",
        system=(
            "You are Lead Line AI. Extract structured buyer signals from visitor messages. "
            "Return compact JSON with keys: intent, entities, sentiment, urgency, topics."
        ),
        user_template=(
            "Analyze this visitor message and return strict JSON only.\n"
            "Message: {message}\n"
            "Rules:\n"
            "- intent: short snake_case label\n"
            "- entities: object with normalized keys and primitive values\n"
            "- sentiment: one of positive|neutral|negative\n"
            "- urgency: one of low|medium|high\n"
            "- topics: array of short strings"
        ),
    )
}


def get_prompt(version: str) -> PromptTemplate:
    return PROMPTS.get(version, PROMPTS["v1"])
