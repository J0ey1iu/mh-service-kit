# Change Log

## 0.1.2a3

- chore: pin `minimal-harness>=0.8.0a3` (lockstep with publish set;
  no SDK code change).

## 0.1.2a2

- chore: pin `minimal-harness>=0.8.0a2` (lockstep with publish set;
  no SDK code change).

## 0.1.2a1

- chore: pin `minimal-harness>=0.8.0a1` (lockstep with publish set)
- docs: repair UTF-8 corruption in README

## 0.1.1a7

- chore: bump `minimal-harness` pin from `==0.7.0a7` to `==0.7.0a8`
  for lockstep pre-release alignment.

## 0.1.1a6

- chore: lockstep pre-release bump with `minimal-harness==0.7.0a8`.
  No SDK code change.

## 0.1.1a5

- chore: aligned pre-release bump with `mh-gateway==0.1.0a5` and
  `minimal-harness==0.7.0a6` (lockstep release).
- chore: pin `minimal-harness==0.7.0a6`.
- refactor: drop the `RemoteAgent` concept and remove
  `SSEAgentDriver` / `RemoteAgent`; the SSE transport is now
  exclusively served by the modules re-exported from
  `mh-service-kit.sse` (round-2 SDK decoupling follow-up).
- fix: pass `trust_env=False` to the `SSEToolExecutor` `httpx`
  client so system proxy env vars no longer hijack outbound
  calls in proxy-enabled environments.
- chore: update internal references from `orchestration-service`
  to `mh-gateway`.

## 0.1.1a4

- chore: pre-release bump to align with `minimal-harness==0.7.0a5`
  no SDK code change.

## 0.1.1a3

- chore: pre-release bump to align with `minimal-harness==0.7.0a4`
  no SDK code change.

## 0.1.1a2

- chore: pre-release bump to align with `minimal-harness==0.7.0a2`
  for the round-2 SDK-decoupling distribution.

## 0.1.1a1

- chore: bump `minimal-harness` dependency constraint to `>=0.7.0a1` for pre-release alignment

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
