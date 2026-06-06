from __future__ import annotations

import logging
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class M2MAuthProvider(Protocol):
    """机机接口鉴权提供者。

    在 agent 调用端点（``POST /agent/{name}/run``）和
    tool 执行端点（``POST /tools/{name}/execute``）被调用时
    验证调用方身份。

    客户企业部署时实现此 protocol，通过 SOA、API Key、mTLS
    或其他机制验证调用方应用身份。接收原始 ``Request`` 对象，
    可自行决定检查方式（header、cookie、mTLS 证书等）。

    返回 ``app_id`` 表示鉴权通过，返回 ``None`` 表示失败（返回 401）。
    """

    async def authenticate(self, request: Any) -> str | None:
        """验证机机调用方身份。

        Args:
            request: 当前 FastAPI Request 对象。

        Returns:
            app_id 表示鉴权通过，``None`` 表示鉴权失败（调用方返回 401）。
        """
        ...

    async def close(self) -> None:
        """释放资源（连接池、文件句柄等）。"""
        ...


class _DefaultM2MAuthProvider:
    """默认实现——不做判断，仅记录请求信息。

    不执行任何鉴权校验，一律放行。仅以 INFO 级别打印请求的
    method、path 和关键 header，方便开发阶段观察流量。

    生产环境必须替换为实际的 M2M 鉴权实现（如 SOA、API Key
    签名校验）。
    """

    async def close(self) -> None:
        pass

    async def authenticate(self, request: Any) -> str | None:
        logger.info(
            "M2M request — method=%s path=%s headers=%s",
            request.method,
            request.url.path,
            dict(request.headers),
        )
        return "anonymous"
