"""An unparseable response is a sampling artifact, so the same model is re-rolled once."""

import asyncio

import pytest

from pr_agent.algo.pr_processing import _get_all_models, retry_with_fallback_models
from pr_agent.algo.utils import ModelPredictionParseError
from pr_agent.config_loader import get_settings


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def _single_model():
    get_settings().set("config.model", "model-a")
    get_settings().set("config.fallback_models", [])
    get_settings().set("config.parse_failure_retries", 1)


def test_parse_failure_retries_the_same_model():
    calls = []

    async def f(model):
        calls.append(model)
        if len(calls) == 1:
            raise ModelPredictionParseError("unparseable")
        return "ok"

    assert _run(retry_with_fallback_models(f)) == "ok"
    assert calls == ["model-a", "model-a"]


def test_parse_failures_are_bounded_by_the_retry_budget():
    calls = []

    async def f(model):
        calls.append(model)
        raise ModelPredictionParseError("unparseable")

    with pytest.raises(Exception, match="Failed to generate prediction with any model"):
        _run(retry_with_fallback_models(f))
    assert calls == ["model-a", "model-a"]  # one initial attempt + one retry


def test_other_errors_are_not_retried_on_the_same_model():
    calls = []

    async def f(model):
        calls.append(model)
        raise RuntimeError("AuthenticationError")

    with pytest.raises(Exception, match="AuthenticationError"):
        _run(retry_with_fallback_models(f))
    assert calls == ["model-a"]


def test_retries_can_be_disabled():
    get_settings().set("config.parse_failure_retries", 0)
    calls = []

    async def f(model):
        calls.append(model)
        raise ModelPredictionParseError("unparseable")

    with pytest.raises(Exception):
        _run(retry_with_fallback_models(f))
    assert calls == ["model-a"]


def test_parse_failure_falls_through_to_the_fallback_model():
    get_settings().set("config.fallback_models", ["model-b"])
    calls = []

    async def f(model):
        calls.append(model)
        if model == "model-a":
            raise ModelPredictionParseError("unparseable")
        return "ok"

    assert _run(retry_with_fallback_models(f)) == "ok"
    assert calls == ["model-a", "model-a", "model-b"]


def test_unparseable_suggestions_raise_a_parse_error_not_a_type_error():
    # a TypeError here would be indistinguishable from an auth failure and would not be retried
    from pr_agent.tools.pr_code_suggestions import PRCodeSuggestions

    for response in ("", "not: [valid", "some prose, not yaml at all"):
        with pytest.raises(ModelPredictionParseError):
            PRCodeSuggestions._prepare_pr_code_suggestions(object(), response)


def test_empty_fallback_models_string_does_not_create_a_blank_model():
    # the 'fallback_models' action input is an empty string when unset
    get_settings().set("config.fallback_models", "")
    assert _get_all_models() == ["model-a"]
