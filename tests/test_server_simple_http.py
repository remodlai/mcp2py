#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "fastmcp>=2.12.4",
# ]
# ///
"""Simple HTTP MCP test server WITHOUT authentication.

For testing HTTP transport without auth complications.

Example usage:
    python tests/test_server_simple_http.py

Then connect with:
    from mcp2py import load
    server = load("http://localhost:8000/sse")
"""

from fastmcp import FastMCP

# Create FastMCP server WITHOUT middleware
mcp = FastMCP("simple-http-server")


@mcp.tool()
def echo(message: str) -> str:
    """Echo back the input message.

    Args:
        message: Message to echo back
    """
    return f"Echo (HTTP): {message}"


@mcp.tool()
def add(a: float, b: float) -> str:
    """Add two numbers together.

    Args:
        a: First number
        b: Second number
    """
    result = a + b
    return f"Result (HTTP): {result}"


@mcp.resource("resource://test")
def get_test() -> str:
    """Test resource."""
    return "Test resource content"


if __name__ == "__main__":
    print("=" * 70)
    print("Simple HTTP MCP Server (NO AUTH)")
    print("=" * 70)
    print("\nServer will run on: http://localhost:8000")
    print("MCP endpoint: http://localhost:8000/sse")
    print("\nExample usage:")
    print('  from mcp2py import load')
    print('  server = load("http://localhost:8000/sse")')
    print('  print(server.echo(message="Hello!"))')
    print("=" * 70)
    print()

    # Run with FastMCP's built-in method
    mcp.run(transport="sse", host="0.0.0.0", port=8000)
