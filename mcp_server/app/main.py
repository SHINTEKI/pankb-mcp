import os
import logging
from fastmcp import FastMCP
from fastmcp.utilities.logging import configure_logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()

# Configure logging: FastMCP's RichHandler for console + FileHandler for file
configure_logging(level="INFO")

# Add file handler for persistent logs
os.makedirs('logs', exist_ok=True)
file_handler = logging.FileHandler('logs/mcp_server.log')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logging.getLogger().addHandler(file_handler)

# Silence noisy third-party modules
for module in ['mcp', 'httpx', 'httpcore', 'matplotlib', 'pymongo', 'azure', 'fakeredis', 'docket']:
    logging.getLogger(module).setLevel(logging.WARNING)

# Import mcp instances from each module
from app.tools.chart import mcp as chart_mcp
from app.tools.analysis import mcp as analysis_mcp
from app.tools.query import mcp as query_mcp
from app.tools.rag import mcp as rag_mcp
from app.tools.azure_blob import mcp as azure_blob_mcp
from app.resources.data import mcp as data_mcp
from app.prompts.templates import mcp as templates_mcp

# Simple Bearer Token authentication
# Set MCP_API_KEY in .env to enable auth, leave empty to disable
API_KEY = os.getenv("MCP_API_KEY", "")


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Simple Bearer Token auth - checks Authorization: Bearer <key>"""
    async def dispatch(self, request, call_next):
        if not API_KEY:  # No key configured = no auth
            return await call_next(request)
        auth = request.headers.get("Authorization", "")
        if auth == f"Bearer {API_KEY}":
            return await call_next(request)
        return JSONResponse({"error": "Unauthorized"}, status_code=401)


# Main server
mcp = FastMCP(
    name="PanKB-MCP",
    instructions="PanKB MCP Server - Provides genomic data query, analysis, visualization and RAG capabilities",
)

# Mount sub-servers
mcp.mount(chart_mcp)
mcp.mount(analysis_mcp)
mcp.mount(query_mcp)
mcp.mount(rag_mcp)
mcp.mount(azure_blob_mcp)
mcp.mount(data_mcp)
mcp.mount(templates_mcp)


# Create HTTP app (module level, supports uvicorn --reload)
app = mcp.http_app()
if API_KEY:
    app.add_middleware(BearerAuthMiddleware)


logger = logging.getLogger(__name__)

if __name__ == "__main__":
    import uvicorn
    if API_KEY:
        logger.info("Starting server with Bearer token authentication")
    else:
        logger.warning("No MCP_API_KEY set, running without authentication")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
