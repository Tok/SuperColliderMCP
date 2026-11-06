"""Run the MCP server over stdio: `supercollider-mcp` or `python -m supercollidermcp`."""

from __future__ import annotations

import argparse
import logging
import sys

from . import __version__
from .engine import Engine
from .osc import SCClient
from .server import config_from_env, create_server


def main(argv: list[str] | None = None) -> None:
    host, port = config_from_env()
    parser = argparse.ArgumentParser(prog="supercollider-mcp", description="MCP server for SuperCollider (stdio)")
    parser.add_argument("--host", default=host, help=f"scsynth host (env SC_HOST, default {host})")
    parser.add_argument("--port", type=int, default=port, help=f"scsynth UDP port (env SC_PORT, default {port})")
    parser.add_argument("--log-level", default="WARNING", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    # stdout carries the MCP protocol, so logs must go to stderr
    logging.basicConfig(level=args.log_level, stream=sys.stderr, format="%(levelname)s %(name)s: %(message)s")
    create_server(Engine(SCClient(args.host, args.port))).run()


if __name__ == "__main__":
    main()
