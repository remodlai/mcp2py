#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "fastmcp>=2.12.4",
# ]
# ///
"""OAuth authenticated MCP test server.

This server requires OAuth authentication.
FastMCP will handle the OAuth flow automatically.

Example usage:
    python tests/test_server_oauth.py

Then connect with:
    from mcp2py import load
    server = load("http://localhost:8001/mcp/sse", auth="oauth")
    # Browser will open for OAuth login
"""

from fastmcp import FastMCP
from fastmcp.server import Context
from fastmcp.server.auth import AuthProvider
from pydantic import BaseModel

# Create FastMCP server with OAuth
mcp = FastMCP(
    "oauth-server",
    auth=AuthProvider.GOOGLE  # Google OAuth
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
    return f"Echo (OAuth): {message}"


@mcp.tool()
def add(a: float, b: float) -> str:
    """Add two numbers together.

    Args:
        a: First number
        b: Second number
    """
    result = a + b
    return f"Result (OAuth): {result}"


@mcp.tool()
def get_user_info(ctx: Context) -> str:
    """Get authenticated user information from OAuth."""
    user = ctx.user
    if user:
        return f"Authenticated user: {user.email or user.id}"
    return "No user information available"


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

    return f"Sentiment (OAuth): {sentiment.strip()}"


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
        return f"Action '{action}' confirmed and executed! (OAuth)"
    else:
        return f"Action '{action}' cancelled. (OAuth)"


# ============================================================================
# RESOURCES
# ============================================================================

@mcp.resource("resource://documentation")
def get_documentation() -> str:
    """API documentation for OAuth server."""
    return """# OAuth Authentication Server

This server requires OAuth authentication via Google.

## Authentication

FastMCP handles OAuth automatically. When you connect:
1. Browser opens to Google login
2. You log in with your Google account
3. Token is stored and auto-refreshed

## Available Tools

- echo(message: str) - Echo a message
- add(a: float, b: float) - Add two numbers
- get_user_info() - Get OAuth user information
- analyze_sentiment(text: str) - Analyze sentiment (requires sampling)
- confirm_action(action: str) - Confirm an action (requires elicitation)

## Example

```python
from mcp2py import load

# Browser opens automatically for OAuth
server = load("http://localhost:8001/mcp/sse", auth="oauth")

result = server.echo(message="Hello!")
print(result)

# Get authenticated user info
user = server.get_user_info()
print(user)
```

## Token Storage

Tokens are cached in: ~/.fastmcp/oauth-mcp-client-cache/
"""


@mcp.resource("resource://auth-info")
def get_auth_info() -> str:
    """Authentication information."""
    import json
    return json.dumps({
        "type": "oauth",
        "provider": "google",
        "scopes": ["openid", "email", "profile"],
        "token_storage": "~/.fastmcp/oauth-mcp-client-cache/"
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


@mcp.prompt()
def generate_readme(project_name: str, description: str) -> str:
    """Generate a README.md template.

    Args:
        project_name: Name of the project
        description: Short description
    """
    return f"""Generate a comprehensive README.md for:

**Project:** {project_name}
**Description:** {description}

Include:
1. Project title and description
2. Installation instructions
3. Quick start guide
4. Usage examples
5. Contributing guidelines
6. License information
"""


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("OAuth Authentication Server (Google)")
    print("=" * 70)
    print("\nServer will run on: http://localhost:8001")
    print("MCP endpoint: http://localhost:8001/mcp/sse")
    print("\nAuthentication: Google OAuth")
    print("Browser will open for login on first connection")
    print("\nExample usage:")
    print('  server = load("http://localhost:8001/mcp/sse", auth="oauth")')
    print('  # Browser opens for Google login')
    print("=" * 70)
    print()

    # Note: OAuth configuration may need environment variables
    print("NOTE: This requires Google OAuth credentials.")
    print("Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables.")
    print()

    # Run with FastMCP's built-in method
    mcp.run(transport="sse", host="0.0.0.0", port=8001)
