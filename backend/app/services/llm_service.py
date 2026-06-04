from enum import Enum
import anthropic
from app.config import settings


class ModelTier(str, Enum):
    FAST = "fast"
    DEEP = "deep"


class LLMService:
    """Thin wrapper around the Anthropic Messages API.

    The module-level ``llm_service`` singleton is created at import time so that
    dependent modules can access it without explicit injection.  Because of this,
    ``api_key`` defaults to an empty string rather than raising immediately — this
    allows the module to be imported in tests and development environments that do
    not have a real API key configured.  Authentication errors are surfaced at
    call time instead.
    """

    def __init__(self, client=None, fast_model: str = None, deep_model: str = None):
        self._client = client or anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._fast_model = fast_model or settings.anthropic_model_fast
        self._deep_model = deep_model or settings.anthropic_model_deep

    def model_name_for_tier(self, tier: ModelTier) -> str:
        return self._fast_model if tier == ModelTier.FAST else self._deep_model

    def run(self, prompt: str, tier: ModelTier, task_type: str, prompt_version: str) -> str:
        model = self._fast_model if tier == ModelTier.FAST else self._deep_model
        try:
            response = self._client.messages.create(
                model=model,
                max_tokens=4096,  # 4096 tokens ≈ 3000 words, sufficient for scientific abstract-length summaries
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except Exception as e:
            raise RuntimeError(
                f"LLM-Anfrage fehlgeschlagen (Modell: {model}, Aufgabe: {task_type}): {e}"
            ) from e


llm_service = LLMService()
