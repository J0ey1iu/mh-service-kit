from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolContext:
    """Request context passed to tool handlers that declare a ``context`` parameter.

    Carries the full original request headers (keys lowercased) plus the
    structured ``context`` object forwarded by the gateway in the request
    body (user id, trace id, locale, scenario/agent, ...).  Fields that the
    gateway did not send remain at their defaults, so tools written for the
    header-only behaviour keep working unchanged.

    Unknown keys in the forwarded context land in :attr:`extra`, so newer
    gateways can add fields without breaking older tool services.
    """

    headers: dict[str, str] = field(default_factory=dict)
    user_id: str = ""
    username: str = ""
    roles: list[str] = field(default_factory=list)
    extra_data: dict[str, Any] = field(default_factory=dict)
    trace_id: str = ""
    locale: str = ""
    scenario_id: str = ""
    agent_name: str = ""
    correlation_id: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(
        cls, context: dict[str, Any] | None, headers: dict[str, str] | None = None
    ) -> "ToolContext":
        """Build a ToolContext from a forwarded ``context`` dict (body) plus the raw request headers."""
        ctx = context or {}
        known = {
            "user_id",
            "username",
            "roles",
            "extra_data",
            "trace_id",
            "locale",
            "scenario_id",
            "agent_name",
            "correlation_id",
        }
        return cls(
            headers=dict(headers or {}),
            user_id=str(ctx.get("user_id", "") or ""),
            username=str(ctx.get("username", "") or ""),
            roles=[str(r) for r in ctx.get("roles") or []],
            extra_data=dict(ctx.get("extra_data") or {}),
            trace_id=str(ctx.get("trace_id", "") or ""),
            locale=str(ctx.get("locale", "") or ""),
            scenario_id=str(ctx.get("scenario_id", "") or ""),
            agent_name=str(ctx.get("agent_name", "") or ""),
            correlation_id=str(ctx.get("correlation_id", "") or ""),
            extra={k: v for k, v in ctx.items() if k not in known},
        )
