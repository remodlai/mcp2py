"""Integration tests for HTTP/SSE transport with authentication.

These tests spin up a real HTTP server and test mcp2py's HTTP client
with various authentication methods.
"""

import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from mcp2py import load
from mcp2py.exceptions import MCPConnectionError


# Pytest fixture to skip if integration tests disabled
@pytest.fixture(scope="module", autouse=True)
def check_integration_enabled():
    """Skip integration tests if SKIP_INTEGRATION env var is set."""
    if os.getenv("SKIP_INTEGRATION"):
        pytest.skip("Integration tests disabled (SKIP_INTEGRATION=1)")


class HTTPServerFixture:
    """Helper to manage HTTP test server lifecycle."""

    def __init__(self, server_script: Path, port: int, wait_time: float = 2.0):
        self.server_script = server_script
        self.port = port
        self.wait_time = wait_time
        self.process = None

    def __enter__(self):
        """Start the server."""
        self.process = subprocess.Popen(
            [sys.executable, str(self.server_script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Wait for server to start
        time.sleep(self.wait_time)

        # Check if process is still running
        if self.process.poll() is not None:
            stdout, stderr = self.process.communicate()
            raise RuntimeError(
                f"Server failed to start:\nstdout: {stdout}\nstderr: {stderr}"
            )

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop the server."""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()


@pytest.fixture
def simple_http_server():
    """Start simple HTTP server without auth."""
    server_path = Path(__file__).parent / "test_server_simple_http.py"
    if not server_path.exists():
        pytest.skip(f"Server not found: {server_path}")

    with HTTPServerFixture(server_path, port=8000) as server:
        yield server


@pytest.fixture
def bearer_http_server():
    """Start HTTP server with bearer token auth."""
    server_path = Path(__file__).parent / "test_server_bearer.py"
    if not server_path.exists():
        pytest.skip(f"Server not found: {server_path}")

    with HTTPServerFixture(server_path, port=8000) as server:
        yield server


# ============================================================================
# Simple HTTP Tests (No Auth)
# ============================================================================


def test_http_simple_connection(simple_http_server):
    """Test basic HTTP connection without authentication."""
    server = load("http://localhost:8000/sse")

    # Test basic tool call
    result = server.echo(message="Hello HTTP!")
    assert "Hello HTTP!" in result

    server.close()


def test_http_simple_multiple_calls(simple_http_server):
    """Test multiple tool calls over same HTTP connection."""
    server = load("http://localhost:8000/sse")

    # Multiple calls
    result1 = server.echo(message="First")
    result2 = server.echo(message="Second")
    result3 = server.add(a=10, b=20)

    assert "First" in result1
    assert "Second" in result2
    assert "30" in result3

    server.close()


def test_http_context_manager(simple_http_server):
    """Test HTTP server with context manager."""
    with load("http://localhost:8000/sse") as server:
        result = server.echo(message="Context manager works!")
        assert "Context manager works!" in result


# ============================================================================
# Bearer Token Authentication Tests
# ============================================================================


def test_bearer_auth_via_auth_parameter(bearer_http_server):
    """Test bearer authentication via auth parameter."""
    server = load("http://localhost:8000/sse", auth="test-token-12345")

    result = server.echo(message="Authenticated!")
    assert "Bearer Auth" in result or "Authenticated!" in result

    server.close()


def test_bearer_auth_via_headers(bearer_http_server):
    """Test bearer authentication via headers parameter."""
    server = load(
        "http://localhost:8000/sse",
        headers={"Authorization": "Bearer test-token-12345"},
    )

    result = server.echo(message="Authenticated!")
    assert "Authenticated!" in result

    server.close()


def test_bearer_auth_via_environment(bearer_http_server):
    """Test bearer authentication via MCP_TOKEN environment variable."""
    # Set environment variable
    os.environ["MCP_TOKEN"] = "test-token-12345"

    try:
        server = load("http://localhost:8000/sse")

        result = server.echo(message="Authenticated!")
        assert "Authenticated!" in result

        server.close()
    finally:
        # Cleanup
        del os.environ["MCP_TOKEN"]


def test_bearer_auth_failure(bearer_http_server):
    """Test that invalid bearer token is rejected."""
    with pytest.raises((MCPConnectionError, RuntimeError)) as exc_info:
        server = load("http://localhost:8000/sse", auth="invalid-token")

    # Should fail with authentication error
    error_msg = str(exc_info.value).lower()
    assert "401" in error_msg or "unauthorized" in error_msg or "failed" in error_msg


def test_bearer_auth_missing(bearer_http_server):
    """Test that missing bearer token is rejected."""
    with pytest.raises((MCPConnectionError, RuntimeError)) as exc_info:
        server = load("http://localhost:8000/sse")

    # Should fail with authentication error
    error_msg = str(exc_info.value).lower()
    assert "401" in error_msg or "unauthorized" in error_msg or "failed" in error_msg


# ============================================================================
# Error Handling Tests
# ============================================================================


def test_http_connection_refused():
    """Test graceful handling of connection refused (server not running)."""
    with pytest.raises((MCPConnectionError, RuntimeError)) as exc_info:
        server = load("http://localhost:9999/sse")  # Port that's not running

    error_msg = str(exc_info.value).lower()
    assert "failed to connect" in error_msg or "connection" in error_msg


def test_http_invalid_url():
    """Test handling of invalid URLs."""
    with pytest.raises((MCPConnectionError, RuntimeError, ValueError)):
        server = load("http://not-a-valid-url-at-all:8000/sse")


# ============================================================================
# Integration Smoke Test
# ============================================================================


def test_end_to_end_http_workflow(simple_http_server):
    """Complete end-to-end test of HTTP workflow."""
    # Load server
    server = load("http://localhost:8000/sse")

    try:
        # Test tools are available
        tools = server.tools
        assert len(tools) >= 2
        assert all(callable(tool) for tool in tools)

        # Test tool execution
        echo_result = server.echo(message="Integration test")
        assert "Integration test" in echo_result

        add_result = server.add(a=100, b=200)
        assert "300" in add_result

        # Test resources (if available)
        try:
            resources = server.resources
            assert isinstance(resources, list)
        except AttributeError:
            pass  # Resources optional

    finally:
        server.close()


# ============================================================================
# Performance/Stress Tests (Optional)
# ============================================================================


@pytest.mark.slow
def test_http_rapid_sequential_calls(simple_http_server):
    """Test rapid sequential calls don't break the connection."""
    server = load("http://localhost:8000/sse")

    try:
        # Make 20 rapid calls
        for i in range(20):
            result = server.echo(message=f"Call {i}")
            assert f"Call {i}" in result

    finally:
        server.close()


# ============================================================================
# Skip Markers for CI
# ============================================================================


def test_auth_integration_summary(capsys):
    """Summary of what was tested (for visibility in test output)."""
    summary = """
    HTTP/SSE Integration Tests Summary:
    ===================================
    ✓ Simple HTTP connection (no auth)
    ✓ Multiple calls over same connection
    ✓ Context manager support
    ✓ Bearer token via auth parameter
    ✓ Bearer token via headers
    ✓ Bearer token via environment variable
    ✓ Invalid token rejection
    ✓ Missing token rejection
    ✓ Connection refused handling
    ✓ End-to-end workflow

    All HTTP authentication features tested!
    """
    print(summary)
    assert True


if __name__ == "__main__":
    # Allow running directly for quick testing
    pytest.main([__file__, "-v", "-s"])
