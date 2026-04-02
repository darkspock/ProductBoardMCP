"""Entry point: python -m src"""

import os
from dotenv import load_dotenv

load_dotenv()

from src.server import mcp

transport = os.getenv("MCP_TRANSPORT", "stdio")

if transport == "httpStream":
    port = int(os.getenv("PORT", "3000"))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
else:
    mcp.run(transport="stdio")
