#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "fastmcp>=2.12.4",
# ]
# ///
"""Bearer token authenticated MCP test server.

This server requires a bearer token for authentication.
Use: Authorization: Bearer test-token-12345

Example usage:
    python tests/test_server_bearer.py

Then connect with:
    from mcp2py import load
    server = load("http://localhost:8000/sse",
                  headers={"Authorization": "Bearer test-token-12345"})
"""

from fastmcp import FastMCP
from fastmcp.server import Context
from pydantic import BaseModel

# Create FastMCP server with custom middleware
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to check bearer token authentication."""

    async def dispatch(self, request, call_next):
        """Check for valid bearer token."""
        # Skip auth for OPTIONS requests (CORS)
        if request.method == "OPTIONS":
            return await call_next(request)

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

        # Token is valid, proceed
        response = await call_next(request)
        return response


# Create FastMCP server with middleware
mcp = FastMCP(
    "bearer-auth-server",
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
    return f"Echo (Bearer Auth): {message}"


@mcp.tool()
def add(a: float, b: float) -> str:
    """Add two numbers together.

    Args:
        a: First number
        b: Second number
    """
    result = a + b
    return f"Result (Bearer Auth): {result}"


@mcp.tool()
def get_user_info() -> str:
    """Get authenticated user information."""
    return "User authenticated with bearer token: test-token-12345"


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

    return f"Sentiment (Bearer Auth): {sentiment.strip()}"


# ============================================================================
# RESOURCES
# ============================================================================

@mcp.resource("resource://documentation")
def get_documentation() -> str:
    """API documentation for bearer auth server."""
    return """# Bearer Token Authentication Server

This server requires bearer token authentication.

## Authentication

Include the Authorization header:
```
Authorization: Bearer test-token-12345
```

## Available Tools

- echo(message: str) - Echo a message
- add(a: float, b: float) - Add two numbers
- get_user_info() - Get authenticated user info
- analyze_sentiment(text: str) - Analyze sentiment (requires sampling)

## Example

```python
from mcp2py import load

server = load(
    "http://localhost:8000/sse",
    headers={"Authorization": "Bearer test-token-12345"}
)

result = server.echo(message="Hello!")
print(result)
```
"""


@mcp.resource("resource://auth-info")
def get_auth_info() -> str:
    """Authentication information."""
    import json
    return json.dumps({
        "type": "bearer",
        "token_format": "Bearer <token>",
        "test_token": "test-token-12345",
        "header_name": "Authorization"
    }, indent=2)


# ============================================================================
# PROMPTS
# ============================================================================

@mcp.prompt()
def review_code(code: str, focus: str = "general quality") -> str:
    """Generate a code review prompt for Python code.

    Args:
        code: Python code to review
        focus: Specific aspect to focus on
    """
    return f"""Please review the following Python code with a focus on {focus}:

```python
{code}
```

Provide feedback on:
1. Code correctness and potential bugs
2. Code style and readability
3. Security considerations
4. Best practices

Be specific and constructive in your feedback."""


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Bearer Token Authentication Server")
    print("=" * 70)
    print("\nServer will run on: http://localhost:8000")
    print("MCP endpoint: http://localhost:8000/sse")
    print("\nRequired token: test-token-12345")
    print("\nExample usage:")
    print('  from mcp2py import load')
    print('  server = load("http://localhost:8000/sse",')
    print('                headers={"Authorization": "Bearer test-token-12345"})')
    print('  print(server.echo(message="Hello!"))')
    print("=" * 70)
    print()

    # Run with FastMCP's built-in method
    mcp.run(transport="sse", host="0.0.0.0", port=8000)
