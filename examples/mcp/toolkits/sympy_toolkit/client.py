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
import asyncio
from typing import TYPE_CHECKING, Union

from mcp.types import CallToolResult

from camel.toolkits.mcp_toolkit import MCPToolkit, _MCPServer

if TYPE_CHECKING:
    from mcp import ListToolsResult


async def run_example():
    mcp_toolkit = MCPToolkit(config_path="./mcp_servers_config.json")

    await mcp_toolkit.connect()

    # call the server to list the available tools
    mcp_client: _MCPServer = mcp_toolkit.servers[0]
    res: Union[str, "ListToolsResult"] = await mcp_client.list_mcp_tools()
    if isinstance(res, str):
        raise Exception(res)

    tools = [tool.name for tool in res.tools]
    print(tools)
    """
===============================================================================
['simplify_expression', 'expand_expression', 'factor_expression', 
'solve_linear_system', 'solve_nonlinear_system', 
'solve_univariate_inequality', 'reduce_inequalities', 
'polynomial_representation', 'polynomial_degree', 'polynomial_coefficients', 
'solve_equation', 'find_roots', 'differentiate', 'integrate', 
'definite_integral', 'series_expansion', 'compute_limit', 
'find_critical_points', 'check_continuity', 'compute_determinant', 
'compute_inverse', 'compute_eigenvalues', 'compute_eigenvectors', 
'compute_nullspace', 'compute_rank', 'compute_inner_product'
===============================================================================
    """

    res: CallToolResult = await mcp_client.session.call_tool(
        "simplify_expression",
        {
            'expression': '(x**4 - 16)/(x**2 - 4) + sin(x)**2 + cos(x)**2 + '
            '(x**3 + 6*x**2 + 12*x + 8)/(x + 2)'
        },
    )
    print(res.content[0].text)
    """
===============================================================================
{"status": "success", "result": "2*x**2 + 4*x + 9"}
===============================================================================    
    """

    await mcp_toolkit.disconnect()


if __name__ == "__main__":
    asyncio.run(run_example())
