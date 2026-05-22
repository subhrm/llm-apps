"""
Main entry point for running the Hacker News Agent SSE server.
Allows execution via `python -m hn_agent` command.
"""

import argparse
import uvicorn


def main() -> None:
    """Parses command line arguments and runs the Uvicorn server."""
    parser = argparse.ArgumentParser(
        description="Run the Hacker News Agent SSE Server (AG-UI)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host address to bind the server to"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8001,
        help="Port number to bind the server to"
    )
    args = parser.parse_args()

    print(f"🚀 Starting Hacker News Agent on http://{args.host}:{args.port}")
    print(f"👉 Connection URL for AG-UI clients: http://{args.host}:{args.port}/chat")
    
    uvicorn.run("hn_agent.server:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
