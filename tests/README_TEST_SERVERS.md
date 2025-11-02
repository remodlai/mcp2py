# Test Servers for Interactive Authentication Testing

This directory contains three MCP test servers for interactive testing of mcp2py's authentication features.

## Servers

### 1. Standard Test Server (No Auth)
**File:** `test_server.py`
**Port:** N/A (stdio only)
**Authentication:** None

Basic MCP server for stdio transport testing.

**Usage:**
```bash
# Terminal 1: Run server via mcp2py
python test_server.py

# Or load directly in Python
from mcp2py import load
server = load("python tests/test_server.py")
result = server.echo(message="Hello!")
print(result)
server.close()
```

---

### 2. Bearer Token Server
**File:** `test_server_bearer.py`
**Port:** 8000
**Authentication:** Bearer Token

Requires `Authorization: Bearer test-token-12345` header.

**Start Server:**
```bash
# Terminal 1
python tests/test_server_bearer.py
```

**Connect with mcp2py:**
```python
# Terminal 2 / Python REPL
from mcp2py import load

# Method 1: Via headers
server = load(
    "http://localhost:8000/mcp/sse",
    headers={"Authorization": "Bearer test-token-12345"}
)

# Method 2: Via auth parameter (string)
server = load(
    "http://localhost:8000/mcp/sse",
    auth="test-token-12345"
)

# Method 3: Via environment variable
import os
os.environ["MCP_TOKEN"] = "test-token-12345"
server = load("http://localhost:8000/mcp/sse")

# Test it
result = server.echo(message="Hello Bearer!")
print(result)  # "Echo (Bearer Auth): Hello Bearer!"

user = server.get_user_info()
print(user)  # "User authenticated with bearer token: test-token-12345"

server.close()
```

**Test Authentication Failure:**
```python
# This should fail with 401
server = load("http://localhost:8000/mcp/sse")
# RuntimeError: Failed to connect to HTTP MCP server
```

---

### 3. OAuth Server
**File:** `test_server_oauth.py`
**Port:** 8001
**Authentication:** Google OAuth 2.0

Requires browser-based OAuth login via Google.

**Prerequisites:**
```bash
# Set up Google OAuth credentials
export GOOGLE_CLIENT_ID="your-client-id"
export GOOGLE_CLIENT_SECRET="your-client-secret"
```

**Start Server:**
```bash
# Terminal 1
python tests/test_server_oauth.py
```

**Connect with mcp2py:**
```python
# Terminal 2 / Python REPL
from mcp2py import load

# OAuth - browser opens automatically
server = load("http://localhost:8001/mcp/sse", auth="oauth")
# 1. Browser window opens
# 2. You log in with Google
# 3. Browser closes
# 4. Connection established!

# Test it
result = server.echo(message="Hello OAuth!")
print(result)  # "Echo (OAuth): Hello OAuth!"

user = server.get_user_info()
print(user)  # "Authenticated user: your-email@gmail.com"

server.close()
```

**Token Caching:**
OAuth tokens are cached automatically:
- Location: `~/.fastmcp/oauth-mcp-client-cache/`
- Second connection doesn't require login
- Tokens auto-refresh when expired

---

## Testing Scenarios

### Scenario 1: Bearer Token Success
```python
from mcp2py import load

server = load(
    "http://localhost:8000/mcp/sse",
    auth="test-token-12345"
)
assert "Bearer Auth" in server.echo(message="test")
server.close()
```

### Scenario 2: Bearer Token Failure
```python
from mcp2py import load

try:
    server = load("http://localhost:8000/mcp/sse")
    assert False, "Should have failed"
except RuntimeError as e:
    assert "401" in str(e) or "Failed to connect" in str(e)
    print("✓ Correctly rejected unauthorized request")
```

### Scenario 3: OAuth with Caching
```python
from mcp2py import load

# First time - browser opens
server1 = load("http://localhost:8001/mcp/sse", auth="oauth")
server1.close()

# Second time - uses cached token
server2 = load("http://localhost:8001/mcp/sse", auth="oauth")
# No browser! Token retrieved from cache
server2.close()
```

### Scenario 4: Callable Token Provider
```python
from mcp2py import load
import os

def get_token():
    """Dynamic token provider."""
    return os.getenv("MY_BEARER_TOKEN", "test-token-12345")

server = load("http://localhost:8000/mcp/sse", auth=get_token)
result = server.echo(message="Dynamic auth!")
server.close()
```

### Scenario 5: Custom httpx.Auth
```python
from mcp2py import load
import httpx

class CustomAuth(httpx.Auth):
    def auth_flow(self, request):
        request.headers["Authorization"] = "Bearer test-token-12345"
        yield request

server = load("http://localhost:8000/mcp/sse", auth=CustomAuth())
result = server.echo(message="Custom auth!")
server.close()
```

---

## Troubleshooting

### Bearer Server Issues

**401 Unauthorized:**
- Check token is exactly: `test-token-12345`
- Verify header format: `Authorization: Bearer test-token-12345`

**Connection refused:**
```bash
# Make sure server is running
curl http://localhost:8000/mcp/sse
```

### OAuth Server Issues

**Missing credentials:**
```bash
# Set environment variables
export GOOGLE_CLIENT_ID="..."
export GOOGLE_CLIENT_SECRET="..."
```

**Browser doesn't open:**
- Check if running in headless environment
- Try with `auto_auth=False` and manual token

**Token cache issues:**
```bash
# Clear token cache
rm -rf ~/.fastmcp/oauth-mcp-client-cache/
```

---

## Server Comparison

| Feature | test_server.py | test_server_bearer.py | test_server_oauth.py |
|---------|---------------|----------------------|---------------------|
| Transport | stdio | HTTP/SSE | HTTP/SSE |
| Port | N/A | 8000 | 8001 |
| Auth Type | None | Bearer Token | OAuth 2.0 |
| Browser Required | No | No | Yes (first time) |
| Token Caching | N/A | No | Yes |
| User Info | No | No | Yes |
| Test Token | N/A | test-token-12345 | N/A (Google) |

---

## Integration Tests

For automated testing of HTTP/SSE and authentication, see [test_http_integration.py](test_http_integration.py).

**Run integration tests:**
```bash
# Run all integration tests (spins up real HTTP servers)
pytest tests/test_http_integration.py -v

# Skip integration tests (for quick local testing)
SKIP_INTEGRATION=1 pytest
```

The integration tests automatically:
- Start HTTP test servers
- Test without auth (simple HTTP)
- Test bearer token authentication (via auth param, headers, environment)
- Test authentication failures (invalid/missing tokens)
- Test connection error handling
- Clean up automatically

**Fast, reliable, comprehensive** - perfect for CI/CD and pre-release testing!

---

## Quick Start All Servers

```bash
# Terminal 1 - Bearer server
python tests/test_server_bearer.py

# Terminal 2 - OAuth server (if configured)
python tests/test_server_oauth.py

# Terminal 3 - Test
python3 << 'EOF'
from mcp2py import load

# Test bearer
bearer = load("http://localhost:8000/mcp/sse", auth="test-token-12345")
print(bearer.echo(message="Bearer works!"))
bearer.close()

# Test OAuth (browser opens)
# oauth = load("http://localhost:8001/mcp/sse", auth="oauth")
# print(oauth.echo(message="OAuth works!"))
# oauth.close()

print("✓ All tests passed!")
EOF
```

---

## Next Steps

1. Start bearer server for basic HTTP/auth testing
2. Configure Google OAuth credentials for full OAuth testing
3. Test with real MCP servers from the ecosystem
4. Build production apps with authenticated MCP servers!

Happy testing! 🚀
