from contextlib import contextmanager

import uvicorn
from fastapi import FastAPI, Request

from mcp_embedded_ui import create_mount

app = FastAPI()


# Mock MCP tools
class MockTool:
    def __init__(self, name, description, input_schema):
        self.name = name
        self.description = description
        self.inputSchema = input_schema


tools = [
    MockTool("echo", "Replies back with your message", {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
        },
    }),
    MockTool("add", "Add two numbers", {
        "type": "object",
        "properties": {
            "a": {"type": "number"},
            "b": {"type": "number"},
        },
    }),
]


# Tool execution handler
async def handle_tool_call(name, args):
    if name == "echo":
        return [{"type": "text", "text": f"You said: {args.get('message')}"}], False, "trace-123"
    if name == "add":
        result = args.get("a", 0) + args.get("b", 0)
        return [{"type": "text", "text": f"Result: {result}"}], False, "trace-456"
    return [{"type": "text", "text": f"Unknown tool: {name}"}], True, None


DEMO_TOKEN = "demo-secret-token"


# Auth hook — guards POST /tools/{name}/call only; discovery endpoints are always public.
# In production, replace with your own logic (JWT, API key, session, etc.).
@contextmanager
def my_auth_hook(request: Request):
    token = request.headers.get("authorization", "")
    if token != f"Bearer {DEMO_TOKEN}":
        raise ValueError("Invalid token")
    yield


# One-liner mount (defaults to /explorer)
app.routes.append(
    create_mount(
        tools=tools,
        handle_call=handle_tool_call,
        auth_hook=my_auth_hook,
        title="My MCP Explorer",
    )
)

if __name__ == "__main__":
    print("Running MCP Embedded UI at http://localhost:8000/explorer")
    print(f"Auth token for demo: Bearer {DEMO_TOKEN}")
    print("Paste the token above into the UI's token field to execute tools")
    uvicorn.run(app, host="0.0.0.0", port=8000)
