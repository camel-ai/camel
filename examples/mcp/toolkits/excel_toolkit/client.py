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
import tempfile
from typing import TYPE_CHECKING, Union

import pandas as pd
from mcp.types import CallToolResult

from camel.toolkits.mcp_toolkit import MCPToolkit, _MCPServer

if TYPE_CHECKING:
    from mcp import ListToolsResult


def create_sample_excel_file(sample_file_path: str):
    # Create a sample DataFrame
    df = pd.DataFrame(
        {
            'Name': ['Alice', 'Bob', 'Charlie'],
            'Age': [25, 30, 35],
            'City': ['New York', 'San Francisco', 'Seattle'],
            'Department': ['Engineering', 'Marketing', 'Finance'],
        }
    )

    # Save the DataFrame to the CSV file
    df.to_csv(sample_file_path, index=False)


async def run_example():
    # Create a sample Excel file for demonstration
    temp_file = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
    sample_file_path = temp_file.name

    create_sample_excel_file(sample_file_path)

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
['extract_excel_content']
===============================================================================
    """

    res1: CallToolResult = await mcp_client.session.call_tool(
        "extract_excel_content",
        {"document_path": sample_file_path},
    )
    print(res1.content[0].text)
    """
===============================================================================
CSV File Processed:
|    | Name    |   Age | City          | Department   |
|---:|:--------|------:|:--------------|:-------------|
|  0 | Alice   |    25 | New York      | Engineering  |
|  1 | Bob     |    30 | San Francisco | Marketing    |
|  2 | Charlie |    35 | Seattle       | Finance      |
===============================================================================    
    """

    await mcp_toolkit.disconnect()


if __name__ == "__main__":
    asyncio.run(run_example())
