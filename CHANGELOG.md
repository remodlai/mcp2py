# Changelog

All notable changes to mcp2py will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2025-01-XX

### Added
- **HTTP/SSE Transport**: Connect to remote MCP servers via HTTP with Server-Sent Events
  - Support for remote MCP servers hosted over HTTP
  - Automatic transport detection based on URL (http:// or https://)
  - SSE streaming for real-time server communication
  - Configurable timeouts for HTTP requests and SSE reads
- **Bearer Token Authentication**: Simple token-based authentication for API access
  - Pass tokens directly via `auth` parameter
  - Header-based authentication via `headers` parameter
  - Environment variable support (`MCP_TOKEN`)
  - Callable token providers for dynamic token retrieval
- **OAuth 2.1 Support**: Browser-based OAuth flows with PKCE security
  - Zero-configuration OAuth with `auth="oauth"`
  - Automatic browser-based authentication flow
  - Token caching in `~/.fastmcp/oauth-mcp-client-cache/`
  - Automatic token refresh when expired
  - Support for custom scopes and client names
- **Flexible Authentication System**: Multiple authentication methods supported
  - Custom `httpx.Auth` handlers for advanced authentication flows
  - Mixed authentication via headers and auth parameter
  - Per-server authentication configuration
- **Security Features**:
  - PKCE (Proof Key for Code Exchange) for OAuth flows
  - Secure token storage with proper file permissions
  - Automatic token refresh handling
  - Environment variable support for secure credential management
- **New Documentation**: Comprehensive authentication guide at `docs/AUTHENTICATION.md`

### Changed
- `load()` function now accepts additional parameters:
  - `headers`: dict[str, str] for HTTP headers
  - `auth`: Multiple types supported (token string, "oauth", callable, or httpx.Auth)
  - `auto_auth`: bool to control automatic OAuth browser flow (default: True)
  - `timeout`: float for HTTP request timeout (default: 30.0s)
- HTTP/SSE transport automatically selected when URL starts with `http://` or `https://`
- Updated README with security best practices and authentication examples
- Improved error messages for HTTP connection failures

### Dependencies
- Now requires `fastmcp>=2.12.4` for OAuth support
- Uses official `mcp>=1.18.0` SDK's `sse_client` for HTTP/SSE transport
- All authentication features use existing dependencies (no new requirements)

### Migration Guide
No breaking changes! All existing code continues to work unchanged.

**Before (stdio only):**
```python
from mcp2py import load

server = load("npx my-server")
```

**After (stdio + HTTP/SSE):**
```python
from mcp2py import load

# Stdio still works exactly the same
server = load("npx my-server")

# Now HTTP also works
server = load("https://api.example.com/mcp/sse", auth="token")
```

## [0.4.0] - 2025-01-09

### Added
- Complete MCP feature support with zero-config IDE autocomplete
- Automatic stub generation for IDE type hints and autocomplete

## [0.3.0] - 2025-01-08

### Added
- Proper function signatures for DSPy/AI framework compatibility
- `.tools` attribute returns callable Python functions with full signatures
- Enhanced type hints for better IDE integration

### Changed
- Improved compatibility with AI frameworks (DSPy, Claudette, etc.)

## [0.2.0] - 2024-12-XX

### Added
- Automatic cleanup with `atexit` - no context manager required
- Servers automatically cleaned up on program exit

### Changed
- Context managers are now optional (but still recommended)

## [0.1.0] - 2024-12-XX

### Added
- Initial release
- Basic stdio transport for local MCP servers
- Tool → function mapping with type hints
- Resource access as Python attributes
- Prompt → template function mapping
- `.tools` attribute for AI SDK integration
- Server registry (`~/.config/mcp2py/servers.json`)
- Context manager protocol for automatic cleanup
- Stub generation for IDE support

---

## [Unreleased]

Features planned for future releases:
- Streamable HTTP transport (when widely adopted in ecosystem)
- Connection pooling for multiple servers
- Auth provider registry for common APIs
- Enhanced logging and debugging tools
