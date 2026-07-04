import sys
from types import SimpleNamespace

import pytest

from src.config import Config, LLMConfig
from src.understanding.llm_provider import OpenAILLMProvider, get_llm_provider


class FakeResponses:
    def __init__(self, output_text: str):
        self.output_text = output_text
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_text=self.output_text)


def make_provider(output_text: str = "hello"):
    responses = FakeResponses(output_text)
    client = SimpleNamespace(responses=responses)
    config = LLMConfig(provider="openai", model="gpt-test", max_tokens=321)
    return OpenAILLMProvider(config, client=client), responses


def test_factory_returns_openai_provider():
    config = Config(llm=LLMConfig(provider="openai", model="gpt-test"))
    assert isinstance(get_llm_provider(config), OpenAILLMProvider)


def test_default_config_uses_openai_provider():
    config = Config()
    assert config.llm.provider == "openai"
    assert config.llm.model == "gpt-5.4-mini"
    assert isinstance(get_llm_provider(config), OpenAILLMProvider)


def test_generate_uses_responses_api_with_system_instructions():
    provider, responses = make_provider("generated text")

    result = provider.generate("user prompt", "system prompt")

    assert result == "generated text"
    assert responses.calls == [{
        "model": "gpt-test",
        "input": "user prompt",
        "instructions": "system prompt",
        "max_output_tokens": 321,
    }]


def test_generate_json_parses_object_response():
    provider, responses = make_provider('{"title": "Test"}')

    result = provider.generate_json("make json", "be concise")

    assert result == {"title": "Test"}
    assert "valid JSON object only" in responses.calls[0]["input"]


def test_generate_json_rejects_invalid_json():
    provider, _ = make_provider("not json")

    with pytest.raises(ValueError, match="invalid JSON"):
        provider.generate_json("make json")


def test_generate_rejects_empty_output():
    provider, _ = make_provider("")

    with pytest.raises(ValueError, match="empty response"):
        provider.generate("hello")


def test_client_loads_dotenv_before_openai_initialization(monkeypatch):
    events = []
    fake_client = SimpleNamespace()
    monkeypatch.setitem(
        sys.modules,
        "dotenv",
        SimpleNamespace(load_dotenv=lambda: events.append("dotenv")),
    )
    monkeypatch.setitem(
        sys.modules,
        "openai",
        SimpleNamespace(OpenAI=lambda: events.append("openai") or fake_client),
    )
    provider = OpenAILLMProvider(LLMConfig(provider="openai", model="gpt-test"))

    assert provider.client is fake_client
    assert events == ["dotenv", "openai"]
