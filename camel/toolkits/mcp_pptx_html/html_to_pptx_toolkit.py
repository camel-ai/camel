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
from camel.toolkits.base import BaseToolkit
from camel.toolkits import MCPToolkit
import os
import subprocess
from camel.toolkits.base import FunctionTool
from camel.utils import MCPServer

@MCPServer()
class HTMLToPPTXToolkit(BaseToolkit):
    def __init__(self):
        super().__init__()
        self.config_path = "camel/toolkits/mcp_pptx_html/mcp_config.json"
        self.node_project_path = "camel/toolkits/mcp_pptx_html/"
        self._init_node_modules()

    def _init_node_modules(self):
        if not os.path.exists(os.path.join(self.node_project_path, 'node_modules')):
            print("Installing Node modules...")
            subprocess.run(['npm', 'install'], cwd=self.node_project_path, check=True)
        else:
            print("Node modules already installed.")

    

    async def convert_htmls_to_pptx(self, html_list: list[str], output_path: str):
        r"""
        Convert a list of HTML strings to a multi-slide PPTX using the MCPToolkit.
        Args:
            html_list: List of HTML contents for each slide.
            output_path: Path to save the PPTX file.
        Returns:
            The result from the MCP tool call.
        """
        async with MCPToolkit(config_path=self.config_path, timeout=120) as mcp_toolkit:
            await mcp_toolkit.connect()
            result = await mcp_toolkit.call_tool(
                "convert_html_to_pptx",
                {"htmlList": html_list, "outputPath": output_path},
            )
            await mcp_toolkit.disconnect()
            return result

    def get_tools(self):
        return [FunctionTool(self.convert_htmls_to_pptx)]

    

