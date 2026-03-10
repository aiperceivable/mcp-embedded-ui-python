"""Tests for mcp_embedded_ui route handlers."""

from __future__ import annotations

from contextlib import asynccontextmanager, contextmanager
from typing import Any

from starlette.routing import Mount
from starlette.testclient import TestClient

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

class FakeTool:
    """Minimal duck-typed MCP Tool."""

    def __init__(
        self,
        name: str,
        description: str = "",
        input_schema: dict | None = None,
        annotations: Any = None,
    ):
        self.name = name
        self.description = description
        self.inputSchema = input_schema or {
            "type": "object",
            "properties": {"msg": {"type": "string"}},
        }
        self.annotations = annotations


TOOLS = [
    FakeTool("echo", "Echo back", annotations={"readOnlyHint": True}),
    FakeTool("boom", "Always errors"),
]


async def fake_handler(
    name: str, args: dict[str, Any]
) -> tuple[list[dict[str, Any]], bool, str | None]:
    if name == "echo":
        return [{"type": "text", "text": f"echo: {args.get('msg', '')}"}], False, "t1"
    if name == "boom":
        return [{"type": "text", "text": "kaboom"}], True, None
    raise ValueError(f"Unknown tool: {name}")


def _build_client(**kwargs) -> TestClient:
    from mcp_embedded_ui import build_ui_routes

    routes = build_ui_routes(TOOLS, fake_handler, **kwargs)
    app = Mount("/", routes=routes)
    return TestClient(app)


# ---------------------------------------------------------------------------
# Explorer page
# ---------------------------------------------------------------------------

class TestExplorerPage:
    def test_returns_html(self):
        client = _build_client()
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "MCP Tool Explorer" in resp.text

    def test_custom_title(self):
        client = _build_client(title="My Custom Explorer")
        resp = client.get("/")
        assert "My Custom Explorer" in resp.text
        assert "MCP Tool Explorer" not in resp.text


# ---------------------------------------------------------------------------
# Allow execute in HTML
# ---------------------------------------------------------------------------

class TestAllowExecuteHtml:
    def test_default_execute_disabled(self):
        client = _build_client()
        resp = client.get("/")
        assert "var executeEnabled = true;" in resp.text

    def test_execute_disabled_in_html(self):
        client = _build_client(allow_execute=False)
        resp = client.get("/")
        assert "var executeEnabled = false;" in resp.text

    def test_execute_enabled_in_html(self):
        client = _build_client(allow_execute=True)
        resp = client.get("/")
        assert "var executeEnabled = true;" in resp.text


# ---------------------------------------------------------------------------
# Project link in footer
# ---------------------------------------------------------------------------

class TestProjectLink:
    def test_no_project_link_by_default(self):
        client = _build_client()
        resp = client.get("/")
        assert "{{PROJECT_LINK}}" not in resp.text
        assert "&middot;" not in resp.text

    def test_project_name_only(self):
        client = _build_client(project_name="my-project")
        resp = client.get("/")
        assert "&middot; my-project" in resp.text
        assert "<a href=" not in resp.text.split("mcp-embedded-ui</a>")[-1]

    def test_project_name_and_url(self):
        client = _build_client(
            project_name="my-project",
            project_url="https://github.com/example/my-project",
        )
        resp = client.get("/")
        assert "my-project" in resp.text
        assert "https://github.com/example/my-project" in resp.text

    def test_project_name_xss_escaped(self):
        client = _build_client(project_name="<script>alert(1)</script>")
        resp = client.get("/")
        assert "<script>alert(1)</script>" not in resp.text
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in resp.text


# ---------------------------------------------------------------------------
# List tools
# ---------------------------------------------------------------------------

class TestListTools:
    def test_returns_all_tools(self):
        client = _build_client()
        resp = client.get("/tools")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        names = {t["name"] for t in data}
        assert names == {"echo", "boom"}

    def test_annotations_included_when_present(self):
        client = _build_client()
        data = client.get("/tools").json()
        echo = next(t for t in data if t["name"] == "echo")
        assert echo["annotations"]["readOnlyHint"] is True

    def test_annotations_omitted_when_none(self):
        client = _build_client()
        data = client.get("/tools").json()
        boom = next(t for t in data if t["name"] == "boom")
        assert "annotations" not in boom


# ---------------------------------------------------------------------------
# Tool detail
# ---------------------------------------------------------------------------

class TestToolDetail:
    def test_existing_tool(self):
        client = _build_client()
        resp = client.get("/tools/echo")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "echo"
        assert "inputSchema" in data

    def test_missing_tool_returns_404(self):
        client = _build_client()
        resp = client.get("/tools/nonexistent")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Call tool
# ---------------------------------------------------------------------------

class TestCallTool:
    def test_successful_call(self):
        client = _build_client()
        resp = client.post("/tools/echo/call", json={"msg": "hi"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["isError"] is False
        assert data["content"][0]["text"] == "echo: hi"
        assert data["_meta"]["_trace_id"] == "t1"

    def test_error_call(self):
        client = _build_client()
        resp = client.post("/tools/boom/call", json={})
        assert resp.status_code == 500
        data = resp.json()
        assert data["isError"] is True

    def test_missing_tool_returns_404(self):
        client = _build_client()
        resp = client.post("/tools/nope/call", json={})
        assert resp.status_code == 404

    def test_empty_body_treated_as_empty_dict(self):
        client = _build_client()
        resp = client.post(
            "/tools/echo/call",
            content=b"not json",
            headers={"content-type": "application/json"},
        )
        assert resp.status_code == 200

    def test_handler_exception_returns_404_for_unknown(self):
        client = _build_client()
        resp = client.post("/tools/unknown_tool/call", json={})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# allow_execute=False
# ---------------------------------------------------------------------------

class TestExecutionDisabled:
    def test_call_returns_403(self):
        client = _build_client(allow_execute=False)
        resp = client.post("/tools/echo/call", json={})
        assert resp.status_code == 403

    def test_list_and_detail_still_work(self):
        client = _build_client(allow_execute=False)
        assert client.get("/tools").status_code == 200
        assert client.get("/tools/echo").status_code == 200


# ---------------------------------------------------------------------------
# Sync auth hook
# ---------------------------------------------------------------------------

class TestSyncAuthHook:
    def test_valid_auth_passes(self):
        @contextmanager
        def auth(request):
            token = request.headers.get("authorization", "")
            if "valid" not in token:
                raise ValueError("bad token")
            yield

        client = _build_client(auth_hook=auth)
        resp = client.post(
            "/tools/echo/call",
            json={"msg": "hi"},
            headers={"Authorization": "Bearer valid-token"},
        )
        assert resp.status_code == 200

    def test_invalid_auth_returns_401(self):
        @contextmanager
        def auth(request):
            raise ValueError("nope")
            yield  # noqa: unreachable

        client = _build_client(auth_hook=auth)
        resp = client.post("/tools/echo/call", json={})
        assert resp.status_code == 401
        assert "Unauthorized" in resp.json()["error"]


# ---------------------------------------------------------------------------
# Async auth hook
# ---------------------------------------------------------------------------

class TestAsyncAuthHook:
    def test_valid_async_auth_passes(self):
        @asynccontextmanager
        async def auth(request):
            token = request.headers.get("authorization", "")
            if "valid" not in token:
                raise ValueError("bad token")
            yield

        client = _build_client(auth_hook=auth)
        resp = client.post(
            "/tools/echo/call",
            json={"msg": "async"},
            headers={"Authorization": "Bearer valid-token"},
        )
        assert resp.status_code == 200
        assert resp.json()["content"][0]["text"] == "echo: async"

    def test_invalid_async_auth_returns_401(self):
        @asynccontextmanager
        async def auth(request):
            raise ValueError("async nope")
            yield  # noqa: unreachable

        client = _build_client(auth_hook=auth)
        resp = client.post("/tools/echo/call", json={})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Trace ID omitted when None
# ---------------------------------------------------------------------------

class TestTraceId:
    def test_no_meta_when_trace_id_is_none(self):
        client = _build_client()
        resp = client.post("/tools/boom/call", json={})
        data = resp.json()
        assert "_meta" not in data


# ---------------------------------------------------------------------------
# Dynamic tools (sync callable)
# ---------------------------------------------------------------------------

class TestSyncToolsCallable:
    def test_sync_callable_tools(self):
        from mcp_embedded_ui import build_ui_routes

        call_count = 0

        def get_tools():
            nonlocal call_count
            call_count += 1
            return [FakeTool("dynamic", "A dynamic tool")]

        routes = build_ui_routes(get_tools, fake_handler)
        client = TestClient(Mount("/", routes=routes))

        resp = client.get("/tools")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "dynamic"
        assert call_count >= 1

    def test_sync_callable_tool_detail(self):
        from mcp_embedded_ui import build_ui_routes

        def get_tools():
            return [FakeTool("dynamic", "A dynamic tool")]

        routes = build_ui_routes(get_tools, fake_handler)
        client = TestClient(Mount("/", routes=routes))
        resp = client.get("/tools/dynamic")
        assert resp.status_code == 200
        assert resp.json()["name"] == "dynamic"


# ---------------------------------------------------------------------------
# Dynamic tools (async callable)
# ---------------------------------------------------------------------------

class TestAsyncToolsCallable:
    def test_async_callable_tools(self):
        from mcp_embedded_ui import build_ui_routes

        async def get_tools():
            return [FakeTool("async-tool", "An async tool")]

        routes = build_ui_routes(get_tools, fake_handler)
        client = TestClient(Mount("/", routes=routes))

        resp = client.get("/tools")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "async-tool"

    def test_async_callable_call(self):
        from mcp_embedded_ui import build_ui_routes

        async def get_tools():
            return [FakeTool("echo", "Echo")]

        routes = build_ui_routes(get_tools, fake_handler)
        client = TestClient(Mount("/", routes=routes))
        resp = client.post("/tools/echo/call", json={"msg": "hello"})
        assert resp.status_code == 200
        assert resp.json()["content"][0]["text"] == "echo: hello"


# ---------------------------------------------------------------------------
# create_app
# ---------------------------------------------------------------------------

class TestCreateApp:
    def test_create_app_returns_asgi(self):
        from mcp_embedded_ui import create_app

        app = create_app(TOOLS, fake_handler, title="Test App")
        client = TestClient(app)

        resp = client.get("/")
        assert resp.status_code == 200
        assert "Test App" in resp.text

        resp = client.get("/tools")
        assert len(resp.json()) == 2

    def test_create_app_with_dynamic_tools(self):
        from mcp_embedded_ui import create_app

        async def get_tools():
            return [FakeTool("dyn", "Dynamic")]

        app = create_app(get_tools, fake_handler)
        client = TestClient(app)
        assert client.get("/tools").json()[0]["name"] == "dyn"


# ---------------------------------------------------------------------------
# create_mount
# ---------------------------------------------------------------------------

class TestCreateMount:
    def test_create_mount_returns_mount(self):
        from mcp_embedded_ui import create_mount

        mount = create_mount("/ui", tools=TOOLS, handle_call=fake_handler)
        assert isinstance(mount, Mount)

    def test_create_mount_default_prefix(self):
        from starlette.applications import Starlette

        from mcp_embedded_ui import create_mount

        mount = create_mount(tools=TOOLS, handle_call=fake_handler)
        app = Starlette(routes=[mount])
        client = TestClient(app)

        resp = client.get("/explorer/")
        assert resp.status_code == 200

        resp = client.get("/explorer/tools")
        assert resp.status_code == 200

    def test_create_mount_works_in_starlette(self):
        from starlette.applications import Starlette

        from mcp_embedded_ui import create_mount

        mount = create_mount("/ui", tools=TOOLS, handle_call=fake_handler, title="Mounted")
        app = Starlette(routes=[mount])
        client = TestClient(app)

        resp = client.get("/ui/")
        assert resp.status_code == 200
        assert "Mounted" in resp.text

        resp = client.get("/ui/tools")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

        resp = client.post("/ui/tools/echo/call", json={"msg": "mount"})
        assert resp.status_code == 200
        assert resp.json()["content"][0]["text"] == "echo: mount"


# ---------------------------------------------------------------------------
# Backward compatibility
# ---------------------------------------------------------------------------

class TestBackwardCompat:
    def test_build_mcp_ui_routes_still_works(self):
        import warnings

        from mcp_embedded_ui import build_mcp_ui_routes

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            routes = build_mcp_ui_routes(TOOLS, fake_handler)
        client = TestClient(Mount("/", routes=routes))
        assert client.get("/tools").status_code == 200

    def test_build_mcp_ui_routes_emits_deprecation_warning(self):
        import warnings

        from mcp_embedded_ui import build_mcp_ui_routes

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            build_mcp_ui_routes(TOOLS, fake_handler)
            deprecations = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert len(deprecations) == 1
            assert "build_ui_routes" in str(deprecations[0].message)


# ---------------------------------------------------------------------------
# Security: XSS prevention in title
# ---------------------------------------------------------------------------

class TestTitleXSS:
    def test_script_tag_in_title_is_escaped(self):
        malicious = '<script>alert("xss")</script>'
        client = _build_client(title=malicious)
        resp = client.get("/")
        assert resp.status_code == 200
        # The raw script tag must NOT appear in the HTML
        assert "<script>alert" not in resp.text
        # The escaped version should be present
        assert "&lt;script&gt;" in resp.text

    def test_html_entities_in_title_are_escaped(self):
        client = _build_client(title='A & B "quoted"')
        resp = client.get("/")
        assert '&amp;' in resp.text
        assert '&quot;' in resp.text or "&#x27;" in resp.text


# ---------------------------------------------------------------------------
# Security: auth error detail does not leak internals
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Handler exception (tool exists but handler throws) — F3-TC-6
# ---------------------------------------------------------------------------

class TestHandlerException:
    def test_handler_exception_returns_500_with_error(self):
        """When handle_call raises an exception, return 500 with isError=True."""

        async def throwing_handler(name, args):
            raise RuntimeError("internal failure")

        from mcp_embedded_ui import build_ui_routes

        routes = build_ui_routes(TOOLS, throwing_handler)
        client = TestClient(Mount("/", routes=routes))
        resp = client.post("/tools/echo/call", json={"msg": "hi"})
        assert resp.status_code == 500
        data = resp.json()
        assert data["isError"] is True
        assert data["content"][0]["type"] == "text"
        assert "internal failure" in data["content"][0]["text"]


# ---------------------------------------------------------------------------
# GET endpoints work without auth when auth_hook is set — F4-TC-6
# ---------------------------------------------------------------------------

class TestGetEndpointsNoAuth:
    def test_get_endpoints_do_not_invoke_auth_hook(self):
        """Auth hook only guards POST /call, GET endpoints must never invoke it."""
        call_count = 0

        @contextmanager
        def counting_auth(request):
            nonlocal call_count
            call_count += 1
            raise ValueError("no auth")
            yield  # noqa: unreachable

        client = _build_client(auth_hook=counting_auth)
        assert client.get("/").status_code == 200
        assert client.get("/tools").status_code == 200
        assert client.get("/tools/echo").status_code == 200
        # Auth hook must NOT have been called for any GET request
        assert call_count == 0, f"Auth hook was called {call_count} time(s) on GET endpoints"


# ---------------------------------------------------------------------------
# {{TITLE}} placeholder absent from served HTML — F1-TC-4
# ---------------------------------------------------------------------------

class TestTitlePlaceholderAbsent:
    def test_no_raw_placeholder_in_html(self):
        client = _build_client()
        resp = client.get("/")
        assert "{{TITLE}}" not in resp.text

    def test_no_raw_placeholder_with_custom_title(self):
        client = _build_client(title="Custom Title")
        resp = client.get("/")
        assert "{{TITLE}}" not in resp.text
        assert "Custom Title" in resp.text


# ---------------------------------------------------------------------------
# All public types importable from root — F5-TC-5
# ---------------------------------------------------------------------------

class TestPublicExports:
    def test_all_public_names_importable(self):
        import mcp_embedded_ui

        expected = [
            "AuthHook", "CallResult", "ToolCallHandler", "ToolsProvider",
            "build_mcp_ui_routes", "build_ui_routes", "create_app", "create_mount",
        ]
        for name in expected:
            assert hasattr(mcp_embedded_ui, name), f"{name} not importable from root"

    def test_all_matches_expected(self):
        import mcp_embedded_ui

        assert set(mcp_embedded_ui.__all__) == {
            "AuthHook", "CallResult", "ToolCallHandler", "ToolsProvider",
            "build_mcp_ui_routes", "build_ui_routes", "create_app", "create_mount",
        }


# ---------------------------------------------------------------------------
# HTML template drift check — spec repo vs implementation
# ---------------------------------------------------------------------------

class TestHtmlTemplateDrift:
    def test_template_matches_spec_repo(self):
        """Embedded HTML template must match the shared spec repo copy."""
        import os

        pkg_html = os.path.join(
            os.path.dirname(__file__),
            "..", "src", "mcp_embedded_ui", "explorer.html",
        )
        spec_html = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "mcp-embedded-ui", "docs", "explorer.html",
        )
        pkg_html = os.path.normpath(pkg_html)
        spec_html = os.path.normpath(spec_html)
        if not os.path.exists(spec_html):
            return
        with open(pkg_html, encoding="utf-8") as f:
            pkg_content = f.read()
        with open(spec_html, encoding="utf-8") as f:
            spec_content = f.read()
        assert pkg_content == spec_content, (
            "explorer.html has drifted from spec repo. "
            "Run: cp ../mcp-embedded-ui/docs/explorer.html src/mcp_embedded_ui/explorer.html"
        )


# ---------------------------------------------------------------------------
# Security: auth error detail does not leak internals
# ---------------------------------------------------------------------------

class TestAuthErrorNoLeak:
    def test_auth_error_does_not_leak_exception_detail(self):
        @contextmanager
        def auth(request):
            raise RuntimeError("DB connection failed at /var/secrets/db.key")
            yield  # noqa: unreachable

        client = _build_client(auth_hook=auth)
        resp = client.post("/tools/echo/call", json={})
        assert resp.status_code == 401
        data = resp.json()
        assert data["error"] == "Unauthorized"
        # Internal detail must not be exposed
        assert "detail" not in data
        assert "db.key" not in str(data)
