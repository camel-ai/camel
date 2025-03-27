# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
import argparse
import os
import sys

from camel.toolkits import GithubToolkit

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run GitHub Toolkit with MCP server mode.",
        usage=f"python {sys.argv[0]} <repo_name> [--mode MODE] [--token "
        "TOKEN]",
    )
    parser.add_argument(
        "repo_name", help="GitHub repository name (e.g., 'camel-ai/camel')"
    )
    parser.add_argument(
        "--mode",
        choices=["stdio", "sse"],
        default="stdio",
        help="MCP server mode (default: 'stdio')",
    )
    parser.add_argument(
        "--token",
        help="GitHub access token (optional, defaults to GITHUB_ACCESS_TOKEN "
        "env var)",
    )
    args = parser.parse_args()

    access_token = args.token or os.getenv("GITHUB_ACCESS_TOKEN")
    if not access_token:
        print("Error: GitHub access token is required.")
        print(
            "  Provide it via --token or set GITHUB_ACCESS_TOKEN environment "
            "variable."
        )
        sys.exit(1)

    gt = GithubToolkit(repo_name=args.repo_name, access_token=access_token)
    gt.mcp.run(args.mode)
