"""
TDWM MCP Server using FastMCP
Supports all transport methods: stdio, SSE, and streamable-http
"""
import argparse
import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from starlette.applications import Starlette
from mcp.server.sse import SseServerTransport
from starlette.requests import Request
from starlette.routing import Mount, Route
from mcp.server import Server
import uvicorn
from urllib.parse import urlparse
from mcp.server.fastmcp import FastMCP

from .tdsql import obfuscate_password
from .settings import Settings, settings_from_env
from .connection_manager import TeradataConnectionManager
from .fnc_tools import (
    set_tools_connection,
    handle_list_tools,
    handle_tool_call
)
from .fnc_resources import (
    handle_list_resources,
    handle_read_resource
)
from .fnc_prompts import (
    handle_list_prompts,
    handle_get_prompt
)
from .auth import (
    OAuthConfig,
    ProtectedResourceMetadata,
    OAuthMiddleware,
    OAuthEndpoints
)
from .oauth_context import OAuthContext, set_oauth_context
from .fnc_common import set_transport

logger = logging.getLogger(__name__)

# Global variables for database connection and OAuth
_connection_manager = None
_db = ""
_oauth_config = None
_oauth_middleware = None
_settings = None

async def initialize_database(settings: Settings):
    """Initialize database connection from environment or command line."""
    global _connection_manager, _db

    # Parse command line arguments for database URL
    parser = argparse.ArgumentParser(description="TDWM MCP Server")
    parser.add_argument("database_url", help="Database connection URL", nargs="?")
    args = parser.parse_args()
    database_url = settings.database_uri or args.database_url

    if not database_url:
        logger.warning("No database URL provided. Database operations will fail.")
        return

    # Initialize database connection
    parsed_url = urlparse(database_url)
    _db = parsed_url.path.lstrip('/')

    try:
        _connection_manager = TeradataConnectionManager(
            database_url=database_url,
            db_name=_db,
            max_retries=settings.max_retries,
            initial_backoff=settings.initial_backoff,
            max_backoff=settings.max_backoff,
            pool_size=settings.pool_size,
            settings=settings,
            acquire_timeout=settings.pool_acquire_timeout,
            breaker_threshold=settings.breaker_threshold,
            breaker_cooldown=settings.breaker_cooldown
        )
        # Register the connection manager with the tool modules now so they
        # can acquire connections from the pool on demand.
        set_tools_connection(
            _connection_manager, _db,
            max_rows=settings.max_rows,
            tool_timeout=settings.tool_timeout,
            tool_timeout_write=settings.tool_timeout_write
        )

        # Pre-warm the pool so no user request pays a Teradata login at
        # ramp-up (may partially fail; tools retry on demand). Then keep
        # idle sessions alive in the background.
        warm_count = settings.pool_warm if settings.pool_warm >= 0 else settings.pool_size
        await _connection_manager.warm(warm_count)
        _connection_manager.start_keepalive()
        logger.info(f"Connection pool initialized (pool_size={settings.pool_size}, warmed={warm_count})")

    except Exception as e:
        logger.warning(
            f"Could not connect to database: {obfuscate_password(str(e))}",
        )
        logger.warning(
            "The MCP server will start but database operations will fail until a valid connection is established.",
        )

async def initialize_oauth():
    """Initialize OAuth 2.1 authentication from environment variables."""
    global _oauth_config, _oauth_middleware

    try:
        # Load OAuth configuration from environment
        _oauth_config = OAuthConfig.from_environment()

        if _oauth_config.enabled:
            # Initialize OAuth components
            metadata = ProtectedResourceMetadata(_oauth_config)
            _oauth_middleware = OAuthMiddleware(_oauth_config, metadata)

            # Set up OAuth context for tools
            oauth_context = OAuthContext(_oauth_config, metadata)
            set_oauth_context(oauth_context)

            logger.info(f"OAuth 2.1 authentication enabled for realm: {_oauth_config.realm}")
            logger.info(f"Authorization server: {_oauth_config.get_issuer_url()}")
            logger.info(f"Required scopes: {_oauth_config.required_scopes}")
        else:
            logger.info("OAuth 2.1 authentication is disabled")
            # Set up empty OAuth context
            set_oauth_context(None)

    except Exception as e:
        logger.warning(f"OAuth initialization failed: {e}")
        logger.warning("Server will start without OAuth authentication")
        _oauth_config = OAuthConfig(enabled=False)
        _oauth_middleware = None
        set_oauth_context(None)

# Create FastMCP app
app = FastMCP("tdwm-mcp")

# Set up the handlers using the internal MCP server for dynamic resources and tools
app._mcp_server.list_tools()(handle_list_tools)
# validate_input=True rejects malformed arguments against each tool's
# inputSchema with a clear error instead of surfacing a KeyError.
app._mcp_server.call_tool(validate_input=True)(handle_tool_call)
app._mcp_server.list_resources()(handle_list_resources)
app._mcp_server.read_resource()(handle_read_resource)
app._mcp_server.list_prompts()(handle_list_prompts)
app._mcp_server.get_prompt()(handle_get_prompt)


@app.custom_route("/metrics", methods=["GET"])
async def streamable_http_metrics(request: Request):
    """Prometheus metrics endpoint for the streamable-http transport."""
    from starlette.responses import Response
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.custom_route("/health", methods=["GET"])
async def streamable_http_health(request: Request):
    """Health check endpoint for the streamable-http transport.

    (The SSE transport registers its own /health in create_starlette_app.)
    """
    from starlette.responses import JSONResponse
    try:
        pool_info = _connection_manager.get_connection_info() if _connection_manager else None
        return JSONResponse(content={
            "status": "healthy",
            "transport": "streamable-http",
            "oauth": {
                "enabled": _oauth_config.enabled if _oauth_config else False,
            },
            "database": {
                "status": "connected" if _connection_manager else "disconnected",
                "pool": pool_info,
            }
        })
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return JSONResponse(status_code=503, content={"status": "unhealthy", "error": str(e)})

def setup_oauth_endpoints():
    """Setup OAuth endpoints for FastMCP app."""
    global _oauth_config, _oauth_middleware

    if _oauth_config and _oauth_config.enabled and _oauth_middleware:
        metadata = ProtectedResourceMetadata(_oauth_config)
        oauth_endpoints = OAuthEndpoints(_oauth_config, metadata, _oauth_middleware)

        # Register OAuth endpoints with the FastAPI app for streamable-http transport
        # Note: For SSE transport, OAuth endpoints are handled in create_starlette_app()
        if hasattr(app, '_app') and hasattr(app._app, 'routes'):
            oauth_endpoints.register_endpoints(app._app)
            logger.info("OAuth endpoints registered with FastAPI app (streamable-http transport)")
        else:
            logger.warning("Could not register OAuth endpoints with FastAPI app")
    else:
        logger.info("OAuth endpoints not registered - OAuth is disabled")

def create_starlette_app(mcp_server: Server, *, debug: bool = False, cors_origins: str = "*") -> Starlette:
    """Create a Starlette application that can serve the provided mcp server with SSE."""
    from starlette.responses import JSONResponse, Response

    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request) -> Response:
        async with sse.connect_sse(
                request.scope,
                request.receive,
                request._send,
        ) as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )
        # Starlette requires route endpoints to return a Response; the SSE
        # stream has already been sent via the raw ASGI interface above.
        return Response()

    async def metrics_endpoint(request: Request) -> Response:
        """Prometheus metrics endpoint for the SSE transport."""
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    # Create base routes for SSE
    routes = [
        Route("/sse", endpoint=handle_sse),
        Mount("/messages/", app=sse.handle_post_message),
        Route("/metrics", endpoint=metrics_endpoint, methods=["GET"]),
    ]

    async def health_check(request: Request):
        """Health check endpoint for SSE transport."""
        try:
            health_status = {
                "status": "healthy",
                "transport": "sse",
                "oauth": {
                    "enabled": _oauth_config.enabled if _oauth_config else False,
                    "configured": bool(_oauth_config and _oauth_config.enabled and _oauth_config.keycloak_url and _oauth_config.realm)
                },
                "database": {
                    "status": "connected" if _connection_manager else "disconnected"
                }
            }
            return JSONResponse(content=health_status)
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return JSONResponse(status_code=503, content={"status": "unhealthy", "error": str(e)})

    async def mcp_server_info(request: Request):
        """MCP Server Information endpoint for SSE transport."""
        try:
            info = {
                "name": "tdwm-mcp",
                "version": "0.1.0",
                "description": "Teradata Workload Management MCP Server",
                "transport": "sse",
                "capabilities": {
                    "tools": True,
                    "resources": True,
                    "prompts": True,
                    "dynamic_resources": True
                },
                "authentication": {
                    "oauth2": {
                        "enabled": _oauth_config.enabled if _oauth_config else False,
                        "authorization_server": _oauth_config.get_issuer_url() if (_oauth_config and _oauth_config.enabled) else None,
                        "flows_supported": ["authorization_code", "client_credentials"] if (_oauth_config and _oauth_config.enabled) else [],
                        "scopes_supported": [
                            "tdwm:read", "tdwm:write", "tdwm:admin",
                            "tdwm:query", "tdwm:monitor", "tdwm:workload"
                        ] if (_oauth_config and _oauth_config.enabled) else [],
                        "protected_resource_metadata": "/.well-known/oauth-protected-resource" if (_oauth_config and _oauth_config.enabled) else None
                    }
                },
                "endpoints": {
                    "sse": "/sse",
                    "messages": "/messages/",
                    "health": "/health",
                    "protected_resource_metadata": "/.well-known/oauth-protected-resource" if (_oauth_config and _oauth_config.enabled) else None
                }
            }
            return JSONResponse(content=info)
        except Exception as e:
            logger.error(f"Error generating MCP server info: {e}")
            return JSONResponse(status_code=500, content={"error": "Internal server error"})

    async def oauth_endpoints_preflight(request: Request):
        """Handle CORS preflight requests for OAuth endpoints."""
        return JSONResponse(
            content={},
            headers={
                "Access-Control-Allow-Origin": cors_origins,
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Authorization, Content-Type",
                "Access-Control-Max-Age": "3600"
            }
        )

    # Add OAuth endpoints if OAuth is enabled
    if _oauth_config and _oauth_config.enabled and _oauth_middleware:
        # Create metadata handler for OAuth endpoints
        metadata = ProtectedResourceMetadata(_oauth_config)

        async def oauth_protected_resource_metadata(request: Request):
            """OAuth Protected Resource Metadata endpoint for SSE transport."""
            try:
                metadata_dict = metadata.get_metadata()
                return JSONResponse(
                    content=metadata_dict,
                    headers={
                        "Content-Type": "application/json",
                        "Cache-Control": "max-age=3600",
                        "Access-Control-Allow-Origin": cors_origins,
                        "Access-Control-Allow-Methods": "GET",
                        "Access-Control-Allow-Headers": "Authorization"
                    }
                )
            except Exception as e:
                logger.error(f"Error generating protected resource metadata: {e}")
                return JSONResponse(
                    status_code=500,
                    content={"error": "Internal server error"}
                )

        # Add OAuth routes to Starlette
        routes.extend([
            Route("/.well-known/oauth-protected-resource", endpoint=oauth_protected_resource_metadata, methods=["GET"]),
            Route("/.well-known/mcp-server-info", endpoint=mcp_server_info, methods=["GET"]),
            Route("/health", endpoint=health_check, methods=["GET"]),
            # CORS preflight routes
            Route("/.well-known/oauth-protected-resource", endpoint=oauth_endpoints_preflight, methods=["OPTIONS"]),
            Route("/.well-known/mcp-server-info", endpoint=oauth_endpoints_preflight, methods=["OPTIONS"]),
            Route("/health", endpoint=oauth_endpoints_preflight, methods=["OPTIONS"]),
        ])

        logger.info("OAuth endpoints added to SSE Starlette app")

    else:
        routes.extend([
            Route("/health", endpoint=health_check, methods=["GET"]),
            Route("/.well-known/mcp-server-info", endpoint=mcp_server_info, methods=["GET"]),
        ])

    return Starlette(
        debug=debug,
        routes=routes,
    )

async def main():
    """Main entry point for the server."""
    global _settings

    # Configure logging
    logging.basicConfig(level=logging.INFO)

    # Load settings once from environment
    _settings = settings_from_env()

    # Size the default executor explicitly: every DB call occupies one worker
    # thread, and the CPython default caps at min(32, cpu+4) — raising
    # DB_POOL_SIZE past that would silently queue DB work behind the cap.
    executor = ThreadPoolExecutor(
        max_workers=_settings.pool_size + 8,
        thread_name_prefix="tdwm-db",
    )
    asyncio.get_running_loop().set_default_executor(executor)

    # Set transport for per-tool QueryBand
    set_transport(_settings.mcp_transport)

    # Initialize OAuth authentication
    await initialize_oauth()

    # Initialize database connection
    await initialize_database(_settings)

    # Setup OAuth endpoints after initialization
    setup_oauth_endpoints()

    mcp_transport = _settings.mcp_transport
    logger.info(f"MCP_TRANSPORT: {mcp_transport}")

    # Start the MCP server
    try:
        if mcp_transport == "sse":
            app.settings.host = _settings.mcp_host
            app.settings.port = _settings.mcp_port
            logger.info(f"Starting MCP server on {app.settings.host}:{app.settings.port}")
            mcp_server = app._mcp_server
            starlette_app = create_starlette_app(
                mcp_server, debug=True, cors_origins=_settings.cors_allowed_origins
            )
            config = uvicorn.Config(starlette_app, host=app.settings.host, port=app.settings.port, log_level="info")
            server = uvicorn.Server(config)
            await server.serve()

        elif mcp_transport == "streamable-http":
            app.settings.host = _settings.mcp_host
            app.settings.port = _settings.mcp_port
            app.settings.streamable_http_path = _settings.mcp_path
            # Stateless mode: no Mcp-Session-Id affinity, so N replicas can
            # sit behind a plain round-robin load balancer.
            app.settings.stateless_http = _settings.mcp_stateless_http
            app.settings.json_response = _settings.mcp_json_response
            logger.info(
                f"Starting MCP server on {app.settings.host}:{app.settings.port} "
                f"with path {app.settings.streamable_http_path} "
                f"(stateless={_settings.mcp_stateless_http})"
            )
            await app.run_streamable_http_async()
        else:
            logger.info("Starting MCP server on stdin/stdout")
            await app.run_stdio_async()
    finally:
        # Graceful drain: stop keepalive and log off pooled sessions
        if _connection_manager:
            await _connection_manager.close()

if __name__ == "__main__":
    asyncio.run(main())
