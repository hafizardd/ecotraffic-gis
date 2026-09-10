import json

import httpx
import pytest

from data_pipeline.activities.llm import LLMError, LLMResponseError, OpenRouterLLMClient
from data_pipeline.activities.schemas import SemanticExtraction


def _response(request, status=200, *, content=None):
    payload = content if content is not None else SemanticExtraction().model_dump(mode="json")
    return httpx.Response(
        status,
        request=request,
        headers={"x-request-id": "request-test"},
        json={
            "choices": [{"message": {"content": json.dumps(payload)}}],
            "usage": {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5},
        },
    )


def _client(handler, *, max_retries=2):
    return OpenRouterLLMClient(
        api_key="test-key",
        base_url="https://openrouter.test/api/v1",
        model="test/model",
        max_retries=max_retries,
        backoff_base=0,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        sleep=lambda _: None,
    )


def _extract(client):
    return client.extract_structured(system_prompt="system", user_prompt="user", response_schema={"type": "object"})


def test_successful_openrouter_response_and_token_metrics():
    client = _client(lambda request: _response(request))
    assert _extract(client)["usage"]["passenger_level"] == "unknown"
    assert client.last_request_id == "request-test"
    assert client.metrics.successful_calls == 1
    assert client.metrics.total_tokens == 5


@pytest.mark.parametrize("status", [401, 402, 403])
def test_non_retryable_openrouter_statuses_are_not_retried(status):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, request=request, json={"error": "no"})

    client = _client(handler)
    with pytest.raises(LLMError) as exc:
        _extract(client)
    assert exc.value.status_code == status
    assert len(calls) == 1
    assert client.metrics.retry_count == 0


@pytest.mark.parametrize("status", [408, 429, 500, 502, 503])
def test_transient_openrouter_statuses_use_bounded_retries(status):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, request=request, json={"error": "later"})

    client = _client(handler, max_retries=2)
    with pytest.raises(LLMError):
        _extract(client)
    assert len(calls) == 3
    assert client.metrics.retry_count == 2
    assert client.metrics.rate_limit_errors == (3 if status == 429 else 0)


def test_timeout_is_retried_then_reported():
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout("timed out", request=request)

    client = _client(handler, max_retries=1)
    with pytest.raises(LLMError, match="timed out"):
        _extract(client)
    assert len(calls) == 2
    assert client.metrics.retry_count == 1


def test_malformed_json_is_rejected():
    def handler(request):
        return httpx.Response(200, request=request, json={"choices": [{"message": {"content": "not-json"}}]})

    with pytest.raises(LLMResponseError, match="malformed JSON"):
        _extract(_client(handler))


def test_empty_response_is_rejected():
    def handler(request):
        return httpx.Response(200, request=request, json={"choices": [{"message": {"content": ""}}]})

    with pytest.raises(LLMResponseError, match="empty response"):
        _extract(_client(handler))


def test_unsupported_structured_output_falls_back_without_switching_model():
    bodies = []

    def handler(request):
        bodies.append(json.loads(request.content))
        if len(bodies) == 1:
            return httpx.Response(400, request=request, json={"error": "response_format unsupported"})
        return _response(request)

    client = _client(handler)
    _extract(client)
    assert bodies[0]["response_format"]["type"] == "json_schema"
    assert bodies[1]["response_format"]["type"] == "json_object"
    assert {body["model"] for body in bodies} == {"test/model"}
    assert client.metrics.structured_output_fallbacks == 1


def test_unrelated_bad_request_does_not_trigger_format_fallback():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(400, request=request, json={"error": "invalid model input"})

    with pytest.raises(LLMError):
        _extract(_client(handler))
    assert len(calls) == 1
