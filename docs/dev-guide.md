# mh-service-kit 服务开发指南

本文档面向 **基于 mh-service-kit 框架开发 Agent/Tool 微服务** 的开发人员。

---

## 架构概述

mh-service-kit 是一个轻量级 FastAPI SDK，用于快速构建提供 Agent 和 Tool 能力的独立微服务。它封装了 LLM 调用、SSE 流式推送、参数校验和国际化能力。

```
┌─────────────────────────────────────────────────────┐
│  mh-service-kit Service                              │
│  ┌───────────────────────────────────────────┐     │
│  │  ServiceApp                                │     │
│  │  ├── add_agent()    → POST /agent/{n}/run  │     │
│  │  ├── add_tool()     → POST /tools/{n}/exec │     │
│  │  ├── build()        → FastAPI app          │     │
│  │  └── run()          → uvicorn 内嵌启动      │     │
│  └───────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────┘
```

---

## 快速开始

```python
from mh_service_kit import ServiceApp

service = ServiceApp(
    title="My Service",
    llm_api_key="sk-xxx",
    llm_base_url="https://api.example.com/v1",
)
app = service.build()  # → FastAPI app
```

或直接运行：

```python
service.run(host="0.0.0.0", port=8003)
```

---

## 开发 Tool

每个 Tool 是一个接收参数字典、返回字符串（或异步生成器）的函数。注册后自动获得 `POST /tools/{name}/execute` SSE 端点和 `GET /tools` 列表。

### 声明式校验（推荐）

```python
# tools/weather.py
import json
from pydantic import BaseModel, Field


class WeatherParams(BaseModel):
    city: str = Field(description="城市名，如 Beijing")
    unit: str | None = Field(default=None, description="温度单位")


TOOL = {
    "name": "weather",
    "display_name": "天气查询",
    "display_name_locale": {"zh": "天气查询", "en": "Weather Query"},
    "description": "获取某个城市的当前天气。",
    "description_locale": {
        "zh": "获取某个城市的当前天气。",
        "en": "Get current weather for a city.",
    },
    "params_model": WeatherParams,
}


def execute(args: dict) -> str:
    city = args["city"]
    return json.dumps({"status": "ok", "city": city, "temperature": 22})
```

注册：

```python
from agent_tool_service.tools.weather import TOOL, execute

service.add_tool(**TOOL, handler=execute)
```

### 原生 JSON Schema 校验

```python
TOOL = {
    "name": "search",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词"},
            "limit": {"type": "integer", "description": "返回条数"},
        },
        "required": ["query"],
    },
}
```

### Handler 三种签名

| 签名 | 行为 |
|------|------|
| `def execute(args: dict) -> str` | 同步，直接返回结果 |
| `async def execute(args: dict) -> str` | 异步，await 结果 |
| `async def execute(args: dict) -> AsyncGenerator[str, None]` | 流式，每次 `yield` 推送 tool_progress，最后一次为 tool_end 结果 |

流式示例：

```python
import asyncio, json
from pydantic import BaseModel, Field

class TextParams(BaseModel):
    text: str = Field(description="要分析的文本")

async def execute(args: dict):
    text = args["text"]
    yield json.dumps({"step": 1, "message": f"正在处理 {len(text)} 个字符..."})
    await asyncio.sleep(0.5)
    yield json.dumps({"step": 2, "message": "分析完成", "result": "..."})
```

### 返回带元数据的结果

如果 Tool 需要同时返回 LLM 可读文本和 UI 展示数据（HTML、图表、档案等），使用 `ToolResult` 对象替代纯字符串：

```python
from mh_service_kit import ToolResult

def execute(args: dict) -> ToolResult:
    result_text = json.dumps({"status": "ok", "city": args["city"]})
    return ToolResult(
        content=result_text,     # 进入 LLM 上下文
        meta={
            "html": "<div class='weather-card'>...</div>",
            "chart_data": {"labels": ["周一","周二"], "values": [22, 25]},
        },
    )
```

- `content`：语义结果，进入 LLM 上下文，LLM 基于此生成回复
- `meta`：UI / 可视化元数据，随 SSE 事件下发但不进入 LLM 上下文，不会消耗上下文窗口

#### 提前终止 Agent 循环

当 Tool 执行完成后不希望 Agent 继续推理时，设置 `stop=True`：

```python
def execute(args: dict) -> ToolResult:
    return ToolResult(
        content=f"订单 {args['order_id']} 已确认，无需后续操作。",
        stop=True,
    )
```

`stop=True` 的效果：
- Agent 在当前这批 Tool 执行完毕后立即停止循环，不再调用 LLM
- `ToolResult.content` 作为最终回复返回给用户

流式 handler 也可以在最后 yield `ToolResult`：

```python
async def execute(args: dict):
    yield json.dumps({"step": 1, "message": "正在获取数据..."})
    yield ToolResult(
        content="找到 3 份档案：Alice、Bob、Charlie",
        meta={"profiles": [...], "html": "..."},
    )
```

### 访问 HTTP 请求上下文

handler 声明 `context` 参数即可接收 `ToolContext`，包含原始请求的 header：

```python
from mh_service_kit import ToolContext

def execute(args: dict, context: ToolContext):
    auth_token = context.headers.get("authorization", "")
    # 调用下游 API 时携带用户认证信息
    return json.dumps({"result": "ok"})
```

---

## 开发 Agent

Agent 是一个由 system prompt 驱动的 LLM 对话端点：

```python
# agents/translator.py
AGENT = {
    "name": "translator",
    "display_name": "翻译助手",
    "display_name_locale": {"zh": "翻译助手", "en": "Translator"},
    "description": "在多语言之间翻译文本。",
    "description_locale": {
        "zh": "在多语言之间翻译文本。",
        "en": "Translates text between multiple languages.",
    },
    "system_prompt": "You are a professional translator.",
    "system_prompt_locale": {
        "zh": "你是一位专业翻译。准确翻译用户文本，保留语气、风格和文化细微差别。",
        "en": "You are a professional translator.",
    },
}
```

注册：

```python
from my_service.agents.translator import AGENT
service.add_agent(**AGENT)
```

注册后自动获得 `POST /agent/{name}/run` 端点和 `GET /agents` 列表。

Agent 端点接收的请求体：

```json
{
  "user_input": [{"role": "user", "content": "..."}],
  "tools": [{"function": {"name": "weather", "parameters": {...}}}],
  "memory": [{"role": "user", "content": "..."}],
  "system_prompt": "覆盖默认 system prompt（可选）",
  "config": {}
}
```

---

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/agents` | 列出所有 Agent（locale-aware） |
| POST | `/agent/{name}/run` | 运行 Agent（SSE 流式） |
| GET | `/tools` | 列出所有 Tool（locale-aware） |
| POST | `/tools/{name}/execute` | 执行 Tool（SSE 流式） |
| GET | `/playground` | 开发者调试 UI（仅 dev_mode） |
| GET | `/docs` | Swagger 文档 |

---

## SSE 流协议

### Tool 执行

```
data: {"type":"tool_start",   "data":{"tool_call":{"id":"...","function":{"name":"...","arguments":"{...}"}}}}
data: {"type":"tool_progress","data":"..."}
data: {"type":"tool_end",     "data":{"tool_call":{"id":"..."},"result":"..."}}
```

校验失败时：

```
data: {"type":"tool_end","data":{"tool_call":{"id":""},"result":"Validation error: ..."}}
```

### Agent 运行

```
data: {"type":"agent_start","data":{"agent":"...","user_input":[...]}}
data: {"type":"llm_start",  "data":{"config":{...}}}
data: {"type":"llm_chunk",  "data":{"content":"..."}}
data: {"type":"llm_end",    "data":{"content":"...","error":null}}
data: {"type":"execution_start","data":{"tool_calls":[...]}}
data: {"type":"tool_progress","data":"..."}
data: {"type":"execution_end","data":{"results":[...],"error":null}}
data: {"type":"agent_end","data":{"response":"...","error":null}}
```

---

## 国际化（Locale）

通过 `Accept-Language` 请求头自动切换语言：

```python
TOOL = {
    "name": "weather",
    "display_name": "Weather Query",
    "display_name_locale": {"zh": "天气查询", "en": "Weather Query"},
    "description": "Get current weather for a city.",
    "description_locale": {"zh": "获取某个城市的当前天气。"},
}
```

`Accept-Language: zh` → 显示 `天气查询`。无匹配时 fallback 到 `default_locale`（默认 `"zh"`）。

Agent 的 `system_prompt_locale` 使得不同语言用户获得对应语言的 system prompt。

---

## 配置参考

### ServiceApp 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `title` | `str` | `"Agent & Tool Service"` | FastAPI app 标题 |
| `version` | `str` | `"0.1.0"` | 版本号 |
| `cors_origins` | `list[str]` | `["http://localhost:5173"]` | CORS 允许来源 |
| `default_locale` | `str` | `"zh"` | 默认语言 |
| `dev_mode` | `bool` | `True` | 启用 `/playground` |
| `llm_api_key` | `str` | `""` | LLM API Key |
| `llm_base_url` | `str` | `""` | LLM 接口地址 |
| `llm_client` | `AsyncOpenAI \| None` | `None` | 自定义 OpenAI 客户端 |
| `runner` | `Any` | `None` | 自定义 SSEAgentRunner |

`llm_api_key` 和 `llm_base_url` 均可通过 `MH_API_KEY` 环境变量覆盖。

### add_tool() 参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `name` | `str` | Tool 标识（URL 路径段） |
| `display_name` | `str` | 显示名 |
| `description` | `str` | 描述（LLM function calling 使用） |
| `parameters` | `dict \| None` | 原生 JSON Schema |
| `params_model` | `type[BaseModel] \| None` | Pydantic 模型（推荐） |
| `handler` | `Callable` | 执行函数 |
| `display_name_locale` | `dict \| None` | 多语言显示名 |
| `description_locale` | `dict \| None` | 多语言描述 |

### add_agent() 参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `name` | `str` | Agent 标识（URL 路径段） |
| `display_name` | `str` | 显示名 |
| `description` | `str` | 描述 |
| `system_prompt` | `str` | LLM system prompt |
| `display_name_locale` | `dict \| None` | 多语言显示名 |
| `description_locale` | `dict \| None` | 多语言描述 |
| `system_prompt_locale` | `dict \| None` | 多语言 system prompt |

---

## 完整示例

```python
# main.py
import json
from pydantic import BaseModel, Field
from mh_service_kit import ServiceApp, parameters_from_model


# ── Tool 定义 ──────────────────────────────────
class CalcParams(BaseModel):
    expression: str = Field(description="数学表达式，如 2 + 2")

def calc_execute(args: dict) -> str:
    return json.dumps({"result": eval(args["expression"])})

# ── Agent 定义 ─────────────────────────────────
TRANSLATOR_AGENT = {
    "name": "translator",
    "display_name": "翻译助手",
    "description": "多语言翻译",
    "system_prompt": "You are a professional translator.",
}

# ── 组装 ───────────────────────────────────────
service = ServiceApp(title="My Service", llm_api_key="sk-xxx")
service.add_tool(
    name="calculator",
    display_name="计算器",
    description="执行数学运算",
    params_model=CalcParams,
    handler=calc_execute,
)
service.add_agent(**TRANSLATOR_AGENT)
app = service.build()
```

启动：

```bash
uvicorn main:app --port 8003
```
