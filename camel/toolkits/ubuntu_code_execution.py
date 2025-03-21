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

from typing import List
import logging
import json

from camel.toolkits import CodeExecutionToolkit, FunctionTool

logger = logging.getLogger(__name__)

class UbuntuCodeExecutionToolkit(CodeExecutionToolkit):
    """A specialized code execution toolkit for Ubuntu environments.
    
    This toolkit extends the base CodeExecutionToolkit to provide Ubuntu-specific
    configurations and Python path handling.

    Args:
        python_path (str): Path to the Python interpreter in Ubuntu environment.
        verbose (bool): Whether to enable verbose logging.
    """
    
    def __init__(
        self,
        python_path: str = "/usr/bin/python3",
        verbose: bool = False
    ) -> None:
        logger.info("Initializing UbuntuCodeExecutionToolkit")
        super().__init__(verbose=verbose)
        self.python_path = python_path
        logger.info("Python path set to: %s", python_path)

    def get_tools(self) -> List[FunctionTool]:
        """Get the list of tools with Ubuntu-specific configuration.
        
        Returns:
            List[FunctionTool]: List of function tools configured for Ubuntu.
        """
        logger.info("Getting tools from parent class")
        tools = super().get_tools()
        
        for tool in tools:
            logger.debug("Processing tool: %s", tool.get_function_name())
            logger.debug("Tool configuration: %s", json.dumps(tool.__dict__, default=str))
            
            if hasattr(tool, 'command'):
                logger.info("Original command: %s", tool.command)
                if isinstance(tool.command, list):
                    if 'python' in tool.command:
                        idx = tool.command.index('python')
                        tool.command[idx] = self.python_path
                        logger.info("Modified command: %s", tool.command)
            else:
                logger.warning("No command attribute found for tool: %s", 
                             tool.get_function_name())
        
        return tools 