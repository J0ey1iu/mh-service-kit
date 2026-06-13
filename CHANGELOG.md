# Change Log

## 0.1.0.post1

- feat: add `MH_M2M_BYPASS` environment variable to bypass M2M auth as an escape hatch

## 0.1.0

- feat: `ServiceApp` factory — register agents and tools, build FastAPI app
- feat: add `M2MAuthProvider` protocol for machine-to-machine auth on POST endpoints
- feat: serialize `__stop` flag in `tool_end` SSE response for early agent loop termination
- feat: `ToolResult` mechanism — separate LLM content from UI metadata via `content` + `meta`
- feat: declarative parameter validation via Pydantic `params_model` with auto JSON Schema
- feat: streaming handler support — sync, async, and async generator signatures
- feat: locale-aware metadata resolution via `Accept-Language` header
- feat: `ToolContext` injection for HTTP request header access in tool handlers
- feat: developer playground UI (`/playground`) in dev mode
- feat: `parameters_from_model()` utility for manual model-to-schema conversion
- docs: add `ToolResult`/`__meta` usage examples for tool handlers
- docs: document `ToolResult.stop` param for early loop termination
- docs: sync docs with current codebase
