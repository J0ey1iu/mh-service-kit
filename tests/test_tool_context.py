"""Tests for the tool-service side of the context protocol.

Covers ToolContext.from_dict parsing and executor body construction
(no network involved).
"""

from mh_service_kit.context import ToolContext
from mh_service_kit.sse.tool_executor import SSEToolExecutor
from minimal_harness.types import RemoteToolBinding


def test_from_dict_parses_known_fields():
    tc = ToolContext.from_dict(
        {
            "user_id": "u-1",
            "username": "alice",
            "roles": ["admin", "member"],
            "extra_data": {"tenant": "t-1"},
            "trace_id": "tr-1",
            "locale": "en",
            "scenario_id": "s-1",
            "agent_name": "triage",
            "correlation_id": "c-1",
        },
        headers={"authorization": "Bearer x"},
    )
    assert tc.user_id == "u-1"
    assert tc.username == "alice"
    assert tc.roles == ["admin", "member"]
    assert tc.extra_data == {"tenant": "t-1"}
    assert tc.trace_id == "tr-1"
    assert tc.locale == "en"
    assert tc.scenario_id == "s-1"
    assert tc.agent_name == "triage"
    assert tc.correlation_id == "c-1"
    assert tc.headers["authorization"] == "Bearer x"
    assert tc.extra == {}


def test_from_dict_unknown_keys_land_in_extra():
    tc = ToolContext.from_dict({"user_id": "u-1", "future_field": 42})
    assert tc.user_id == "u-1"
    assert tc.extra == {"future_field": 42}


def test_from_dict_empty_context_is_header_only():
    tc = ToolContext.from_dict(None, headers={"cookie": "a=b"})
    assert tc.user_id == ""
    assert tc.roles == []
    assert tc.headers == {"cookie": "a=b"}


async def test_executor_body_merges_context():
    async def provider() -> dict:
        return {"user_id": "u-1", "locale": "en"}

    executor = SSEToolExecutor(
        RemoteToolBinding(url="http://example.invalid/tool", context_provider=provider)
    )
    body = await executor._body(
        {"x": 1},
        {"type": "function", "id": "c-1", "function": {"name": "t", "arguments": "{}"}},
    )
    assert body["args"] == {"x": 1}
    assert body["tool_call"]["id"] == "c-1"
    assert body["context"] == {"user_id": "u-1", "locale": "en"}


async def test_executor_body_omits_context_when_empty():
    async def empty_provider() -> dict:
        return {}

    for binding in (
        RemoteToolBinding(url="http://example.invalid/tool", context_provider=None),
        RemoteToolBinding(
            url="http://example.invalid/tool", context_provider=empty_provider
        ),
    ):
        executor = SSEToolExecutor(binding)
        body = await executor._body(
            {"x": 1},
            {
                "type": "function",
                "id": "c-1",
                "function": {"name": "t", "arguments": "{}"},
            },
        )
        assert "context" not in body
        assert body["args"] == {"x": 1}
