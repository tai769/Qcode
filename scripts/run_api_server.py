#!/usr/bin/env python3
"""Start Qcode Web API server."""

import argparse
import logging
from pathlib import Path

from qcode.api.server import run_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

def main() -> None:
    parser = argparse.ArgumentParser(description="Qcode Web API Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    parser.add_argument("--workdir", type=Path, help="Working directory")
    parser.add_argument("--profile", help="Configuration profile")
    args = parser.parse_args()

    print(f"🚀 Starting Qcode Web API server on http://{args.host}:{args.port}")
    print(f"   Workdir: {args.workdir or Path.cwd()}")
    if args.profile:
        print(f"   Profile: {args.profile}")

    run_server(
        host=args.host,
        port=args.port,
        workdir=args.workdir,
        profile=args.profile,
    )


if __name__ == "__main__":
    main()
