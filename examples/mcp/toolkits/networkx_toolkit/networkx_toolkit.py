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

import networkx as nx

from camel.toolkits import NetworkXToolkit

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run Network X Toolkit with MCP server mode.",
        usage=f"python {sys.argv[0]} [--graph_type] [--mode MODE]",
    )
    parser.add_argument(
        "--graph_type",
        choices=['graph', 'digraph', 'multigraph', 'multidigraph'],
        default="digraph",
        help="Type of graph to create (default: 'digraph')",
    )
    parser.add_argument(
        "--mode",
        choices=["stdio", "sse"],
        default="stdio",
        help="MCP server mode (default: 'stdio')",
    )

    args = parser.parse_args()

    toolkit = NetworkXToolkit(args.graph_type)

    toolkit.mcp.run(args.mode)
