from __future__ import annotations

import json
from typing import Any


def sse_line(event: str, data: Any) -> str:
    return f"data: {json.dumps({'type': event, 'data': data}, ensure_ascii=False, default=str)}\n\n"
