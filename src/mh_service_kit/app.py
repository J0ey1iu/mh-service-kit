from __future__ import annotations

import inspect
import logging
from collections.abc import AsyncGenerator
from typing import Any, Callable

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from openai import AsyncOpenAI
from pydantic import BaseModel

from mh_service_kit.context import ToolContext
from mh_service_kit.llm import get_runner, reset as reset_llm
from mh_service_kit.locale import parse_locale, resolve_locale
from mh_service_kit.models import (
    AgentRunRequest,
    ToolExecuteRequest,
    parameters_from_model,
    validate_args,
)
from mh_service_kit.playground import PLAYGROUND_HTML
from mh_service_kit.sse import sse_line

from minimal_harness.client.logging_setup import setup_service_logging
from minimal_harness.types import ToolResult

logger = logging.getLogger(__name__)


class ServiceApp:
    def __init__(
        self,
        *,
        title: str = "Agent & Tool Service",
        version: str = "0.1.0",
        cors_origins: list[str] | None = None,
        default_locale: str = "zh",
        dev_mode: bool = True,
        llm_client: AsyncOpenAI | None = None,
        runner: Any | None = None,
        llm_api_key: str = "",
        llm_base_url: str = "",
    ):
        self._title = title
        self._version = version
        self._cors_origins = cors_origins or ["http://localhost:5173"]
        self._default_locale = default_locale
        self._dev_mode = dev_mode
        self._llm_client = llm_client
        self._runner = runner
        self._llm_api_key = llm_api_key
        self._llm_base_url = llm_base_url

        self._agents: dict[str, dict[str, Any]] = {}
        self._tools: dict[str, dict[str, Any]] = {}
        self._handlers: dict[str, Callable] = {}
        self._params_models: dict[str, type[BaseModel] | None] = {}

    # ── Agent registration ──────────────────────────────────────────

    def add_agent(
        self,
        *,
        name: str,
        display_name: str = "",
        description: str = "",
        system_prompt: str = "",
        display_name_locale: dict[str, str] | None = None,
        description_locale: dict[str, str] | None = None,
        system_prompt_locale: dict[str, str] | None = None,
    ) -> None:
        self._agents[name] = {
            "name": name,
            "display_name": display_name or name,
            "display_name_locale": display_name_locale,
            "description": description,
            "description_locale": description_locale,
            "system_prompt": system_prompt,
            "system_prompt_locale": system_prompt_locale,
        }

    # ── Tool registration ───────────────────────────────────────────

    def add_tool(
        self,
        *,
        name: str,
        display_name: str = "",
        description: str = "",
        parameters: dict | None = None,
        params_model: type[BaseModel] | None = None,
        handler: Callable[[dict], str]
        | Callable[[dict], AsyncGenerator[str, None]]
        | None = None,
        display_name_locale: dict[str, str] | None = None,
        description_locale: dict[str, str] | None = None,
    ) -> None:
        if params_model is not None:
            resolved_params: dict = parameters_from_model(params_model)
        else:
            resolved_params = parameters or {}

        self._tools[name] = {
            "name": name,
            "display_name": display_name or name,
            "display_name_locale": display_name_locale,
            "description": description,
            "description_locale": description_locale,
            "parameters": resolved_params,
        }
        self._params_models[name] = params_model
        if handler:
            self._handlers[name] = handler

    # ── LLM helpers ─────────────────────────────────────────────────

    def _resolve_runner(self) -> Any:
        if self._runner is not None:
            return self._runner
        client = self._llm_client
        if client is None:
            client = self._get_default_client()
        return get_runner(llm_client=client)

    def _get_default_client(self) -> AsyncOpenAI:
        from os import environ

        api_key = self._llm_api_key or environ.get("MH_API_KEY", "")
        base_url = self._llm_base_url or "https://aihubmix.com/v1"
        return AsyncOpenAI(api_key=api_key, base_url=base_url)

    def reset_llm_singletons(self) -> None:
        reset_llm()

    # ── Build FastAPI app ───────────────────────────────────────────

    def build(self) -> FastAPI:
        app = FastAPI(title=self._title, version=self._version)
        app.add_middleware(
            CORSMiddleware,
            allow_origins=self._cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        if self._dev_mode:

            @app.get("/playground", include_in_schema=False)
            async def playground():
                return HTMLResponse(PLAYGROUND_HTML)

        agents = self._agents
        tools = self._tools
        handlers = self._handlers
        resolve = resolve_locale
        default_locale = self._default_locale
        resolve_runner = self._resolve_runner

        # ── GET /agents ─────────────────────────────────────────────

        @app.get("/agents")
        async def list_agents(
            accept_language: str | None = Header(None, alias="Accept-Language"),
        ):
            locale = parse_locale(accept_language) or default_locale
            result = [
                {
                    "name": cfg["name"],
                    "display_name": resolve(
                        cfg["display_name"], cfg.get("display_name_locale"), locale
                    ),
                    "description": resolve(
                        cfg["description"], cfg.get("description_locale"), locale
                    ),
                }
                for cfg in agents.values()
            ]
            logger.debug(
                "OUTBOUND GET /agents — locale=%s returned=%d",
                locale,
                len(result),
            )
            return result

        # ── GET /tools ──────────────────────────────────────────────

        @app.get("/tools")
        async def list_tools(
            accept_language: str | None = Header(None, alias="Accept-Language"),
        ):
            locale = parse_locale(accept_language) or default_locale
            result = [
                {
                    **t,
                    "display_name": resolve(
                        t["display_name"], t.get("display_name_locale"), locale
                    ),
                    "description": resolve(
                        t["description"], t.get("description_locale"), locale
                    ),
                }
                for t in tools.values()
            ]
            logger.debug(
                "OUTBOUND GET /tools — locale=%s returned=%d",
                locale,
                len(result),
            )
            return result

        # ── POST /agent/{agent_name}/run ────────────────────────────

        @app.post("/agent/{agent_name}/run")
        async def run_agent(
            agent_name: str,
            body: AgentRunRequest,
            accept_language: str | None = Header(None, alias="Accept-Language"),
        ):
            logger.debug(
                "INBOUND POST /agent/%s/run — user_input_count=%d tools_count=%d memory_count=%d locale=%s",
                agent_name,
                len(body.user_input),
                len(body.tools),
                len(body.memory),
                accept_language,
            )
            agent = agents.get(agent_name)
            if agent is None:
                logger.warning("agent not found: %s", agent_name)
                raise HTTPException(
                    status_code=404, detail=f"Agent {agent_name} not found"
                )

            locale = parse_locale(accept_language) or default_locale
            system_prompt = body.system_prompt or resolve(
                agent["system_prompt"], agent.get("system_prompt_locale"), locale
            )

            runner = resolve_runner()

            async def event_stream():
                event_count = 0
                async for line in runner.run(
                    user_input=body.user_input,
                    tools_schema=body.tools,
                    memory_messages=body.memory,
                    system_prompt=system_prompt,
                    config=body.config,
                ):
                    event_count += 1
                    logger.debug(
                        "OUTBOUND /agent/%s/run event — event_count=%d line_preview=%r",
                        agent_name,
                        event_count,
                        line[:120] if isinstance(line, str) else line,
                    )
                    yield line
                logger.debug(
                    "OUTBOUND /agent/%s/run complete — total_events=%d",
                    agent_name,
                    event_count,
                )

            return StreamingResponse(event_stream(), media_type="text/event-stream")

        # ── POST /tools/{tool_name}/execute ─────────────────────────

        @app.post("/tools/{tool_name}/execute")
        async def execute_tool(
            tool_name: str,
            body: ToolExecuteRequest,
            request: Request,
        ):
            logger.debug(
                "INBOUND POST /tools/%s/execute — args_keys=%s",
                tool_name,
                list(body.args.keys()) if isinstance(body.args, dict) else [],
            )
            handler = handlers.get(tool_name)
            if handler is None:
                logger.warning("tool not found: %s", tool_name)

                async def error_stream():
                    yield sse_line("tool_end", f"Tool {tool_name} not found")

                return StreamingResponse(error_stream(), media_type="text/event-stream")

            params_model = self._params_models.get(tool_name)
            tool_config = tools.get(tool_name, {})
            validated, error = validate_args(
                body.args, tool_config.get("parameters"), params_model
            )
            if error is not None:
                logger.warning(
                    "tool arg validation failed: tool=%s error=%s", tool_name, error
                )

                async def validation_error_stream():
                    yield sse_line("tool_end", f"Validation error: {error}")

                return StreamingResponse(
                    validation_error_stream(), media_type="text/event-stream"
                )

            context = ToolContext(
                headers={k.lower(): v for k, v in request.headers.items()},
            )
            needs_context = "context" in inspect.signature(handler).parameters

            async def event_stream():
                try:
                    if inspect.isasyncgenfunction(handler):
                        final_result = ""
                        gen = (
                            handler(validated, context=context)
                            if needs_context
                            else handler(validated)
                        )
                        async for chunk in gen:
                            logger.debug(
                                "OUTBOUND /tools/%s/tool_progress — chunk_type=%s chunk_preview=%r",
                                tool_name,
                                type(chunk).__name__,
                                str(chunk)[:80],
                            )
                            yield sse_line("tool_progress", chunk)
                            final_result = chunk
                        result = final_result
                    elif inspect.iscoroutinefunction(handler):
                        result = (
                            await handler(validated, context=context)
                            if needs_context
                            else await handler(validated)
                        )
                        logger.debug(
                            "OUTBOUND /tools/%s/tool_progress — result_type=%s result_preview=%r",
                            tool_name,
                            type(result).__name__,
                            str(result)[:80],
                        )
                        yield sse_line("tool_progress", result)
                    else:
                        result = (
                            handler(validated, context=context)
                            if needs_context
                            else handler(validated)
                        )
                        logger.debug(
                            "OUTBOUND /tools/%s/tool_progress — result_type=%s result_preview=%r",
                            tool_name,
                            type(result).__name__,
                            str(result)[:80],
                        )
                        yield sse_line("tool_progress", result)

                    logger.debug(
                        "OUTBOUND /tools/%s/tool_end — result_preview=%r",
                        tool_name,
                        str(result)[:120],
                    )
                    if isinstance(result, ToolResult):
                        yield sse_line(
                            "tool_end",
                            {"content": result.content, "__meta": result.meta},
                        )
                    else:
                        yield sse_line("tool_end", result)
                except Exception as e:
                    logger.exception(
                        "Tool %s execution failed — error=%s",
                        tool_name,
                        e,
                    )
                    yield sse_line(
                        "error",
                        {"message": f"Tool execution failed: {e}"},
                    )
                    yield sse_line(
                        "tool_end",
                        {
                            "tool_call": {"id": body.tool_call_id},
                            "result": f"Error: {e}",
                        },
                    )

            return StreamingResponse(event_stream(), media_type="text/event-stream")

        return app

    # ── Run server ──────────────────────────────────────────────────

    def run(self, host: str = "0.0.0.0", port: int = 8003) -> None:
        import uvicorn

        setup_service_logging()
        logger.info("starting service — host=%s port=%d", host, port)
        app = self.build()
        uvicorn.run(app, host=host, port=port)
