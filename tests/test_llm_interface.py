"""Tests for LLM provider interface and NullLLMProvider."""
from __future__ import annotations

from auditgraph.llm.interface import LLMProvider, LLMResponse, NullLLMProvider


class TestNullLLMProviderProtocol:
    def test_satisfies_llm_provider_protocol(self) -> None:
        provider = NullLLMProvider()
        assert isinstance(provider, LLMProvider)

    def test_complete_returns_llm_response(self) -> None:
        provider = NullLLMProvider()
        response = provider.complete("hello")
        assert isinstance(response, LLMResponse)

    def test_complete_model_is_null(self) -> None:
        provider = NullLLMProvider()
        response = provider.complete("hello")
        assert response.model == "null"

    def test_complete_text_is_empty(self) -> None:
        provider = NullLLMProvider()
        response = provider.complete("hello")
        assert response.text == ""

    def test_complete_does_not_raise_on_empty_prompt(self) -> None:
        provider = NullLLMProvider()
        response = provider.complete("")
        assert response.model == "null"

    def test_complete_does_not_raise_on_large_prompt(self) -> None:
        provider = NullLLMProvider()
        large_prompt = "x" * 10_000_000
        response = provider.complete(large_prompt)
        assert response.model == "null"

    def test_model_name_returns_null(self) -> None:
        provider = NullLLMProvider()
        assert provider.model_name == "null"


class TestLLMResponseMetadata:
    def test_metadata_not_shared_across_instances(self) -> None:
        r1 = LLMResponse(text="a", model="m1")
        r2 = LLMResponse(text="b", model="m2")
        assert r1.metadata is not r2.metadata

    def test_metadata_defaults_to_empty_dict(self) -> None:
        r = LLMResponse(text="", model="null")
        assert r.metadata == {}

    def test_frozen_response_raises_on_mutation(self) -> None:
        r = LLMResponse(text="", model="null")
        try:
            r.text = "changed"  # type: ignore[misc]
            assert False, "Should have raised"
        except AttributeError:
            pass
