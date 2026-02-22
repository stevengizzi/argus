"""Standalone entry point for the Argus API server.

Usage:
    python -m argus.api --dev              # Dev mode with mock data
    python -m argus.api --dev --port 3000  # Custom port

Note: Non-dev mode is not supported standalone. For production, start
the API via argus.main which integrates with the full trading engine.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

import uvicorn


def main() -> None:
    """Parse arguments and start the API server."""
    parser = argparse.ArgumentParser(
        description="Argus Command Center API Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m argus.api --dev              Start in dev mode with mock data
    python -m argus.api --dev --port 3000  Use custom port
    python -m argus.api --dev --host 127.0.0.1  Bind to localhost only
        """,
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Run in development mode with mock data",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host address to bind (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port number to bind (default: 8000)",
    )

    args = parser.parse_args()

    if not args.dev:
        print("Non-dev standalone mode is not supported.")
        print("Use --dev for development with mock data, or start via main.py for production.")
        print()
        print("Examples:")
        print("  python -m argus.api --dev              # Dev mode")
        print("  python -m argus.main                   # Production mode")
        sys.exit(1)

    # Dev mode: create mock state and run server
    from argus.api.dev_state import create_dev_state
    from argus.api.server import create_app

    print("Starting Argus API Server in development mode...")
    print(f"  Host: {args.host}")
    print(f"  Port: {args.port}")
    print("  Auth: password is 'argus'")
    print()
    print(f"  API:  http://{args.host}:{args.port}/api/v1")
    print(f"  Docs: http://{args.host}:{args.port}/docs")
    print()

    # Create the dev state asynchronously
    state = asyncio.run(create_dev_state())
    app = create_app(state)

    # Run uvicorn (bridge starts in lifespan handler)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
