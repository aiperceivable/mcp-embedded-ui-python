"""Self-contained HTML page for the MCP Tool Explorer."""

from html import escape
from importlib.resources import files

_EXPLORER_HTML_TEMPLATE = files(__package__).joinpath("explorer.html").read_text(encoding="utf-8")

_DEFAULT_TITLE = "MCP Tool Explorer"


def _build_project_link(project_name: str | None, project_url: str | None) -> str:
    if not project_name and not project_url:
        return ""
    name = escape(project_name or "")
    if project_url:
        url = escape(project_url, quote=True)
        return (
            f' &middot; <a href="{url}" style="color:#888;text-decoration:none"'
            f' target="_blank" rel="noopener">{name}</a>'
        )
    return f" &middot; {name}"


def render_explorer_html(
    title: str = _DEFAULT_TITLE,
    *,
    allow_execute: bool = False,
    project_name: str | None = None,
    project_url: str | None = None,
) -> str:
    """Render the explorer HTML page with the given title."""
    return (
        _EXPLORER_HTML_TEMPLATE
        .replace("{{TITLE}}", escape(title))
        .replace("{{ALLOW_EXECUTE}}", "true" if allow_execute else "false")
        .replace("{{PROJECT_LINK}}", _build_project_link(project_name, project_url))
    )
