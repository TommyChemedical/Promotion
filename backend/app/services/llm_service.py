from enum import Enum
import anthropic
from app.config import settings


class ModelTier(str, Enum):
    FAST = "fast"
    DEEP = "deep"


class LLMService:
    def __init__(self, client=None, fast_model: str = None, deep_model: str = None):
        self._client = client or anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._fast_model = fast_model or settings.anthropic_model_fast
        self._deep_model = deep_model or settings.anthropic_model_deep

    def run(self, prompt: str, tier: ModelTier, task_type: str, prompt_version: str) -> str:
        model = self._fast_model if tier == ModelTier.FAST else self._deep_model
        response = self._client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text


llm_service = LLMService()
