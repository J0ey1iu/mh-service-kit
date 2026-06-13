# mh-service-kit

SDK for building standalone agent & tool services in the minimal-harness ecosystem.

Latest version: **0.1.0.post1**

> **开发者指南**：[docs/dev-guide.md](./docs/dev-guide.md)（中文） · [docs/dev-guide.agent.md](./docs/dev-guide.agent.md)（英文，面向 Coding Agent）

## Installation

```bash
uv add mh-service-kit
```

## Quick start

```python
from mh_service_kit import ServiceApp

service = ServiceApp(
    title="My Agent & Tool Service",
    llm_api_key="sk-xxx",
    llm_base_url="https://api.example.com/v1",
)

# Register tools and agents here...

app = service.build()  # → FastAPI app
```

Or to run directly:

```python
service.run(host="0.0.0.0", port=8003)
```

## Tool development

A Tool is a function that receives parameters (`dict`) and returns a result (`str`).
Every tool registered via `add_tool()` automatically gets:
- A `POST /tools/{name}/execute` SSE endpoint
- Entry in `GET /tools` listing
- **Automatic parameter validation** before the handler is called

### Declarative validation (recommended)

Define parameters with a Pydantic `BaseModel`. The SDK auto-generates the OpenAI JSON Schema and validates every request:

```python
# tools/weather.py
import json
from pydantic import BaseModel, Field


class WeatherParams(BaseModel):
    city: str = Field(description="City name, e.g. Beijing")
    unit: str | None = Field(default=None, description="Temperature unit")


TOOL = {
    "name": "weather",
    "display_name": "Weather Query",
    "display_name_locale": {"zh": "天气查询"},
    "description": "Get current weather for a city.",
    "description_locale": {"zh": "获取某个城市的当前天气。"},
    "params_model": WeatherParams,
}


def execute(args: dict) -> str:
    # args is guaranteed to have "city" after validation
    city = args["city"]
    return json.dumps({
        "status": "ok", "city": city,
        "temperature": 22, "condition": "sunny",
    })
```

Register in `main.py`:

```python
from mh_service_kit import ServiceApp
from agent_tool_service.tools.weather import TOOL as _weather_tool, execute as _weather_exec

service = ServiceApp(...)
service.add_tool(**_weather_tool, handler=_weather_exec)
```

The `**` unpacking passes `params_model` from the `TOOL` dict to `add_tool()`, which then:
1. Converts `WeatherParams` to an OpenAI-compatible `parameters` JSON Schema
2. Stores the model for runtime validation
3. Before calling `execute()`, validates `args` via `WeatherParams.model_validate(args)`
4. On validation failure, returns a `Validation error` SSE stream

### Schema-based validation (compatible)

If you prefer not to use Pydantic, pass a raw JSON Schema dict as `parameters`:

```python
TOOL = {
    "name": "weather",
    "parameters": {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "City name"},
        },
        "required": ["city"],
    },
}
```

Required fields and `enum` values are still checked at runtime.

### Handler signatures

The SDK supports three handler types:

| Signature | Behavior |
|---|---|
| `def execute(args: dict) -> str` | Sync call, returns result directly |
| `async def execute(args: dict) -> str` | Async call, `await` the result |
| `async def execute(args: dict) -> AsyncGenerator[str, None]` | Async generator, each `yield` → `tool_progress` SSE, last yield → `tool_end` result |

Example — streaming handler with progress steps:

```python
import asyncio, json
from pydantic import BaseModel, Field

class TextParams(BaseModel):
    text: str = Field(description="The text to analyze")

TOOL = {"name": "analyzer", "params_model": TextParams, ...}

async def execute(args: dict):
    text = args["text"]
    yield json.dumps({"step": 1, "message": f"Processing {len(text)} chars..."})
    await asyncio.sleep(0.5)
    yield json.dumps({"step": 2, "message": "Analysis complete", "result": ...})
```

### Returning metadata with results

When a tool needs to return UI data (HTML, charts, profiles) alongside the LLM-facing text, use `ToolResult` instead of a plain string:

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

`content` is the semantic payload consumed by the LLM. `meta` holds arbitrary UI/viz data — it is preserved in SSE events but never included in the LLM context window.

Streaming handlers can also yield `ToolResult` as the final result:

```python
async def execute(args: dict):
    yield json.dumps({"step": 1, "message": "Fetching data..."})
    yield ToolResult(
        content="3 profiles found: Alice, Bob, Charlie",
        meta={"profiles": [...], "html": "..."},
    )
```

### Using `parameters_from_model()` directly

You can also convert a model manually and pass the dict as `parameters`:

```python
from pydantic import BaseModel, Field
from mh_service_kit import parameters_from_model

class MyParams(BaseModel):
    query: str = Field(description="Search query")

TOOL = {
    "name": "search",
    "parameters": parameters_from_model(MyParams),
}
```

## Agent development

An Agent is an LLM-powered conversational endpoint backed by a system prompt.

```python
# agents/translator.py
AGENT = {
    "name": "translator",
    "display_name": "Translator",
    "display_name_locale": {"zh": "翻译助手", "en": "Translator"},
    "description": "Translates text between multiple languages.",
    "description_locale": {"zh": "在多语言之间翻译文本。"},
    "system_prompt": "You are a professional translator.",
    "system_prompt_locale": {
        "zh": "你是一位专业翻译。准确翻译用户文本，保留语气、风格和文化细微差别。"
    },
}
```

Register:

```python
from agent_tool_service.agents.translator import AGENT as _translator_agent
service.add_agent(**_translator_agent)
```

Each agent automatically gets `POST /agent/{name}/run` and appears in `GET /agents`.

## API reference

The built FastAPI app automatically exposes:

| Endpoint | Method | Description |
|---|---|---|
| `/agents` | GET | List all registered agents (locale-aware) |
| `/agent/{name}/run` | POST | Run an agent (SSE stream) |
| `/tools` | GET | List all registered tools (locale-aware) |
| `/tools/{name}/execute` | POST | Execute a tool (SSE stream) |
| `/playground` | GET | Developer playground UI (dev mode only) |
| `/docs` | GET | Swagger UI (FastAPI built-in) |

### SSE stream protocol

Every SSE event uses the format `data: {"type":"<event>","data":<payload>}`.

**Tool execution** — events emitted by this SDK (`tool_start` is emitted by the orchestration caller):

```
data: {"type":"tool_progress","data":"..."}                            (0 or more; one per handler yield/return)
data: {"type":"tool_end",     "data":"..."}                            (final result as string)
```

When the handler returns a `ToolResult`:

```
data: {"type":"tool_end","data":{"content":"...","__meta":{...},"__stop":false}}
```

**On validation error:**

```
data: {"type":"tool_end","data":"Validation error: ..."}
```

**Agent run** — events emitted by the LLM runner:

```
data: {"type":"agent_start",     "data":{"agent":"...","user_input":[...]}}
data: {"type":"llm_start",       "data":{"config":{...}}}
data: {"type":"llm_chunk",       "data":{"content":"..."}}             (0 or more)
data: {"type":"llm_end",         "data":{"content":"...","error":null}}
data: {"type":"execution_start", "data":{"tool_calls":[...]}}          (if tool calls)
data: {"type":"tool_progress",   "data":"..."}                        (per tool call)
data: {"type":"execution_end",   "data":{"results":[...],"error":null}}
data: {"type":"agent_end",       "data":{"response":"...","error":null}}
```

### Validation errors

When a tool request fails parameter validation, the SDK returns a `tool_end` SSE event with the error message prefixed by `Validation error:`.

```json
{"type":"tool_end","data":"Validation error: 1 validation error for WeatherParams\ncity\n  Field required [type=missing, ...]"}
```

## Locale support

Tool and agent metadata supports locale-aware resolution via `Accept-Language` header.

```python
TOOL = {
    "name": "weather",
    "display_name": "Weather Query",
    "display_name_locale": {"zh": "天气查询", "en": "Weather Query"},
    "description": "Get current weather for a city.",
    "description_locale": {"zh": "获取某个城市的当前天气。"},
}
```

`Accept-Language: zh` → displays `天气查询`. Falls back to the base value if no match.

## Configuration reference

### `ServiceApp`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `title` | `str` | `"Agent & Tool Service"` | FastAPI app title |
| `version` | `str` | `"0.1.0"` | FastAPI app version |
| `cors_origins` | `list[str]` | `["http://localhost:5173"]` | CORS allowed origins |
| `default_locale` | `str` | `"zh"` | Fallback locale |
| `dev_mode` | `bool` | `True` | Enables `/playground` |
| `llm_api_key` | `str` | `""` | Default LLM API key |
| `llm_base_url` | `str` | `""` | Default LLM base URL |
| `llm_client` | `AsyncOpenAI \| None` | `None` | Custom OpenAI client (overrides key/url) |
| `runner` | `Any \| None` | `None` | Custom SSEAgentRunner |
| `m2m_auth_provider` | `M2MAuthProvider \| None` | `None` | M2M auth provider for POST endpoints |

### `add_tool()`

| Parameter | Type | Description |
|---|---|---|
| `name` | `str` | Tool identifier (URL path segment) |
| `display_name` | `str` | Human-readable name |
| `description` | `str` | Description for LLM function calling |
| `parameters` | `dict | None` | Raw JSON Schema dict |
| `params_model` | `type[BaseModel] | None` | Pydantic model for declarative validation & schema generation |
| `handler` | `Callable` | The execute function |
| `display_name_locale` | `dict | None` | Locale-aware display names |
| `description_locale` | `dict | None` | Locale-aware descriptions |

### `add_agent()`

| Parameter | Type | Description |
|---|---|---|
| `name` | `str` | Agent identifier (URL path segment) |
| `display_name` | `str` | Human-readable name |
| `description` | `str` | Description of agent capabilities |
| `system_prompt` | `str` | LLM system prompt |
| `display_name_locale` | `dict | None` | Locale-aware display names |
| `description_locale` | `dict | None` | Locale-aware descriptions |
| `system_prompt_locale` | `dict | None` | Locale-aware system prompts |

## M2M authentication

The SDK supports machine-to-machine authentication on `POST /agent/{name}/run` and `POST /tools/{name}/execute` via a pluggable `M2MAuthProvider`.

```python
from mh_service_kit import M2MAuthProvider, ServiceApp


class MyM2MAuth:
    async def authenticate(self, request) -> str | None:
        token = request.headers.get("Authorization", "").removeprefix("Bearer ")
        return await my_token_validator.validate(token)  # app_id or None

    async def close(self) -> None:
        pass


service = ServiceApp(
    m2m_auth_provider=MyM2MAuth(),
    ...
)
app = service.build()
```

When `m2m_auth_provider` is `None` (default), POST endpoints are open (backward compatible). When set, `authenticate()` is called on every request — return `None` for 401.

## Testing

```bash
# Install
uv sync --all-packages

# Lint & format
uv run ruff check --fix packages/mh-service-kit/
uv run ruff format packages/mh-service-kit/

# Type check
uv run pyright packages/mh-service-kit/

# Run tests
uv run pytest packages/agent-tool-service/tests -v
```

## Example project

See [`agent-tool-service`](../agent-tool-service/README.md) for a complete working example with multiple agents and tools.

## Developer guide

See [`docs/dev-guide.md`](./docs/dev-guide.md) (Chinese) and [`docs/dev-guide.agent.md`](./docs/dev-guide.agent.md) (English, for Coding Agents) for detailed development instructions covering:

- Tool and agent development patterns
- Pydantic-based vs schema-based validation
- Streaming handler signatures with `ToolContext`
- Locale/i18n support
- SSE stream protocol
- Configuration reference and complete examples
