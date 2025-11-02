#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "fastmcp>=2.12.4",
# ]
# ///
"""Full-featured HTTP MCP test server WITH bearer token authentication.

Same as test_server.py but runs on HTTP/SSE with bearer token auth.
Required token: test-token-12345
"""

from fastmcp import FastMCP
from fastmcp.server import Context
from pydantic import BaseModel
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to check bearer token authentication."""

    async def dispatch(self, request, call_next):
        """Check for valid bearer token."""
        # Skip auth for OPTIONS requests (CORS)
        if request.method == "OPTIONS":
            response = await call_next(request)
            return response

        # Check authentication
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                {"error": "Missing or invalid Authorization header"},
                status_code=401,
                headers={"WWW-Authenticate": 'Bearer realm="MCP Server"'}
            )

        token = auth_header.replace("Bearer ", "")
        if token != "test-token-12345":
            return JSONResponse(
                {"error": "Invalid bearer token"},
                status_code=401,
                headers={"WWW-Authenticate": 'Bearer realm="MCP Server"'}
            )

        # Token is valid - add to request state for downstream use
        request.state.authenticated = True
        request.state.token = token

        # Proceed with request
        response = await call_next(request)
        return response


# Create FastMCP server with bearer auth middleware
mcp = FastMCP(
    "test-server-http-auth",
    middleware=[Middleware(BearerAuthMiddleware)]
)


# ============================================================================
# MODELS
# ============================================================================

class ConfirmResponse(BaseModel):
    confirm: bool


# ============================================================================
# TOOLS
# ============================================================================

@mcp.tool()
def echo(message: str) -> str:
    """Echo back the input message.

    Args:
        message: Message to echo back
    """
    return f"Echo: {message}"


@mcp.tool()
def add(a: float, b: float) -> str:
    """Add two numbers together.

    Args:
        a: First number
        b: Second number
    """
    result = a + b
    return f"Result: {result}"


@mcp.tool()
async def analyze_sentiment(text: str, ctx: Context) -> str:
    """Analyze sentiment of text using LLM (triggers sampling).

    Args:
        text: Text to analyze for sentiment
    """
    from mcp.types import SamplingMessage, TextContent

    result = await ctx.session.create_message(
        messages=[
            SamplingMessage(
                role="user",
                content=TextContent(
                    type="text",
                    text=f"Analyze the sentiment of this text and respond with just one word (positive, negative, or neutral): {text}"
                )
            )
        ],
        max_tokens=10
    )

    if hasattr(result.content, 'text'):
        sentiment = result.content.text
    else:
        sentiment = str(result.content)

    return f"Sentiment: {sentiment.strip()}"


@mcp.tool()
async def confirm_action(action: str, ctx: Context) -> str:
    """Ask user to confirm an action (triggers elicitation).

    Args:
        action: Action to confirm with the user
    """
    result = await ctx.elicit(
        message=f"Do you want to {action}?",
        response_type=ConfirmResponse
    )

    if result and hasattr(result, 'data') and result.data and result.data.confirm:
        return f"Action '{action}' confirmed and executed!"
    else:
        return f"Action '{action}' cancelled."


# ============================================================================
# RESOURCES
# ============================================================================

@mcp.resource("resource://documentation")
def get_documentation() -> str:
    """Complete API documentation for mcp2py."""
    return """# mcp2py API Documentation

## Overview
mcp2py turns MCP servers into Python modules with a simple, synchronous API.

## Core Functions

### load(command, **kwargs)
Load an MCP server and return a Python interface.

**Parameters:**
- `command` (str | list[str]): Command to launch server or HTTP URL
- `headers` (dict): HTTP headers for remote servers
- `auth` (str | httpx.Auth): Authentication (bearer token or "oauth")
- `roots` (optional): Directory roots for the server
- `allow_sampling` (bool): Allow LLM sampling (default: True)
- `allow_elicitation` (bool): Allow user input prompts (default: True)

**Returns:** MCPServer object with tools as methods

**Example:**
```python
from mcp2py import load

# Local server (stdio)
server = load("npx -y @modelcontextprotocol/server-filesystem /tmp")

# Remote server (HTTP with auth)
server = load("https://api.example.com/mcp",
              headers={"Authorization": "Bearer token"})

result = server.list_directory(path="/tmp")
```

### register(**servers)
Register servers with friendly names.

**Example:**
```python
from mcp2py import register

register(
    weather="npx -y @h1deya/mcp-server-weather",
    fs="npx -y @modelcontextprotocol/server-filesystem /tmp"
)
```

## Classes

### MCPServer
Pythonic wrapper around MCP client.

**Properties:**
- `tools`: List of callable tool functions with proper signatures

**Methods:**
- Tool methods are generated dynamically from server capabilities

## Exceptions

- `MCPError`: Base exception for all mcp2py errors
- `MCPConnectionError`: Failed to connect to server
- `MCPToolError`: Tool execution failed
- `MCPResourceError`: Resource access failed
- `MCPPromptError`: Prompt execution failed
"""


@mcp.resource("resource://version")
def get_version() -> str:
    """Current version and build information."""
    import json
    import sys

    return json.dumps({
        "version": "0.5.0",
        "build": "20251020",
        "python_version": sys.version,
        "protocol_version": "2024-11-05",
        "http_support": True,
        "auth_support": True
    }, indent=2)


@mcp.resource("resource://stats")
def get_stats() -> str:
    """Real-time server statistics."""
    import json
    import time

    return json.dumps({
        "uptime_seconds": 0,
        "tools_called": 0,
        "last_call": None,
        "timestamp": time.time(),
        "transport": "http-sse"
    }, indent=2)


# ============================================================================
# PROMPTS
# ============================================================================

@mcp.prompt()
def review_code(code: str, focus: str = "general quality") -> str:
    """Generate a code review prompt for Python code.

    Args:
        code: Python code to review
        focus: Specific aspect to focus on (style, bugs, performance)
    """
    return f"""Please review the following Python code with a focus on {focus}:

```python
{code}
```

Provide feedback on:
1. Code correctness and potential bugs
2. Code style and readability
3. Performance considerations
4. Best practices and patterns
5. Suggestions for improvement

Be specific and constructive in your feedback."""


@mcp.prompt()
def generate_readme(project_name: str, description: str, features: str = "") -> str:
    """Generate a README.md template for a project.

    Args:
        project_name: Name of the project
        description: Short description of the project
        features: Comma-separated list of key features
    """
    features_list = ""
    if features:
        features_list = "\n".join(f"- {f.strip()}" for f in features.split(","))

    return f"""Generate a comprehensive README.md file for a project with these details:

**Project Name:** {project_name}
**Description:** {description}
**Key Features:**
{features_list}

The README should include:
1. Project title and description
2. Installation instructions
3. Quick start guide with code examples
4. Feature list
5. Usage examples
6. Contributing guidelines
7. License information

Make it professional, clear, and engaging."""


@mcp.prompt()
def explain_mcp() -> str:
    """Explain what MCP (Model Context Protocol) is."""
    return """Explain what the Model Context Protocol (MCP) is and why it's useful.

Cover:
1. What problem does MCP solve?
2. How does MCP work at a high level?
3. What are the key concepts (tools, resources, prompts)?
4. What are some practical use cases?
5. How does mcp2py make MCP easier to use from Python?

Provide a clear, concise explanation suitable for a developer new to MCP."""


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Full HTTP MCP Test Server WITH BEARER AUTH")
    print("=" * 70)
    print("\nServer will run on: http://localhost:8000")
    print("MCP endpoint: http://localhost:8000/sse")
    print("\nRequired token: test-token-12345")
    print("\nExample usage:")
    print('  from mcp2py import load')
    print('  server = load("http://localhost:8000/sse",')
    print('                headers={"Authorization": "Bearer test-token-12345"})')
    print('  print(server.echo(message="Hello!"))')
    print('  print(server.get_version())  # Resource')
    print('  print(server.explain_mcp())  # Prompt')
    print("\nOr use the auth parameter:")
    print('  server = load("http://localhost:8000/sse", auth="test-token-12345")')
    print("=" * 70)
    print()

    # Run with FastMCP's built-in method
    mcp.run(transport="sse", host="0.0.0.0", port=8000)
