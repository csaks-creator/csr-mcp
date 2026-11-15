import os

import fastapi_mcp.transport.http as _http_transport
from fastapi import Depends, FastAPI
from fastapi_mcp import AuthConfig, FastApiMCP
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

from app.security import verify_token
from app.tools import router


class _StatelessSessionManager(StreamableHTTPSessionManager):
    def __init__(self, **kwargs):
        super().__init__(**{**kwargs, "stateless": True})


# fastapi-mcp 0.4 hard-codes stateful sessions; stateless lets any task behind the load balancer serve any request.
if os.environ.get("MCP_STATELESS", "1") == "1":
    _http_transport.StreamableHTTPSessionManager = _StatelessSessionManager

app = FastAPI(title="nova-act-mcp", description="Browser automation tools powered by Amazon Nova Act")


@app.get("/health", include_in_schema=False)
def health() -> str:
    return "ok"


app.include_router(router)

# Build the MCP server after all routes are registered; only the tagged routes become tools.
mcp = FastApiMCP(
    app,
    name="nova-act-mcp",
    include_tags=["nova"],
    auth_config=AuthConfig(dependencies=[Depends(verify_token)]),
)
mcp.mount_http()  # served at /mcp
