# mcp-embedded-ui (Python)

The Python implementation of [mcp-embedded-ui](https://github.com/aipartnerup/mcp-embedded-ui) — a browser-based tool explorer for any [MCP](https://modelcontextprotocol.io/) (Model Context Protocol) server.

## What is this?

If you build an MCP server in Python, your users interact with tools through raw JSON — no visual feedback, no schema browser, no quick way to test. This library adds a full browser UI to your server with **one import and one mount**.

```
┌───────────────────────────────────┐
│  Browser                          │
│  Tool list → Schema → Try it      │
└──────────────┬────────────────────┘
               │ HTTP / JSON
┌──────────────▼────────────────────┐
│  Your Python MCP Server           │
│  + mcp-embedded-ui                │
│    (FastAPI / Starlette / ASGI)   │
└───────────────────────────────────┘
```

## What does the UI provide?

- **Tool list** — browse all registered tools with descriptions and annotation badges
- **Schema inspector** — expand any tool to view its full JSON Schema (`inputSchema`)
- **Try-it console** — type JSON arguments, execute the tool, see results instantly
- **cURL export** — copy a ready-made cURL command for any execution
- **Auth support** — enter a Bearer token in the UI, sent with all requests

No build step. No CDN. No external dependencies. The entire UI is a single self-contained HTML page embedded in the package.

## Install

```bash
pip install mcp-embedded-ui
```

Requires Python 3.10+ and [Starlette](https://www.starlette.io/) >= 0.14.

## Quick Start

### FastAPI / Starlette

```python
from fastapi import FastAPI
from mcp_embedded_ui import create_mount

app = FastAPI()

# Mount at /explorer (default), enable tool execution
app.routes.append(create_mount(tools=my_tools, handle_call=my_handler, allow_execute=True))

# Or specify a custom prefix
app.routes.append(create_mount("/mcp-ui", tools=my_tools, handle_call=my_handler, allow_execute=True))

# Visit http://localhost:8000/explorer/
```

### Any ASGI framework

```python
from mcp_embedded_ui import create_app

# Returns a standard ASGI app — mount in any ASGI-compatible framework
ui_app = create_app(tools=my_tools, handle_call=my_handler, allow_execute=True)
```

### Full working example

```python
from fastapi import FastAPI
from mcp_embedded_ui import create_mount

# 1. Define your tools (any object with .name, .description, .inputSchema)
class MyTool:
    def __init__(self, name, description, input_schema):
        self.name = name
        self.description = description
        self.inputSchema = input_schema

tools = [
    MyTool("greet", "Say hello", {
        "type": "object",
        "properties": {"name": {"type": "string"}},
    }),
]

# 2. Define a handler: (name, args) -> (content, is_error, trace_id)
async def handle_call(name, args):
    if name == "greet":
        return [{"type": "text", "text": f"Hello, {args.get('name', 'world')}!"}], False, None
    return [{"type": "text", "text": f"Unknown tool: {name}"}], True, None

# 3. Mount the UI
app = FastAPI()
app.routes.append(create_mount(tools=tools, handle_call=handle_call, allow_execute=True))
```

### With auth hook

```python
from contextlib import contextmanager
from fastapi import Request

@contextmanager
def my_auth(request: Request):
    token = request.headers.get("authorization", "")
    if not token.startswith("Bearer "):
        raise ValueError("Unauthorized")
    # Verify the token with your own logic (JWT, API key, session, etc.)
    yield

# Pass auth_hook to enable, omit to disable
app.routes.append(create_mount(
    tools=tools,
    handle_call=handle_call,
    allow_execute=True,
    auth_hook=my_auth,
))
```

Auth only guards `POST /tools/{name}/call`. Discovery endpoints are always public. The UI has a built-in token input field — enter your Bearer token there and it's sent with every execution request.

The included demo (`examples/fastapi_demo.py`) uses a hardcoded `Bearer demo-secret-token` — the token is printed at startup so you know what to paste into the UI.

### Dynamic tools

```python
# Sync callable — re-evaluated on every request
def get_tools():
    return registry.list_tools()

# Async callable
async def get_tools():
    return await registry.async_list_tools()

app = create_app(tools=get_tools, handle_call=my_handler, allow_execute=True)
```

## API

### Three-tier API

| Function | Returns | Use case |
|----------|---------|----------|
| `create_mount(prefix, *, tools, handle_call, **config)` | `Mount` | FastAPI / Starlette — mount under a URL prefix |
| `create_app(tools, handle_call, **config)` | `ASGIApp` | Any ASGI framework — standalone app |
| `build_ui_routes(tools, handle_call, **config)` | `list[Route]` | Power users — fine-grained route control |

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `tools` | `list \| Callable \| AsyncCallable` | _required_ | MCP Tool objects (`.name`, `.description`, `.inputSchema`) |
| `handle_call` | `ToolCallHandler` | _required_ | `async (name, args) -> (content, is_error, trace_id)` |
| `allow_execute` | `bool` | `False` | Enable/disable tool execution (enforced server-side) |
| `auth_hook` | `AuthHook \| None` | `None` | Sync/async context manager factory for auth |
| `title` | `str` | `"MCP Tool Explorer"` | Page title (HTML-escaped automatically) |
| `project_name` | `str \| None` | `None` | Project name shown in footer |
| `project_url` | `str \| None` | `None` | Project URL linked in footer (requires `project_name`) |

### Auth Hook

The `auth_hook` receives a Starlette `Request` and returns a context manager (sync or async). Raise inside to reject with 401. The error response is always `{"error": "Unauthorized"}` — internal details are never leaked.

```python
from contextlib import contextmanager

@contextmanager
def my_auth(request):
    token = request.headers.get("Authorization")
    if not valid(token):
        raise ValueError("Bad token")
    my_identity_var.set(decode(token))
    yield
```

Auth only guards `POST /tools/{name}/call`. Discovery endpoints (`GET /tools`, `GET /tools/{name}`) are always public.

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Self-contained HTML explorer page |
| GET | `/tools` | Summary list of all tools |
| GET | `/tools/{name}` | Full tool detail with `inputSchema` |
| POST | `/tools/{name}/call` | Execute a tool, returns MCP `CallToolResult` |

## Development

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run the demo (auth enabled with a demo token)
python examples/fastapi_demo.py
# Visit http://localhost:8000/explorer/
# Paste "Bearer demo-secret-token" in the UI's token field to execute tools

# Run tests
pytest
```

## Cross-Language Specification

This package implements the [mcp-embedded-ui](https://github.com/aipartnerup/mcp-embedded-ui) specification. The spec repo contains:

- [PROTOCOL.md](https://github.com/aipartnerup/mcp-embedded-ui/blob/main/docs/PROTOCOL.md) — endpoint spec, data shapes, security checklist
- [explorer.html](https://github.com/aipartnerup/mcp-embedded-ui/blob/main/docs/explorer.html) — shared HTML template (identical across all language implementations)
- [Feature specs](https://github.com/aipartnerup/mcp-embedded-ui/blob/main/docs/features/MANIFEST.md) — detailed requirements and test criteria

## License

Apache-2.0
