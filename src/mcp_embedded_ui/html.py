"""Self-contained HTML page for the MCP Tool Explorer."""

from html import escape
from importlib.resources import files

_EXPLORER_HTML_TEMPLATE = files(__package__).joinpath("explorer.html").read_text(encoding="utf-8")

_DEFAULT_TITLE = "MCP Tool Explorer"


_ALLOWED_URL_SCHEMES = ("http://", "https://", "mailto:")

#: Characters a browser ignores while resolving a URL scheme.
_SCHEME_NOISE = {0x09: None, 0x0A: None, 0x0D: None}  # TAB, LF, CR


def _is_safe_url(url: str) -> bool:
    """Whether ``url`` may be placed in an ``href``.

    HTML escaping alone does not neutralise ``javascript:`` -- that string
    contains no character an escaper would touch. Browsers also ignore
    TAB/LF/CR and surrounding whitespace while resolving a scheme, so
    ``java\tscript:alert(1)`` resolves to ``javascript:alert(1)``; strip those
    before testing rather than after. See PROTOCOL.md security checklist.
    """
    cleaned = url.translate(_SCHEME_NOISE).strip()
    return cleaned.startswith("/") or cleaned.lower().startswith(_ALLOWED_URL_SCHEMES)


def _build_project_link(project_name: str | None, project_url: str | None) -> str:
    if not project_name and not project_url:
        return ""
    name = escape(project_name or "")
    if project_url and _is_safe_url(project_url):
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
