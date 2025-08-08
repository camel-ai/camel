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
import sys

from camel.toolkits import HybridBrowserToolkit

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run HybridBrowserToolkit with MCP server mode.",
        usage=(
            f"python {sys.argv[0]} [--mode MODE] [--timeout TIMEOUT] "
            "[--headless] [--stealth] [--implementation]"
        ),
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
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run browser in headless mode (default: True)",
    )
    parser.add_argument(
        "--no-headless",
        action="store_false",
        dest="headless",
        help="Run browser with UI (disable headless mode)",
    )
    parser.add_argument(
        "--stealth",
        action="store_true",
        default=False,
        help="Enable stealth mode (default: False)",
    )
    parser.add_argument(
        "--implementation",
        choices=["python", "typescript"],
        default="python",
        help="Browser implementation to use (default: 'python')",
    )

    args = parser.parse_args()

    toolkit = HybridBrowserToolkit(
        mode=args.implementation,
        timeout=args.timeout,
        headless=args.headless,
        stealth=args.stealth,
        enabled_tools=None,  # Use default tools
    )

    toolkit.run_mcp_server(mode=args.mode)
