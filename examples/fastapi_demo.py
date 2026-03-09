import uvicorn
from fastapi import FastAPI, Request
from contextlib import contextmanager

from mcp_embedded_ui import create_mount

app = FastAPI()


# Mock MCP tools
class MockTool:
    def __init__(self, name, description):
        self.name = name
        self.description = description
        self.inputSchema = {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
            },
        }


tools = [
    MockTool("echo", "Replies back with your message"),
    MockTool("add", "Add two numbers"),
]


# Tool execution handler
async def handle_tool_call(name, args):
    if name == "echo":
        return [{"type": "text", "text": f"You said: {args.get('message')}"}], False, "trace-123"
    return [{"type": "text", "text": "Result: 42"}], False, "trace-456"


# Auth hook example (use your own ContextVar to propagate identity downstream)
@contextmanager
def my_auth_hook(request: Request):
    # token = request.headers.get("Authorization")
    # if not token: raise Exception("Missing token")
    yield  # raise here to reject the request with 401


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
    uvicorn.run(app, host="0.0.0.0", port=8000)
