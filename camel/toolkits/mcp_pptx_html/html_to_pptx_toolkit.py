from camel.toolkits.base import BaseToolkit
from camel.toolkits import MCPToolkit
import os
import subprocess
from camel.toolkits.base import FunctionTool

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

    

    async def convert_htmls_to_pptx(self, html_list, output_path):
        r"""
        Convert a list of HTML strings to a multi-slide PPTX using the MCPToolkit.
        Args:
            html_list (List[str]): List of HTML contents for each slide.
            output_path (str): Path to save the PPTX file.
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

    

