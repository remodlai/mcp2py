# Authentication Guide

Full guide to using authentication with mcp2py for remote MCP servers.

## Quick Start

### Bearer Token
```python
from mcp2py import load

# Method 1: Direct token
server = load("https://api.example.com/mcp/sse", auth="sk-token123")

# Method 2: Via headers
server = load(
    "https://api.example.com/mcp/sse",
    headers={"Authorization": "Bearer sk-token123"}
)

# Method 3: Via environment variable
import os
os.environ["MCP_TOKEN"] = "sk-token123"
server = load("https://api.example.com/mcp/sse")
```

### OAuth 2.1
```python
from mcp2py import load

# Auto OAuth (browser opens automatically)
server = load("https://api.example.com/mcp/sse", auth="oauth")

# First time: Browser opens, you log in, browser closes
# Second time: Uses cached token automatically
```

## Supported Authentication Methods

### 1. Bearer Token Authentication

Simple token-based authentication for API keys and access tokens.

**Basic Usage:**
```python
server = load("https://api.example.com/mcp/sse", auth="your-token-here")
```

**With Environment Variables (Recommended):**
```python
import os

# Set token
os.environ["MCP_TOKEN"] = "your-token-here"

# Load server (automatically uses MCP_TOKEN)
server = load("https://api.example.com/mcp/sse")
```

**Callable Token Provider:**
```python
def get_token():
    """Dynamic token retrieval."""
    # Read from secure storage, refresh if needed, etc.
    return os.getenv("MY_API_TOKEN")

server = load("https://api.example.com/mcp/sse", auth=get_token)
```

### 2. OAuth 2.1 with PKCE

Browser-based OAuth flows with automatic token management.

**Zero-Configuration OAuth:**
```python
# Browser opens automatically for login
server = load("https://api.example.com/mcp/sse", auth="oauth")

# 1. Browser window opens
# 2. You authenticate with OAuth provider (Google, GitHub, etc.)
# 3. Browser closes automatically
# 4. Connection established!
```

**Custom OAuth Configuration:**
```python
from mcp2py import OAuth

oauth = OAuth(
    url="https://api.example.com/mcp/sse",
    scopes=["read", "write"],
    client_name="my-app"
)

server = load("https://api.example.com/mcp/sse", auth=oauth)
```

**Token Caching:**
- Tokens automatically cached in `~/.fastmcp/oauth-mcp-client-cache/`
- Second connection doesn't require re-authentication
- Tokens auto-refresh when expired
- Per-server token storage

**Disable Auto-Browser (CI/Production):**
```python
# Raises error if OAuth needed (won't open browser)
server = load(
    "https://api.example.com/mcp/sse",
    auth="oauth",
    auto_auth=False
)
```

### 3. Custom Headers

For API keys, custom authentication schemes, or multiple headers.

```python
server = load(
    "https://api.example.com/mcp/sse",
    headers={
        "X-API-Key": "your-api-key",
        "X-Client-ID": "your-client-id",
        "X-Custom-Header": "custom-value"
    }
)
```

### 4. Custom httpx.Auth

For advanced authentication flows.

```python
import httpx
from mcp2py import load

class CustomAuth(httpx.Auth):
    def auth_flow(self, request):
        # Custom authentication logic
        request.headers["Authorization"] = f"Custom {self.get_token()}"
        yield request

    def get_token(self):
        # Your custom token logic
        return "custom-token"

server = load("https://api.example.com/mcp/sse", auth=CustomAuth())
```

## Security Best Practices

### Client-Side (Automatic)
- ✅ Secure token storage - OAuth tokens in `~/.fastmcp/oauth-mcp-client-cache/`
- ✅ PKCE support for OAuth (Proof Key for Code Exchange)
- ✅ Automatic token refresh before expiration
- ✅ Environment variable support

### Your Responsibilities

**1. Use HTTPS in Production**
```python
# Good
server = load("https://api.example.com/mcp/sse", auth=token)

# Bad - unencrypted!
# server = load("http://api.example.com/mcp/sse", auth=token)
```

**2. Never Hardcode Secrets**
```python
# Good - use environment variables
import os
server = load("https://api.example.com/mcp/sse", auth=os.getenv("MCP_TOKEN"))

# Bad - token in source code!
# server = load("https://api.example.com/mcp/sse", auth="sk-secret-123")
```

**3. Rotate Credentials Regularly**
- Change API tokens periodically
- Revoke unused tokens
- Monitor token usage

**4. Secure Token Storage**
```python
# For production applications
from your_secure_storage import get_secret

token = get_secret("mcp_api_token")
server = load("https://api.example.com/mcp/sse", auth=token)
```

## Examples

### Example 1: Environment-Based Configuration
```python
"""Production-ready configuration using environment variables."""
import os
from mcp2py import load

# Configuration from environment
MCP_URL = os.getenv("MCP_SERVER_URL", "https://api.example.com/mcp/sse")
MCP_TOKEN = os.getenv("MCP_TOKEN")

if not MCP_TOKEN:
    raise ValueError("MCP_TOKEN environment variable required")

# Load with environment config
server = load(MCP_URL, auth=MCP_TOKEN)

# Use the server
result = server.my_tool(param="value")
print(result)

server.close()
```

### Example 2: OAuth with Error Handling
```python
"""OAuth with graceful error handling."""
from mcp2py import load
from mcp2py.exceptions import MCPConnectionError

try:
    # Attempt OAuth login
    server = load("https://api.example.com/mcp/sse", auth="oauth")

    # Use the server
    result = server.my_tool()
    print(result)

except MCPConnectionError as e:
    print(f"Failed to connect: {e}")
    print("Please check:")
    print("  - Server URL is correct")
    print("  - You have network connectivity")
    print("  - OAuth credentials are valid")
finally:
    if 'server' in locals():
        server.close()
```

### Example 3: Multi-Environment Setup
```python
"""Different authentication for dev/staging/prod."""
import os
from mcp2py import load

ENVIRONMENT = os.getenv("ENV", "development")

configs = {
    "development": {
        "url": "http://localhost:8000/sse",
        "auth": None  # No auth for local dev
    },
    "staging": {
        "url": "https://staging-api.example.com/mcp/sse",
        "auth": os.getenv("STAGING_TOKEN")
    },
    "production": {
        "url": "https://api.example.com/mcp/sse",
        "auth": os.getenv("PROD_TOKEN")
    }
}

config = configs[ENVIRONMENT]
server = load(config["url"], auth=config["auth"])
```

### Example 4: Service Account (No Browser)
```python
"""Using service accounts for automated systems."""
from google.oauth2 import service_account
from mcp2py import load

# Load service account credentials
credentials = service_account.Credentials.from_service_account_file(
    'service-account.json',
    scopes=['https://www.googleapis.com/auth/mcp.read']
)

# Use with mcp2py
server = load("https://api.example.com/mcp/sse", auth=credentials)

# Automated workflow (no human interaction needed)
result = server.automated_task()
```

## Troubleshooting

### 401 Unauthorized
**Symptoms:** Connection fails with 401 error

**Solutions:**
1. Check token is correct: `echo $MCP_TOKEN`
2. Verify token format: Should be `Bearer <token>` in Authorization header
3. Ensure token hasn't expired
4. Check server URL is correct

### OAuth Browser Doesn't Open
**Symptoms:** OAuth flow doesn't launch browser

**Solutions:**
1. Check you're not in a headless environment (server/CI)
2. Use `auto_auth=False` and provide token manually for servers
3. Verify OAuth provider configuration
4. Check firewall/network restrictions

### Token Cache Issues
**Symptoms:** OAuth prompts for login every time

**Solutions:**
```bash
# Check cache directory
ls -la ~/.fastmcp/oauth-mcp-client-cache/

# Clear cache to force re-authentication
rm -rf ~/.fastmcp/oauth-mcp-client-cache/

# Re-authenticate
python -c "from mcp2py import load; load('https://api.example.com/mcp/sse', auth='oauth')"
```

### Connection Timeout
**Symptoms:** Connection times out

**Solutions:**
```python
# Increase timeout
server = load(
    "https://api.example.com/mcp/sse",
    auth=token,
    timeout=60.0  # Increase from default 30s
)
```

## Architecture

### How Authentication Works

```
Your Code
    ↓
mcp2py.load(auth=...)
    ↓
auth.create_auth_handler()  ← Processes auth parameter
    ↓
httpx.Auth or headers       ← Converted to httpx format
    ↓
HTTPMCPClient               ← Uses auth with requests
    ↓
Official MCP SDK sse_client ← HTTP/SSE transport
    ↓
Remote MCP Server           ← Validates credentials
```

### Token Flow (OAuth)

```
1. First Connection:
   load(url, auth="oauth")
   → FastMCP OAuth initiates flow
   → Browser opens for authentication
   → User logs in
   → OAuth callback receives tokens
   → Tokens saved to ~/.fastmcp/oauth-mcp-client-cache/
   → Connection established

2. Subsequent Connections:
   load(url, auth="oauth")
   → FastMCP checks cache
   → Cached token found
   → Token still valid? Use it
   → Token expired? Refresh automatically
   → Connection established (no browser!)
```

## API Reference

### BearerAuth
```python
from mcp2py import BearerAuth

auth = BearerAuth("your-token-here")
server = load("https://api.example.com/mcp/sse", auth=auth)
```

### OAuth
```python
from mcp2py import OAuth

oauth = OAuth(
    url="https://api.example.com/mcp/sse",
    scopes=["read", "write"],  # Optional scopes
    client_name="my-app"        # Optional client name
)
server = load("https://api.example.com/mcp/sse", auth=oauth)
```

### load() Parameters
```python
def load(
    command: str,
    *,
    headers: dict[str, str] | None = None,
    auth: httpx.Auth | Literal["oauth"] | str | Callable[[], str] | None = None,
    auto_auth: bool = True,
    timeout: float = 30.0,
    **kwargs
) -> MCPServer:
    """Load MCP server with authentication.

    Args:
        command: Server URL or command
        headers: HTTP headers (including Authorization)
        auth: Authentication handler (token, "oauth", callable, or httpx.Auth)
        auto_auth: Enable automatic OAuth browser flow
        timeout: HTTP timeout in seconds
    """
```

## Additional Resources

- [MCP Specification](https://modelcontextprotocol.io)
- [FastMCP Documentation](https://gofastmcp.com)
- [httpx Authentication](https://www.python-httpx.org/advanced/authentication/)
- [OAuth 2.1 Specification](https://oauth.net/2.1/)

## Summary

**Simple Cases - Just Works:**
```python
# Bearer token
server = load("https://api.example.com/mcp/sse", auth="token")

# OAuth
server = load("https://api.example.com/mcp/sse", auth="oauth")
```

**Production - Full Control:**
```python
# Environment-based config
server = load(
    os.getenv("MCP_URL"),
    auth=os.getenv("MCP_TOKEN"),
    timeout=60.0,
    auto_auth=False
)
```

**mcp2py makes authentication simple by default, powerful when you need it.**
