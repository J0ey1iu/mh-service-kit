# mh-service-kit Developer Guide (for Coding Agent)

This document specifies the exact contract for building standalone Agent & Tool microservices using the `mh-service-kit` SDK.

---

## 1. Entry Point

Create a `ServiceApp` instance, register agents and tools, then call `build()` to get a FastAPI app:

```python
from mh_service_kit import ServiceApp

service = ServiceApp(title="My Service", llm_api_key="sk-xxx")
app = service.build()  # -> FastAPI
```

Or run directly:

```python
service.run(host="0.0.0.0", port=8003)  # calls uvicorn internally
```

---

## 2. Tool Development

### 2.1 Tool Definition Pattern

Every tool is defined as a dict-like module-level constant and a handler function:

```python
# tools/my_tool.py
import json
from pydantic import BaseModel, Field

class MyParams(BaseModel):
    query: str = Field(description="Search query")
    limit: int | None = Field(default=10, description="Max results")

TOOL = {
    "name": "my_tool",
    "display_name": "My Tool",
    "display_name_locale": {"zh": "我的工具", "en": "My Tool"},
    "description": "Does something useful",
    "description_locale": {"zh": "做有用的事", "en": "Does something useful"},
    "params_model": MyParams,   # RECOMMENDED: Pydantic model for validation + schema
}
```

### 2.2 Handler Signatures

Three supported signatures:

```python
# Sync (returns result directly)
def execute(args: dict) -> str: ...

# Async
async def execute(args: dict) -> str: ...

# Streaming async generator (yields progress events)
async def execute(args: dict) -> AsyncGenerator[str, None]: ...
```

The SDK auto-detects the signature using `inspect.isasyncgenfunction()` and `inspect.iscoroutinefunction()`.

### 2.3 Argument Validation

If `params_model` is set (Pydantic model):
- SDK converts it to OpenAI-compatible JSON Schema via `model.model_json_schema()`
- Before calling handler, `params_model.model_validate(args)` runs — on failure returns SSE `tool_end` with `"Validation error: ..."`
- The validated/coerced dict is passed to the handler

If `parameters` (raw JSON Schema dict) is set instead:
- Only checks `required` fields and `enum` values
- Passes raw dict to handler

If neither is set: no validation, passes raw `{}`.

### 2.4 ToolContext (HTTP Request Access)

If handler declares a `context` keyword parameter, SDK injects a `ToolContext` dataclass:

```python
from mh_service_kit import ToolContext

def execute(args: dict, context: ToolContext) -> str:
    auth = context.headers.get("authorization", "")
    # context.headers contains ALL original request headers (lowercased keys)
    return json.dumps({"result": "ok"})
```

### 2.4b Returning Metadata with Results (`ToolResult`)

To return UI data (HTML, charts, profiles) alongside the LLM-facing text, use `ToolResult` instead of a plain string:

```python
from mh_service_kit import ToolResult

def execute(args: dict) -> ToolResult:
    result_text = json.dumps({"status": "ok", "city": args["city"]})
    return ToolResult(
        content=result_text,          # goes into LLM context
        meta={
            "html": "<div class='weather-card'>...</div>",
            "chart_data": {"labels": ["Mon","Tue"], "values": [22, 25]},
        },
    )
```

Design contract:
- `content` (`Any`): Semantic payload — included in the LLM conversation context
- `meta` (`dict | None`): Arbitrary UI/viz data — serialized as `__meta` in SSE `tool_end` events, but **never** included in the LLM context window

Streaming handlers can yield `ToolResult` as the final event:

```python
async def execute(args: dict):
    yield json.dumps({"step": 1, "message": "Fetching data..."})
    yield ToolResult(
        content="3 profiles found: Alice, Bob, Charlie",
        meta={"profiles": [...], "html": "..."},
    )
```

SSE wire format when `ToolResult` is returned:

```
data: {"type":"tool_end","data":{"content":"...","__meta":{...}}}
```

### 2.5 Registration

```python
from my_service.tools.my_tool import TOOL, execute

service.add_tool(**TOOL, handler=execute)
```

The `**TOOL` unpacking passes `params_model`, `name`, `display_name`, etc. as keyword arguments.

### 2.6 Auto-generated API

- `GET /tools` — lists all tools (locale-aware via `Accept-Language`)
- `POST /tools/{name}/execute` — SSE streaming endpoint

### 2.7 Tool SSE Protocol

```
data: {"type":"tool_start",   "data":{"tool_call":{"id":"...","function":{"name":"...","arguments":"{...}"}}}}
data: {"type":"tool_progress","data":"..."}         (0+ times for streaming handlers)
data: {"type":"tool_end",     "data":{"tool_call":{"id":"..."},"result":"..."}}
```

On validation error:

```
data: {"type":"tool_end","data":{"tool_call":{"id":""},"result":"Validation error: ..."}}
```

---

## 3. Agent Development

### 3.1 Agent Definition Pattern

```python
# agents/my_agent.py
AGENT = {
    "name": "my_agent",
    "display_name": "My Agent",
    "display_name_locale": {"zh": "我的智能体", "en": "My Agent"},
    "description": "Helps with tasks",
    "description_locale": {"zh": "帮助完成任务", "en": "Helps with tasks"},
    "system_prompt": "You are a helpful assistant.",
    "system_prompt_locale": {
        "zh": "你是一个有用的助手。",
        "en": "You are a helpful assistant.",
    },
}
```

### 3.2 Registration

```python
from my_service.agents.my_agent import AGENT
service.add_agent(**AGENT)
```

### 3.3 Agent Run Request Body

`POST /agent/{name}/run` accepts:

```json
{
  "user_input": [{"role": "user", "content": "Hello"}],
  "tools": [{"function": {"name": "my_tool", "description": "...", "parameters": {}}}],
  "memory": [{"role": "user", "content": "previous message"}],
  "system_prompt": "Optional override",
  "config": {}
}
```

Fields: `user_input` (`list[dict]`), `tools` (`list[dict]`), `memory` (`list[dict]`), `system_prompt` (`str`), `config` (`dict`).

### 3.4 Agent SSE Protocol

```
data: {"type":"agent_start",   "data":{"agent":"...","user_input":[...]}}
data: {"type":"llm_start",     "data":{"config":{...}}}
data: {"type":"llm_chunk",     "data":{"content":"..."}}
data: {"type":"llm_end",       "data":{"content":"...","error":null}}
data: {"type":"execution_start","data":{"tool_calls":[...]}}   (if tools called)
data: {"type":"tool_progress", "data":"..."}                    (per tool call)
data: {"type":"execution_end", "data":{"results":[...],"error":null}}
data: {"type":"agent_end",     "data":{"response":"...","error":null}}
```

### 3.5 System Prompt Locale Resolution

If `Accept-Language: zh` header is set AND `system_prompt_locale` contains a `"zh"` key, that value replaces the base `system_prompt`. Otherwise the base value is used.

---

## 4. Locale Resolution

Locale is parsed from `Accept-Language` header using `parse_locale()`:

```python
def parse_locale(accept_language: str | None = None) -> str:
    # "zh-CN,en;q=0.9" -> "zh"
    # Falls back to "zh"
```

Display name and description resolution:

```python
def resolve_locale(value: str, value_locale: dict | None, locale: str) -> str:
    if locale and value_locale and locale in value_locale:
        return value_locale[locale]
    return value
```

---

## 5. Build Configuration

### 5.1 ServiceApp Constructor

```python
ServiceApp(
    *,
    title: str = "Agent & Tool Service",
    version: str = "0.1.0",
    cors_origins: list[str] | None = None,         # default: ["http://localhost:5173"]
    default_locale: str = "zh",
    dev_mode: bool = True,                          # enables /playground
    llm_api_key: str = "",
    llm_base_url: str = "",
    llm_client: AsyncOpenAI | None = None,          # custom client (overrides key/url)
    runner: Any | None = None,                      # custom SSEAgentRunner
    m2m_auth_provider: M2MAuthProvider | None = None, # M2M auth for POST endpoints
)
```

`llm_api_key` and `llm_base_url` fall back to `MH_API_KEY` env var and `https://aihubmix.com/v1` respectively.

### 5.2 add_tool() Parameters

```python
service.add_tool(
    *,
    name: str,                                      # REQUIRED
    display_name: str = "",
    description: str = "",
    parameters: dict | None = None,                 # raw JSON Schema
    params_model: type[BaseModel] | None = None,    # Pydantic model (RECOMMENDED)
    handler: Callable | None = None,                 # REQUIRED
    display_name_locale: dict[str, str] | None = None,
    description_locale: dict[str, str] | None = None,
)
```

### 5.3 add_agent() Parameters

```python
service.add_agent(
    *,
    name: str,                                      # REQUIRED
    display_name: str = "",
    description: str = "",
    system_prompt: str = "",
    display_name_locale: dict[str, str] | None = None,
    description_locale: dict[str, str] | None = None,
    system_prompt_locale: dict[str, str] | None = None,
)
```

---

## 6. M2M Authentication

`POST /agent/{name}/run` and `POST /tools/{name}/execute` are M2M endpoints called by the orchestration layer. Protect them with `M2MAuthProvider`.

### 6.1 Protocol

```python
from mh_service_kit import M2MAuthProvider


class MyM2MAuth:
    async def authenticate(self, request) -> str | None:
        """Verify M2M caller identity. Return app_id or None → 401."""
        ...

    async def close(self) -> None:
        """Release resources."""
        ...
```

### 6.2 Injection

```python
from mh_service_kit import ServiceApp

service = ServiceApp(
    m2m_auth_provider=MyM2MAuth(),
    ...
)
app = service.build()
```

When `m2m_auth_provider` is `None` (default), POST endpoints are open — backward compatible for dev setups. When set, every POST to `/agent/{name}/run` or `/tools/{name}/execute` is authenticated.

---

## 7. Complete Example

```python
# main.py
import json
from pydantic import BaseModel, Field
from mh_service_kit import ServiceApp


class EchoParams(BaseModel):
    message: str = Field(description="Message to echo")

def echo_execute(args: dict) -> str:
    return json.dumps({"echo": args["message"]})


service = ServiceApp(title="Echo Service", llm_api_key="sk-xxx")
service.add_tool(
    name="echo",
    display_name="Echo",
    description="Echo back a message",
    params_model=EchoParams,
    handler=echo_execute,
)
service.add_agent(
    name="helper",
    display_name="Helper",
    description="General assistant",
    system_prompt="You are a helpful assistant.",
)
app = service.build()
```

Start with `uvicorn main:app --port 8003`.

---

## 8. LLM Runner Internals

The SDK uses `SSEAgentRunner` from `minimal_harness.agent.runner` to drive LLM conversations. It is lazily initialized via `get_runner()` singleton pattern.

To reset singleton (e.g. for test isolation):

```python
service.reset_llm_singletons()
```
