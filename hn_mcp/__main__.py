"""
CLI Entry point for Hacker News MCP Server.
Allows executing the module via `python -m hn_mcp`.
"""

import argparse
import os
import uvicorn

from hn_mcp.server import create_app


def main():
    """
    Parses CLI arguments and starts the Uvicorn ASGI server to serve the MCP via SSE.
    """
    parser = argparse.ArgumentParser(description="Hacker News MCP SSE Server")
    parser.add_argument(
        "--host",
        type=str,
        default=os.getenv("HN_MCP_HOST", "127.0.0.1"),
        help="Host address to bind the server to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("HN_MCP_PORT", "8000")),
        help="Port number to run the server on (default: 8000)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable uvicorn auto-reload for development",
    )
    
    args = parser.parse_args()
    
    # Create the Starlette ASGI app
    app = create_app()
    
    print(f"Starting Hacker News MCP SSE Server on http://{args.host}:{args.port}")
    print(f"Endpoints:")
    print(f"  - SSE Connection: GET http://{args.host}:{args.port}/sse")
    print(f"  - Messages Endpoint: POST http://{args.host}:{args.port}/messages")
    
    uvicorn.run(
        "hn_mcp.server:create_app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        factory=True,
    )


if __name__ == "__main__":
    main()
