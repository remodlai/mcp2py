"""Tests for authentication module."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from mcp2py.auth import BearerAuth, OAuth, create_auth_handler


class TestBearerAuth:
    """Test bearer token authentication."""

    def test_bearer_auth_initialization(self):
        """Test BearerAuth initialization."""
        auth = BearerAuth("sk-test-token")
        assert auth is not None

    def test_bearer_auth_adds_header(self):
        """Test that BearerAuth adds Authorization header."""
        auth = BearerAuth("sk-test-token")
        request = httpx.Request("GET", "https://example.com")

        # Auth flow is a generator
        flow = auth.auth_flow(request)
        modified_request = next(flow)

        assert "Authorization" in modified_request.headers
        assert modified_request.headers["Authorization"] == "Bearer sk-test-token"


class TestOAuth:
    """Test OAuth authentication."""

    def test_oauth_initialization(self):
        """Test OAuth initialization."""
        oauth = OAuth("https://api.example.com/mcp")
        assert oauth is not None

    def test_oauth_with_scopes(self):
        """Test OAuth with custom scopes."""
        oauth = OAuth(
            "https://api.example.com/mcp",
            scopes=["read", "write"],
        )
        assert oauth is not None

    def test_oauth_with_client_name(self):
        """Test OAuth with custom client name."""
        oauth = OAuth(
            "https://api.example.com/mcp",
            client_name="my-app",
        )
        assert oauth is not None


class TestCreateAuthHandler:
    """Test create_auth_handler function."""

    def test_no_auth(self):
        """Test with no authentication."""
        auth, headers = create_auth_handler(None, None, "https://example.com", True)
        assert auth is None
        assert headers == {}

    def test_bearer_token_string(self):
        """Test with bearer token as string."""
        auth, headers = create_auth_handler(
            "sk-test-token", None, "https://example.com", True
        )
        assert isinstance(auth, BearerAuth)
        assert headers == {}

    def test_oauth_string(self):
        """Test with 'oauth' string."""
        auth, headers = create_auth_handler("oauth", None, "https://example.com", True)
        assert isinstance(auth, OAuth)
        assert headers == {}

    def test_custom_headers(self):
        """Test with custom headers."""
        custom_headers = {"X-API-Key": "abc123"}
        auth, headers = create_auth_handler(
            None, custom_headers, "https://example.com", True
        )
        assert auth is None
        assert headers == custom_headers

    def test_headers_with_authorization(self):
        """Test headers with Authorization."""
        custom_headers = {"Authorization": "Bearer custom-token"}
        auth, headers = create_auth_handler(
            None, custom_headers, "https://example.com", True
        )
        assert auth is None
        assert "Authorization" in headers

    def test_callable_token_provider(self):
        """Test with callable token provider."""

        def get_token():
            return "dynamic-token"

        auth, headers = create_auth_handler(
            get_token, None, "https://example.com", True
        )
        assert isinstance(auth, BearerAuth)

    def test_callable_token_provider_none(self):
        """Test with callable that returns None."""

        def get_token():
            return None

        auth, headers = create_auth_handler(
            get_token, None, "https://example.com", True
        )
        assert auth is None

    def test_custom_httpx_auth(self):
        """Test with custom httpx.Auth instance."""

        class CustomAuth(httpx.Auth):
            def auth_flow(self, request):
                request.headers["X-Custom"] = "value"
                yield request

        custom_auth = CustomAuth()
        auth, headers = create_auth_handler(
            custom_auth, None, "https://example.com", True
        )
        assert auth is custom_auth

    def test_env_token_fallback(self):
        """Test MCP_TOKEN environment variable."""
        with patch.dict(os.environ, {"MCP_TOKEN": "env-token"}):
            auth, headers = create_auth_handler(
                None, None, "https://example.com", True
            )
            assert isinstance(auth, BearerAuth)

    def test_invalid_auth_type(self):
        """Test with invalid auth type."""
        with pytest.raises(ValueError, match="Invalid auth type"):
            create_auth_handler(123, None, "https://example.com", True)  # type: ignore


class TestAuthIntegration:
    """Integration tests for authentication."""

    def test_auth_with_load_function(self):
        """Test that auth can be passed to load function."""
        # This tests the interface, actual load() tests are elsewhere
        from mcp2py import load

        # Verify load accepts auth parameters
        import inspect

        sig = inspect.signature(load)
        assert "auth" in sig.parameters
        assert "headers" in sig.parameters
        assert "auto_auth" in sig.parameters
        assert "timeout" in sig.parameters
