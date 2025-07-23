import argparse
import sys

from camel.toolkits import TerminalToolkit

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run Terminal Toolkit with MCP server mode.",
        usage=f"python {sys.argv[0]} [--mode MODE] [--timeout TIMEOUT]",
    )
    parser.add_argument(
        "--mode",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="MCP server mode (default: 'stdio')",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Timeout for the MCP server (default: None)",
    )

    args = parser.parse_args()

    toolkit = TerminalToolkit(timeout=args.timeout)

    toolkit.run_mcp_server(mode=args.mode) 