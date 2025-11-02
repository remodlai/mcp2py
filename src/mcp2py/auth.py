"""Authentication support for MCP servers.

This module provides various authentication methods for remote MCP servers,
including bearer tokens, OAuth 2.1, and custom authentication handlers.

This wraps FastMCP's authentication to provide a simpler API.
"""

import os
from typing import Any, Callable, Literal

import httpx
from fastmcp.client.auth.bearer import BearerAuth as FastMCPBearerAuth
from fastmcp.client.auth.oauth import OAuth as FastMCPOAuth


# Re-export FastMCP's BearerAuth
BearerAuth = FastMCPBearerAuth


# FastMCP handles token storage automatically via FileTokenStorage
# in ~/.fastmcp/oauth-mcp-client-cache/


class OAuth:
    """OAuth 2.1 authentication handler with PKCE support.

    Wraps FastMCP's OAuth implementation for easier use with mcp2py.
    Handles browser-based OAuth flows with automatic token management.

    Example:
        >>> oauth = OAuth("https://api.example.com/mcp")
        >>> # FastMCP handles browser opening and token caching automatically
        >>> auth = oauth  # Use directly as httpx.Auth

    Note:
        Tokens are cached in ~/.fastmcp/oauth-mcp-client-cache/
    """

    def __init__(
        self,
        url: str,
        scopes: str | list[str] | None = None,
        client_name: str = "mcp2py",
    ):
        """Initialize OAuth handler.

        Args:
            url: MCP server URL
            scopes: OAuth scopes to request
            client_name: Name for this client during registration
        """
        self._oauth = FastMCPOAuth(
            mcp_url=url,
            scopes=scopes,
            client_name=client_name,
        )

    def auth_flow(self, request: httpx.Request):
        """HTTPX auth flow - delegates to FastMCP OAuth."""
        return self._oauth.auth_flow(request)

    async def async_auth_flow(self, request: httpx.Request):
        """Async HTTPX auth flow - delegates to FastMCP OAuth."""
        return self._oauth.async_auth_flow(request)


def create_auth_handler(
    auth: httpx.Auth | Literal["oauth"] | str | Callable[[], str] | None,
    headers: dict[str, str] | None,
    url: str,
    auto_auth: bool = True,
) -> tuple[httpx.Auth | None, dict[str, str]]:
    """Create authentication handler from various input types.

    Args:
        auth: Authentication specification (bearer token, "oauth", callable, or httpx.Auth)
        headers: HTTP headers (may contain Authorization)
        url: MCP server URL
        auto_auth: Enable automatic OAuth flow

    Returns:
        Tuple of (auth_handler, updated_headers)

    Example:
        >>> # Bearer token string
        >>> auth, headers = create_auth_handler("sk-123", None, "https://api.example.com", True)

        >>> # OAuth
        >>> auth, headers = create_auth_handler("oauth", None, "https://api.example.com", True)

        >>> # Token from environment
        >>> auth, headers = create_auth_handler(lambda: os.getenv("TOKEN"), None, "https://api.example.com", True)

        >>> # Custom headers
        >>> auth, headers = create_auth_handler(None, {"Authorization": "Bearer sk-123"}, "https://api.example.com", True)
    """
    headers = headers or {}

    # Check environment variable first
    env_token = os.getenv("MCP_TOKEN")
    if env_token and not auth and "Authorization" not in headers:
        return BearerAuth(env_token), headers

    # Handle different auth types
    if auth is None:
        # No auth specified, use headers as-is
        return None, headers

    elif isinstance(auth, str):
        if auth == "oauth":
            # OAuth flow
            oauth_handler = OAuth(url)
            return oauth_handler, headers
        else:
            # Treat as bearer token
            return BearerAuth(auth), headers

    elif callable(auth):
        # Token provider function
        token = auth()
        if token:
            return BearerAuth(token), headers
        return None, headers

    elif isinstance(auth, httpx.Auth):
        # Custom httpx Auth instance
        return auth, headers

    else:
        raise ValueError(f"Invalid auth type: {type(auth)}")
