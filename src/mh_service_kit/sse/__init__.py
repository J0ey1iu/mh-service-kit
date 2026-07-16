"""SSE/HTTP wire-protocol implementations for service-mode consumers.

The framework's :class:`minimal_harness.tool.remote.RemoteToolExecutor`
Protocol is a framework primitive. The concrete SSE-over-HTTP
implementations (``SSEToolExecutor``, ``ToolServiceExecutor``) and
the :class:`SSEAgentRunner` engine that wraps the agent loop in an
OpenAI-compatible stream live here because they are service-infrastructure,
not framework code.
"""

from mh_service_kit.sse.agent_runner import SSEAgentRunner
from mh_service_kit.sse.line import sse_line
from mh_service_kit.sse.serialization import (
    deserialize_event,
    serialize_event,
)
from mh_service_kit.sse.tool_executor import (
    SSEToolExecutor,
    ToolServiceExecutor,
)

__all__ = [
    "SSEAgentRunner",
    "SSEToolExecutor",
    "ToolServiceExecutor",
    "deserialize_event",
    "serialize_event",
    "sse_line",
]
