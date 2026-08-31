"""R03-T01 — the contract every LLM provider adapter must satisfy.

Parametrised over EVERY provider in the central registry
(``infrastructure/providers/provider_registry.py``), so registering a new
provider automatically subjects it to the same specification and a provider that
drifts from the canonical shapes fails here.

The contract, in one list:

* construction — the registry builds a real ``Provider`` for every id;
* ``chat()`` — canonical signature, canonical assistant message, streamed text
  delivered through ``on_text``, tool calls normalised to
  ``{"id", "name", "arguments": dict}``, response always closed;
* tool schema translation matches the adapter's wire protocol;
* failures raise ``ProviderError`` — never a bare transport exception;
* ``list_models()`` / ``test_connection()`` report a reason instead of a silent
  empty list;
* telemetry — exactly one ``UsageEvent`` per turn (R03-T06), with the real
  counts when the stream reports them.

Everything runs offline: ``Provider._request`` is replaced by a scripted
transport, so the suite needs no network, no API key and no Qt event loop.
"""

from __future__ import annotations

import pytest
import requests
from cowork_local.infrastructure.providers.provider_registry import (
    BUILTIN_DESCRIPTORS,
    ProviderRegistry,
)
from cowork_local.infrastructure.telemetry import usage_sink
from cowork_local.providers.base import Provider, ProviderError, ToolSpec
from cowork_local.tests.contracts.provider_stubs import (
    EXPECTED_CACHED_TOKENS,
    EXPECTED_INPUT_TOKENS,
    EXPECTED_OUTPUT_TOKENS,
    EXPECTED_TEXT,
    EXPECTED_TOOL_CALL,
    PROTOCOL_FIXTURES,
    FakeStreamResponse,
    ScriptedTransport,
)

# Every provider id in the catalogue — the parametrisation that makes this a
# contract suite rather than a per-adapter unit test.
PROVIDER_IDS = [d.provider_id for d in BUILTIN_DESCRIPTORS]

# Minimal config: enough for any adapter to build a URL and headers offline.
BASE_CONF = {"base_url": "https://gateway.test/v1", "api_key": "test-key"}

SAMPLE_MESSAGES = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Say hello"},
]

SAMPLE_TOOL = ToolSpec(
    name="read_file",
    description="Read a file from disk",
    parameters={"type": "object", "properties": {"path": {"type": "string"}}},
)


@pytest.fixture()
def registry() -> ProviderRegistry:
    """A private registry per test so registrations never leak between tests."""
    return ProviderRegistry(BUILTIN_DESCRIPTORS)


@pytest.fixture()
def collected_usage(monkeypatch) -> usage_sink.InMemoryUsageSink:
    """Swap the process-wide telemetry sink for an in-memory one.

    Restored by monkeypatch after each test, so a contract run never appends to
    the developer's real ``~/.cowork_local/usage/`` files.
    """
    sink = usage_sink.InMemoryUsageSink()
    monkeypatch.setattr(usage_sink, "_sink", usage_sink.CompositeUsageSink([sink]))
    return sink


def _fixtures_for(registry: ProviderRegistry, provider_id: str) -> dict:
    """The stream/model-list script matching this provider's wire protocol."""
    protocol = registry.get(provider_id).wire_protocol.value
    return PROTOCOL_FIXTURES[protocol]


def _build(registry: ProviderRegistry, provider_id: str, transport=None) -> Provider:
    """Build a provider and (optionally) replace its transport with a script."""
    provider = registry.build(provider_id, dict(BASE_CONF))
    if transport is not None:
        # Patch the INSTANCE, not the class: parallel parametrised cases must
        # not see each other's scripted transport.
        provider._request = transport
    return provider


# --------------------------------------------------------------------------- #
# Construction & interface shape
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("provider_id", PROVIDER_IDS)
def test_registry_builds_a_provider_for_every_registered_id(registry, provider_id) -> None:
    """Every catalogued provider must be constructible — a descriptor with no
    working adapter is a broken entry, not a feature flag."""
    provider = _build(registry, provider_id)

    assert isinstance(provider, Provider)
    # The registry fills in the descriptor's default model when config omits it,
    # so a half-configured provider still names a concrete model.
    assert provider.model, f"{provider_id} built without a model id"
    assert provider.describe() == f"{provider.name}:{provider.model}"


@pytest.mark.parametrize("provider_id", PROVIDER_IDS)
def test_chat_signature_is_uniform(registry, provider_id) -> None:
    """All adapters accept the same call, so the agent runtime can swap
    providers without knowing which one it holds."""
    import inspect

    provider = _build(registry, provider_id)
    params = list(inspect.signature(provider.chat).parameters)

    assert params == ["messages", "tools", "on_text", "cancel", "on_reasoning"]


@pytest.mark.parametrize("provider_id", PROVIDER_IDS)
def test_tool_schema_matches_the_wire_protocol(registry, provider_id) -> None:
    """A ToolSpec must translate into the exact shape the endpoint expects."""
    descriptor = registry.get(provider_id)

    if descriptor.wire_protocol.value == "anthropic":
        translated = SAMPLE_TOOL.to_anthropic()
        assert translated["input_schema"] == SAMPLE_TOOL.parameters
        assert translated["name"] == "read_file"
    else:
        translated = SAMPLE_TOOL.to_openai()
        assert translated["type"] == "function"
        assert translated["function"]["parameters"] == SAMPLE_TOOL.parameters


# --------------------------------------------------------------------------- #
# The turn itself
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("provider_id", PROVIDER_IDS)
def test_chat_returns_the_canonical_assistant_message(registry, provider_id, collected_usage) -> None:
    """Whatever the wire format, one turn yields the same canonical result."""
    fixtures = _fixtures_for(registry, provider_id)
    response = FakeStreamResponse(lines=fixtures["stream_lines"]())
    transport = ScriptedTransport([response])
    provider = _build(registry, provider_id, transport)

    streamed: list = []
    result = provider.chat(
        SAMPLE_MESSAGES, tools=[SAMPLE_TOOL], on_text=streamed.append,
    )

    assert result["role"] == "assistant"
    assert result["content"] == EXPECTED_TEXT
    # Text must arrive incrementally, not only in the final message — the chat
    # UI streams from these callbacks.
    assert "".join(streamed) == EXPECTED_TEXT
    assert len(streamed) >= 2
    # Tool calls are normalised: parsed arguments, never the raw JSON fragments.
    assert result["tool_calls"] == [EXPECTED_TOOL_CALL]
    assert response.closed, "provider left the streaming response open"


@pytest.mark.parametrize("provider_id", PROVIDER_IDS)
def test_chat_publishes_exactly_one_usage_event(registry, provider_id, collected_usage) -> None:
    """R03-T06: a turn reports its token usage through the telemetry sink, with
    the server's real counts when the stream carried them."""
    fixtures = _fixtures_for(registry, provider_id)
    transport = ScriptedTransport([FakeStreamResponse(lines=fixtures["stream_lines"]())])
    provider = _build(registry, provider_id, transport)

    provider.chat(SAMPLE_MESSAGES, tools=[SAMPLE_TOOL])

    events = collected_usage.snapshot()
    assert len(events) == 1, "a turn must publish exactly one usage event"
    event = events[0]
    assert event.provider == provider.name
    assert event.model == provider.model
    assert event.input_tokens == EXPECTED_INPUT_TOKENS
    assert event.output_tokens == EXPECTED_OUTPUT_TOKENS
    assert event.cached_tokens == EXPECTED_CACHED_TOKENS
    # Real counts were available, so the event must NOT be flagged as a guess.
    assert event.estimated is False


@pytest.mark.parametrize("provider_id", PROVIDER_IDS)
def test_usage_is_estimated_when_the_stream_reports_none(registry, provider_id, collected_usage) -> None:
    """Gateways that never send usage still produce a dashboard row — clearly
    flagged as an estimate rather than silently recorded as zero."""
    # Only text; no usage block anywhere in the stream.
    silent_stream = ['data: ' + '{"choices": [{"delta": {"content": "hi"}}]}', "data: [DONE]"]
    if registry.get(provider_id).wire_protocol.value == "anthropic":
        silent_stream = [
            'data: {"type": "content_block_start", "index": 0, "content_block": {"type": "text"}}',
            'data: {"type": "content_block_delta", "index": 0,'
            ' "delta": {"type": "text_delta", "text": "hi"}}',
        ]
    transport = ScriptedTransport([FakeStreamResponse(lines=silent_stream)])
    provider = _build(registry, provider_id, transport)

    provider.chat(SAMPLE_MESSAGES)

    events = collected_usage.snapshot()
    assert len(events) == 1
    assert events[0].estimated is True
    # An estimate still has to be a positive number to be worth showing.
    assert events[0].total_tokens > 0


# --------------------------------------------------------------------------- #
# Failure behaviour
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("provider_id", PROVIDER_IDS)
def test_http_error_becomes_provider_error(registry, provider_id, collected_usage) -> None:
    """Callers handle exactly one exception type; adapters must not leak
    transport- or JSON-level errors past their boundary."""
    failing = FakeStreamResponse(status_code=401, body='{"error": {"message": "bad key"}}')
    transport = ScriptedTransport([failing])
    provider = _build(registry, provider_id, transport)

    with pytest.raises(ProviderError):
        provider.chat(SAMPLE_MESSAGES)

    assert failing.closed, "provider left a failed response open"


@pytest.mark.parametrize("provider_id", PROVIDER_IDS)
def test_list_models_and_test_connection_report_a_reason(registry, provider_id) -> None:
    """A failed model load must explain itself: ``last_error`` is what Settings
    shows instead of an unexplained empty dropdown."""
    def _boom(*_args, **_kwargs):
        # A transport failure, i.e. what actually happens when the gateway is
        # unreachable — adapters translate this class of error, not arbitrary
        # programming errors, which must still surface as bugs.
        raise requests.ConnectionError("network down")

    provider = _build(registry, provider_id, _boom)

    models = provider.list_models()

    assert provider.last_error, f"{provider_id} swallowed a model-load failure"
    ok, message = provider.test_connection()
    assert ok is False
    assert message
    # Anthropic answers with a built-in fallback catalogue; a gateway answers
    # with nothing. Both are acceptable — the contract is only that a failure is
    # never reported as success.
    assert isinstance(models, list)


@pytest.mark.parametrize("provider_id", PROVIDER_IDS)
def test_list_models_returns_ids_on_success(registry, provider_id) -> None:
    """The happy path returns plain model-id strings, not raw API objects."""
    fixtures = _fixtures_for(registry, provider_id)
    transport = ScriptedTransport([
        FakeStreamResponse(status_code=200, payload=fixtures["models_payload"]),
    ])
    provider = _build(registry, provider_id, transport)

    models = provider.list_models()

    assert models == fixtures["expected_models"]
    assert provider.last_error == ""
    assert all(isinstance(m, str) for m in models)


@pytest.mark.parametrize("provider_id", PROVIDER_IDS)
def test_strip_think_removes_inline_reasoning(registry, provider_id) -> None:
    """Reasoning must never leak into a final answer, whichever adapter ran."""
    provider = _build(registry, provider_id)

    cleaned = provider.strip_think("<think>secret plan</think>Visible answer")

    assert cleaned == "Visible answer"
