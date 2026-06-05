import pytest
from unittest.mock import MagicMock
from app.services.llm_service import LLMService, ModelTier


@pytest.fixture
def mock_client():
    client = MagicMock()
    message = MagicMock()
    message.content = [MagicMock(text='{"result": "test output"}')]
    client.messages.create.return_value = message
    return client


def test_fast_tier_uses_fast_model(mock_client):
    svc = LLMService(client=mock_client, fast_model="haiku-test", deep_model="sonnet-test")
    svc.run("prompt text", ModelTier.FAST, task_type="tags", prompt_version="tags_v1")
    kwargs = mock_client.messages.create.call_args.kwargs
    assert kwargs["model"] == "haiku-test"


def test_deep_tier_uses_deep_model(mock_client):
    svc = LLMService(client=mock_client, fast_model="haiku-test", deep_model="sonnet-test")
    svc.run("prompt text", ModelTier.DEEP, task_type="summarize", prompt_version="summary_v1")
    kwargs = mock_client.messages.create.call_args.kwargs
    assert kwargs["model"] == "sonnet-test"


def test_run_returns_text_content(mock_client):
    from app.services.llm_service import LLMResult
    svc = LLMService(client=mock_client, fast_model="haiku-test", deep_model="sonnet-test")
    result = svc.run("prompt text", ModelTier.DEEP, task_type="summarize", prompt_version="summary_v1")
    assert isinstance(result, LLMResult)
    assert result.text == '{"result": "test output"}'


def test_run_sends_correct_message_structure(mock_client):
    svc = LLMService(client=mock_client, fast_model="haiku-test", deep_model="sonnet-test")
    svc.run("my prompt", ModelTier.FAST, task_type="tags", prompt_version="tags_v1")
    kwargs = mock_client.messages.create.call_args.kwargs
    assert kwargs["messages"] == [{"role": "user", "content": "my prompt"}]
    assert kwargs["max_tokens"] >= 1024


def test_run_wraps_api_errors(mock_client):
    mock_client.messages.create.side_effect = Exception("rate limit")
    svc = LLMService(client=mock_client, fast_model="haiku-test", deep_model="sonnet-test")
    with pytest.raises(RuntimeError, match="LLM-Anfrage fehlgeschlagen"):
        svc.run("prompt", ModelTier.FAST, task_type="tags", prompt_version="tags_v1")


def test_llm_service_module_level_instance_exists():
    from app.services.llm_service import llm_service
    assert llm_service is not None
    assert isinstance(llm_service, LLMService)


def test_model_name_for_tier(mock_client):
    svc = LLMService(client=mock_client, fast_model="haiku-test", deep_model="sonnet-test")
    assert svc.model_name_for_tier(ModelTier.FAST) == "haiku-test"
    assert svc.model_name_for_tier(ModelTier.DEEP) == "sonnet-test"
