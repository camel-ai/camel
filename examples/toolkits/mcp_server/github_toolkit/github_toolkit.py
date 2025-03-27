import os
import sys
import argparse

from camel.toolkits import GithubToolkit


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run GitHub Toolkit with MCP server mode.",
        usage="python client.py <repo_name> [--mode MODE] [--token TOKEN]"
    )
    parser.add_argument(
        "repo_name",
        help="GitHub repository name (e.g., 'camel-ai/camel')"
    )
    parser.add_argument(
        "--mode",
        choices=["stdio", "sse"],
        default="stdio",
        help="MCP server mode (default: 'stdio')"
    )
    parser.add_argument(
        "--token",
        help="GitHub access token (optional, defaults to GITHUB_ACCESS_TOKEN env var)"
    )
    args = parser.parse_args()

    access_token = args.token or os.getenv("GITHUB_ACCESS_TOKEN")
    if not access_token:
        print("Error: GitHub access token is required.")
        print(
            "  Provide it via --token or set GITHUB_ACCESS_TOKEN environment variable."
        )
        sys.exit(1)

    gt = GithubToolkit(repo_name=args.repo_name, access_token=access_token)
    gt.mcp.run(args.mode)
