"""Core route generation and ASGI app factory for mcp-embedded-ui."""

from __future__ import annotations

import inspect
import logging
import warnings
from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from typing import Any, TypedDict

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.types import ASGIApp

from .html import render_explorer_html

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

class CallResult(TypedDict):
    content: list[dict[str, Any]]
    isError: bool
    _meta: dict[str, Any] | None


_ToolCallResult = Awaitable[tuple[list[dict[str, Any]], bool, str | None]]

# 2-param: (name, args) -> result
_ToolCallHandler2 = Callable[[str, dict[str, Any]], _ToolCallResult]
# 3-param: (name, args, request) -> result
_ToolCallHandler3 = Callable[[str, dict[str, Any], Request], _ToolCallResult]

ToolCallHandler = _ToolCallHandler2 | _ToolCallHandler3

# Auth hook can return either a sync or async context manager
AuthHook = Callable[
    [Request],
    AbstractContextManager[Any] | AbstractAsyncContextManager[Any],
]

# Tools can be a static list, a sync callable, or an async callable
ToolsProvider = (
    list[Any]
    | Callable[[], list[Any]]
    | Callable[[], Awaitable[list[Any]]]
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _resolve_tools(tools: ToolsProvider) -> list[Any]:
    """Resolve a ToolsProvider into a concrete list of tools."""
    if isinstance(tools, list):
        return tools
    result = tools()
    if inspect.isawaitable(result):
        return await result
    return result  # type: ignore[return-value]


def _make_serializable(obj: Any) -> Any:
    """Convert common model types to JSON-serializable dicts."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump(exclude_none=True)
    if hasattr(obj, "dict"):
        return obj.dict(exclude_none=True)
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    return obj


def _tool_summary(tool: Any) -> dict[str, Any]:
    """Return a summary dict for a tool."""
    result: dict[str, Any] = {
        "name": getattr(tool, "name", "unknown"),
        "description": getattr(tool, "description", ""),
    }
    annotations = _make_serializable(getattr(tool, "annotations", None))
    if annotations:
        result["annotations"] = annotations
    return result


def _tool_detail(tool: Any) -> dict[str, Any]:
    """Return a full detail dict for a tool."""
    result: dict[str, Any] = {
        "name": getattr(tool, "name", "unknown"),
        "description": getattr(tool, "description", ""),
        "inputSchema": _make_serializable(getattr(tool, "inputSchema", {})),
    }
    annotations = _make_serializable(getattr(tool, "annotations", None))
    if annotations:
        result["annotations"] = annotations
    return result


async def _resolve_tools_by_name(
    tools: ToolsProvider,
) -> tuple[list[Any], dict[str, Any]]:
    """Resolve tools and build a name->tool lookup dict."""
    tool_list = await _resolve_tools(tools)
    by_name = {getattr(t, "name", ""): t for t in tool_list}
    return tool_list, by_name


# ---------------------------------------------------------------------------
# Route builder (low-level)
# ---------------------------------------------------------------------------

def build_ui_routes(
    tools: ToolsProvider,
    handle_call: ToolCallHandler,
    *,
    allow_execute: bool = True,
    auth_hook: AuthHook | None = None,
    title: str = "MCP Tool Explorer",
    project_name: str | None = None,
    project_url: str | None = None,
) -> list[Route]:
    """Build Starlette routes for the MCP Embedded UI.

    Args:
        tools: MCP Tool objects (list, sync callable, or async callable).
            Each tool must have ``.name``, ``.description``, ``.inputSchema``.
        handle_call: Async callback for tool execution:
            ``(name, args) -> (content, is_error, trace_id)``.
        allow_execute: Enable/disable tool execution via UI.
        auth_hook: Optional hook that receives a ``Request`` and returns a
            context manager (sync or async).  Raise inside to reject with
            401.  Use your own ``ContextVar`` to propagate identity.
        title: Page title shown in the browser tab and heading.
        project_name: Optional project name shown in the footer.
        project_url: Optional project URL linked in the footer.
    """
    html_page = render_explorer_html(
        title, allow_execute=allow_execute,
        project_name=project_name, project_url=project_url,
    )
    _handler_takes_request = len(inspect.signature(handle_call).parameters) >= 3

    async def explorer_page(request: Request) -> HTMLResponse:
        return HTMLResponse(html_page)

    async def list_tools(request: Request) -> JSONResponse:
        tool_list = await _resolve_tools(tools)
        return JSONResponse([_tool_summary(t) for t in tool_list])

    async def tool_detail_endpoint(request: Request) -> Response:
        name = request.path_params["name"]
        _, by_name = await _resolve_tools_by_name(tools)
        tool = by_name.get(name)
        if tool is None:
            return JSONResponse({"error": f"Tool not found: {name}"}, status_code=404)
        return JSONResponse(_tool_detail(tool))

    async def call_tool(request: Request) -> Response:
        if not allow_execute:
            return JSONResponse({"error": "Tool execution is disabled."}, status_code=403)

        name = request.path_params["name"]
        _, by_name = await _resolve_tools_by_name(tools)
        tool = by_name.get(name)
        if tool is None:
            return JSONResponse({"error": f"Tool not found: {name}"}, status_code=404)

        try:
            body = await request.json()
        except Exception:
            body = {}

        if auth_hook:
            try:
                cm = auth_hook(request)
                if isinstance(cm, AbstractAsyncContextManager):
                    async with cm:
                        return await _do_call(name, body, handle_call, request)
                else:
                    with cm:
                        return await _do_call(name, body, handle_call, request)
            except Exception as e:
                logger.warning("Auth hook failed for tool %s: %s", name, e)
                return JSONResponse(
                    {"error": "Unauthorized"},
                    status_code=401,
                )

        return await _do_call(name, body, handle_call, request)

    async def _do_call(
        name: str, body: dict, handler: ToolCallHandler, request: Request
    ) -> JSONResponse:
        try:
            if _handler_takes_request:
                content, is_error, trace_id = await handler(name, body, request)  # type: ignore[call-arg]
            else:
                content, is_error, trace_id = await handler(name, body)  # type: ignore[call-arg]
            result: dict[str, Any] = {"content": content, "isError": is_error}
            if trace_id:
                result["_meta"] = {"_trace_id": trace_id}
            return JSONResponse(result, status_code=500 if is_error else 200)
        except Exception as exc:
            logger.error("UI call_tool error for %s: %s", name, exc)
            return JSONResponse(
                {"content": [{"type": "text", "text": str(exc)}], "isError": True},
                status_code=500,
            )

    return [
        Route("/", endpoint=explorer_page, methods=["GET"]),
        Route("/tools", endpoint=list_tools, methods=["GET"]),
        Route("/tools/{name:path}/call", endpoint=call_tool, methods=["POST"]),
        Route("/tools/{name:path}", endpoint=tool_detail_endpoint, methods=["GET"]),
    ]


# ---------------------------------------------------------------------------
# High-level factories
# ---------------------------------------------------------------------------

def create_app(
    tools: ToolsProvider,
    handle_call: ToolCallHandler,
    **kwargs: Any,
) -> ASGIApp:
    """Create a standalone ASGI application for the MCP Embedded UI.

    This is the universal entry point — mount in any ASGI-compatible
    framework (Starlette, FastAPI, Django, aiohttp via adapter, etc.).

    All keyword arguments are forwarded to :func:`build_ui_routes`.
    """
    routes = build_ui_routes(tools, handle_call, **kwargs)
    return Starlette(routes=routes)


def create_mount(
    prefix: str = "/explorer",
    *,
    tools: ToolsProvider,
    handle_call: ToolCallHandler,
    **kwargs: Any,
) -> Mount:
    """Create a Starlette ``Mount`` for embedding the UI under a URL prefix.

    Convenience wrapper for Starlette/FastAPI apps::

        app.routes.append(create_mount(tools=tools, handle_call=handler))

    All keyword arguments are forwarded to :func:`build_ui_routes`.
    """
    routes = build_ui_routes(tools, handle_call, **kwargs)
    return Mount(prefix, routes=routes)


# ---------------------------------------------------------------------------
# Backward compatibility
# ---------------------------------------------------------------------------

def build_mcp_ui_routes(
    tools: ToolsProvider,
    handle_call: ToolCallHandler,
    **kwargs: Any,
) -> list[Route]:
    """Deprecated: use :func:`build_ui_routes` instead."""
    warnings.warn(
        "build_mcp_ui_routes is deprecated, use build_ui_routes instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return build_ui_routes(tools, handle_call, **kwargs)
