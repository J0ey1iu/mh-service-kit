from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ToolContext:
    """HTTP request context passed to tool handlers that declare a ``context`` parameter.

    Carries the full original request headers (keys lowercased) so tool
    implementations can extract whatever HTTP-level information they need
    — cookies, auth tokens, custom headers, etc. — without the framework
    having to predict every need.
    """

    headers: dict[str, str] = field(default_factory=dict)
