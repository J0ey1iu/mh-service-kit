from __future__ import annotations

from openai import AsyncOpenAI
from minimal_harness.agent.runner import SSEAgentRunner

_client: AsyncOpenAI | None = None
_runner: SSEAgentRunner | None = None


def get_client(api_key: str = "", base_url: str = "") -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    return _client


def get_runner(llm_client: AsyncOpenAI | None = None) -> SSEAgentRunner:
    global _runner
    if _runner is None:
        _runner = SSEAgentRunner(llm_client=llm_client)
    return _runner


def reset() -> None:
    global _client, _runner
    _client = None
    _runner = None
