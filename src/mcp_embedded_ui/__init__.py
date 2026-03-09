
from importlib.metadata import PackageNotFoundError, version

from .server import (
    AuthHook,
    CallResult,
    ToolCallHandler,
    ToolsProvider,
    build_mcp_ui_routes,
    build_ui_routes,
    create_app,
    create_mount,
)

try:
    __version__ = version("mcp-embedded-ui")
except PackageNotFoundError:
    __version__ = "unknown"

__all__ = [
    "AuthHook",
    "CallResult",
    "ToolCallHandler",
    "ToolsProvider",
    "build_mcp_ui_routes",
    "build_ui_routes",
    "create_app",
    "create_mount",
]
