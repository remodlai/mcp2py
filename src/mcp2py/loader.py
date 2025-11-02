"""Loader for MCP servers.

This module provides the main entry point for loading MCP servers and
creating Python interfaces to them.
"""

from pathlib import Path
from typing import Any, Callable, Literal

import httpx

from mcp2py.auth import BearerAuth, OAuth, create_auth_handler
from mcp2py.client import MCPClient
from mcp2py.elicitation import DefaultElicitationHandler, ElicitationHandler
from mcp2py.event_loop import AsyncRunner
from mcp2py.http_client import HTTPMCPClient
from mcp2py.registry import get_command
from mcp2py.roots import normalize_roots
from mcp2py.sampling import DefaultSamplingHandler, SamplingHandler
from mcp2py.schema import parse_command
from mcp2py.server import MCPServer


def load(
    command: str | list[str],
    *,
    roots: str | list[str] | Path | list[Path] | None = None,
    headers: dict[str, str] | None = None,
    auth: httpx.Auth | Literal["oauth"] | str | Callable[[], str] | None = None,
    auto_auth: bool = True,
    timeout: float = 30.0,
    allow_sampling: bool = True,
    on_sampling: SamplingHandler | None = None,
    allow_elicitation: bool = True,
    on_elicitation: ElicitationHandler | None = None,
    **kwargs: Any,
) -> MCPServer:
    """Load MCP server and return Python interface.

    Supports both stdio (local subprocess) and HTTP/SSE (remote server) transports.
    Automatically detects transport type based on command format.

    Args:
        command: Command to launch server, URL, or registered server name
        roots: Optional directory roots for the server to focus on
        headers: HTTP headers for remote servers (e.g., Authorization)
        auth: Authentication handler (bearer token, "oauth", callable, or httpx.Auth)
        auto_auth: Enable automatic OAuth flow (default: True)
        timeout: HTTP request timeout in seconds (default: 30.0)
        allow_sampling: Allow server to request LLM completions (default: True)
        on_sampling: Custom sampling handler (default: auto-detect from env)
        allow_elicitation: Allow server to request user input (default: True)
        on_elicitation: Custom elicitation handler (default: terminal prompts)
        **kwargs: Reserved for future options

    Returns:
        MCPServer object with tools as methods

    Raises:
        RuntimeError: If connection or initialization fails
        ValueError: If command is invalid

    Example (stdio - local server):
        >>> server = load("python tests/test_server.py")
        >>> result = server.echo(message="Hello!")
        >>> "Hello!" in result
        True
        >>> server.close()

    Example (HTTP - remote server with bearer token):
        >>> server = load(
        ...     "https://api.example.com/mcp",
        ...     headers={"Authorization": "Bearer sk-1234"}
        ... )
        >>> result = server.search(query="test")
        >>> server.close()

    Example (HTTP - remote server with OAuth):
        >>> server = load("https://api.example.com/mcp", auth="oauth")
        >>> # Browser opens automatically for login
        >>> result = server.search(query="test")
        >>> server.close()

    Example with registered server:
        >>> from mcp2py import register
        >>> register(weather="npx -y @h1deya/mcp-server-weather")
        >>> server = load("weather")  # Looks up in registry

    Example with roots:
        >>> server = load("npx filesystem-server", roots="/tmp")
        >>> # Server will focus on /tmp directory

    Example with sampling disabled:
        >>> server = load("npx my-server", allow_sampling=False)
        >>> # Server cannot request LLM completions

    Example with context manager:
        >>> with load("python tests/test_server.py") as server:
        ...     result = server.echo(message="test")
        ...     "test" in result
        True

    Example with list command:
        >>> server = load(["python", "tests/test_server.py"])
        >>> result = server.add(a=5, b=3)
        >>> "8" in result
        True
        >>> server.close()
    """
    # Detect transport type
    is_http = isinstance(command, str) and command.startswith(("http://", "https://"))

    if is_http:
        # HTTP/SSE transport for remote servers
        url = command
        auth_handler, headers = create_auth_handler(auth, headers, url, auto_auth)

        return _load_http_server(
            url=url,
            headers=headers,
            auth=auth_handler,
            timeout=timeout,
            allow_sampling=allow_sampling,
            on_sampling=on_sampling,
            allow_elicitation=allow_elicitation,
            on_elicitation=on_elicitation,
        )

    # Stdio transport for local servers
    # Check if command is a registered server name
    if isinstance(command, str) and not command.startswith(("python", "npx", "node", "uv", "/")):
        registered_cmd = get_command(command)
        if registered_cmd:
            command = registered_cmd

    # Parse command into list
    cmd_list = parse_command(command)

    if not cmd_list:
        raise ValueError("Command cannot be empty")

    # Normalize roots if provided, or auto-detect from filesystem server
    if roots:
        roots_list = normalize_roots(roots)
    else:
        # Auto-detect roots for filesystem servers
        # If command contains "server-filesystem" and has path arguments, use them as roots
        if any("server-filesystem" in part for part in cmd_list):
            # Extract directory paths from command (skip command/flags)
            potential_roots = []
            for arg in cmd_list:
                # Skip commands, flags, and npm-related args
                if not arg.startswith(("-", "npx", "node", "@", "uv")) and "/" in arg:
                    potential_roots.append(arg)

            if potential_roots:
                roots_list = normalize_roots(potential_roots)
            else:
                roots_list = None
        else:
            roots_list = None

    # Set up sampling handler
    sampling_callback = None
    if allow_sampling:
        if on_sampling:
            # Use custom handler
            sampling_handler = on_sampling
        else:
            # Use default handler
            sampling_handler = DefaultSamplingHandler()

        # Create async wrapper for the sampling handler
        async def sampling_callback(context, params):
            from mcp import types

            try:
                # Convert params to handler format
                messages = [
                    {"role": msg.role, "content": msg.content.text if hasattr(msg.content, 'text') else str(msg.content)}
                    for msg in params.messages
                ]

                # Call handler (synchronous)
                response_text = sampling_handler(
                    messages=messages,
                    model_preferences=params.modelPreferences.model_dump() if hasattr(params, 'modelPreferences') and params.modelPreferences else None,
                    system_prompt=params.systemPrompt if hasattr(params, 'systemPrompt') else None,
                    max_tokens=params.maxTokens if hasattr(params, 'maxTokens') else 1000,
                )

                # Return MCP response
                return types.CreateMessageResult(
                    role="assistant",
                    content=types.TextContent(type="text", text=response_text),
                    model=sampling_handler.model if hasattr(sampling_handler, 'model') and sampling_handler.model else "default",
                    stopReason="endTurn"
                )
            except Exception as e:
                # Return error
                return types.ErrorData(
                    code="INTERNAL_ERROR",
                    message=f"Sampling failed: {e}"
                )

    # Set up elicitation handler
    elicitation_callback = None
    if allow_elicitation:
        if on_elicitation:
            elicitation_handler = on_elicitation
        else:
            elicitation_handler = DefaultElicitationHandler()

        # Create async wrapper for the elicitation handler
        async def elicitation_callback(context, params):
            from mcp import types

            try:
                # Convert params to handler format
                message = params.message if hasattr(params, 'message') else ""

                # Get schema - it might be a Pydantic model or already a dict
                if hasattr(params, 'requestedSchema') and params.requestedSchema:
                    schema = params.requestedSchema.model_dump() if hasattr(params.requestedSchema, 'model_dump') else params.requestedSchema
                else:
                    schema = {}

                # Call handler (synchronous)
                response_data = elicitation_handler(message, schema)

                # Return MCP response
                return types.ElicitResult(
                    action="accept",
                    content=response_data
                )
            except Exception as e:
                # Return cancel on error
                return types.ElicitResult(
                    action="cancel",
                    content={"error": str(e)}
                )

    # Create async runner (background event loop in thread)
    runner = AsyncRunner()

    # Create MCP client with roots and callbacks
    client = MCPClient(
        cmd_list,
        roots=roots_list,
        sampling_callback=sampling_callback,
        elicitation_callback=elicitation_callback,
    )

    # Connect and initialize synchronously via runner
    try:
        # Connect to server subprocess
        runner.run(client.connect())

        # MCP initialization handshake
        runner.run(
            client.initialize(
                client_info={
                    "name": "mcp2py",
                    "version": "0.1.0",
                }
            )
        )

        # List available tools (required)
        tools = runner.run(client.list_tools())

        # Try to list resources (optional capability)
        try:
            resources = runner.run(client.list_resources())
        except Exception:
            # Server doesn't support resources
            resources = []

        # Try to list prompts (optional capability)
        try:
            prompts = runner.run(client.list_prompts())
        except Exception:
            # Server doesn't support prompts
            prompts = []

    except Exception as e:
        # Cleanup on failure
        try:
            runner.close()
        except Exception:
            pass

        raise RuntimeError(f"Failed to connect to MCP server: {e}") from e

    # Create dynamically typed server class for IDE autocomplete
    try:
        from mcp2py.stubs import create_typed_server_class

        # Create typed subclass with method stubs
        TypedServerClass = create_typed_server_class(
            MCPServer, tools, resources, prompts
        )

        # Instantiate the typed class instead of base MCPServer
        server = TypedServerClass(client, runner, tools, resources, prompts, command=command)

    except Exception:
        # Fallback to regular MCPServer if typing fails
        server = MCPServer(client, runner, tools, resources, prompts, command=command)

    # Auto-generate stub file to cache (best effort, don't fail if it errors)
    try:
        server.generate_stubs()
    except Exception:
        # Silently ignore stub generation failures
        pass

    return server


def _load_http_server(
    url: str,
    headers: dict[str, str] | None = None,
    auth: httpx.Auth | None = None,
    timeout: float = 30.0,
    allow_sampling: bool = True,
    on_sampling: SamplingHandler | None = None,
    allow_elicitation: bool = True,
    on_elicitation: ElicitationHandler | None = None,
) -> MCPServer:
    """Load HTTP/SSE MCP server (internal helper).

    Args:
        url: HTTP/HTTPS URL of MCP server
        headers: HTTP headers
        auth: Authentication handler
        timeout: Request timeout
        allow_sampling: Allow LLM sampling
        on_sampling: Custom sampling handler
        allow_elicitation: Allow user input
        on_elicitation: Custom elicitation handler

    Returns:
        MCPServer object

    Raises:
        RuntimeError: If connection fails
    """
    # HTTP client doesn't support sampling/elicitation callbacks yet
    # These would need to be handled differently in SSE transport
    sampling_callback = None
    elicitation_callback = None

    # Create async runner (background event loop in thread)
    runner = AsyncRunner()

    # Create HTTP MCP client
    client = HTTPMCPClient(
        url=url,
        headers=headers,
        auth=auth,
        timeout=timeout,
        sse_read_timeout=300.0,  # 5 minutes for SSE
        sampling_callback=sampling_callback,
        elicitation_callback=elicitation_callback,
    )

    # Connect and initialize synchronously via runner
    try:
        # Connect to HTTP server
        runner.run(client.connect())

        # MCP initialization handshake
        runner.run(
            client.initialize(
                client_info={
                    "name": "mcp2py",
                    "version": "0.1.0",
                }
            )
        )

        # List available tools (required)
        tools = runner.run(client.list_tools())

        # Try to list resources (optional capability)
        try:
            resources = runner.run(client.list_resources())
        except Exception:
            resources = []

        # Try to list prompts (optional capability)
        try:
            prompts = runner.run(client.list_prompts())
        except Exception:
            prompts = []

    except Exception as e:
        # Cleanup on failure
        try:
            runner.close()
        except Exception:
            pass

        raise RuntimeError(f"Failed to connect to HTTP MCP server: {e}") from e

    # Create dynamically typed server class for IDE autocomplete
    try:
        from mcp2py.stubs import create_typed_server_class

        # Create typed subclass with method stubs
        TypedServerClass = create_typed_server_class(
            MCPServer, tools, resources, prompts
        )

        # Instantiate the typed class
        server = TypedServerClass(client, runner, tools, resources, prompts, command=url)

    except Exception:
        # Fallback to regular MCPServer if typing fails
        server = MCPServer(client, runner, tools, resources, prompts, command=url)

    # Auto-generate stub file to cache (best effort)
    try:
        server.generate_stubs()
    except Exception:
        pass

    return server
