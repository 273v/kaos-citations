"""MCP server for kaos-citations.

Exposes 3 tools (extract, validate, doctor) plus the
``kaos-citations://kinds`` resource for taxonomy discovery.

Run::

    kaos-citations-serve              # stdio (for Claude Code)
    kaos-citations-serve --http       # streamable HTTP

Also available via: ``kaos-mcp serve --module citations``
"""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="kaos-citations MCP server")
    parser.add_argument("--http", action="store_true", help="Serve over HTTP")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8084)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args(argv)

    try:
        from kaos_core import KaosRuntime
        from kaos_mcp import KaosMCPServer, KaosMCPSettings  # ty: ignore[unresolved-import]
    except ImportError:
        print(
            "Error: MCP server requires the 'mcp' extra.\n"
            "Install with: pip install 'kaos-citations[mcp]'",
            file=sys.stderr,
        )
        sys.exit(1)

    runtime = KaosRuntime.default()

    from kaos_citations.resources import register_citations_resources
    from kaos_citations.tools import register_citations_tools

    n_tools = register_citations_tools(runtime)
    n_resources = register_citations_resources(runtime)
    print(
        f"Registered {n_tools} citations tools, {n_resources} resources",
        file=sys.stderr,
    )

    settings = KaosMCPSettings(
        name="kaos-citations",
        transport="streamable-http" if args.http else "stdio",
        host=args.host,
        port=args.port,
        debug=args.debug,
    )
    server = KaosMCPServer(runtime=runtime, settings=settings)

    if args.http:
        print(f"Starting HTTP server on {args.host}:{args.port}/mcp", file=sys.stderr)
        server.run_streamable_http()
    else:
        print("Starting stdio server", file=sys.stderr)
        server.run_stdio()


if __name__ == "__main__":
    main()
