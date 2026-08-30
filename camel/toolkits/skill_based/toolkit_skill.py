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

from typing import Dict, List, Optional, Any

from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool

class ToolkitSkill:
    r"""Wraps a BaseToolkit with skill-based metadata extraction.

    This class provides progressive loading capabilities by extracting
    lightweight metadata first, then loading full tool schemas on demand.

    Args:
        toolkit (BaseToolkit): The toolkit to wrap.
    """

    def __init__(self, toolkit: BaseToolkit):
        self.toolkit = toolkit
        self.toolkit_name = toolkit.__class__.__name__
        self.description = self._extract_toolkit_docstring()
        self._tools: Optional[List[FunctionTool]] = None
        self._tools_metadata: Optional[List[Dict[str, Any]]] = None
    
    def _extract_toolkit_docstring(self) -> str:
        r"""Extract toolkit docstring as metadata.

        Extracts the description part of the docstring, preserving readability.
        Stops at structured sections like Args, Returns, Raises, etc.

        Returns:
            str: The cleaned, readable docstring description.
        """
        docstring = self.toolkit.__class__.__doc__
        if not docstring:
            return f"{self.toolkit_name} toolkit"

        lines = docstring.strip().split('\n')
        clean_lines = []
        
        # Stop at structured sections
        stop_keywords = ['Args:', 'Returns:', 'Raises:', 'Note:', 'Example:', 'Examples:']
        
        for line in lines:
            line = line.strip()
            
            # Skip docstring markers
            if line.startswith('r"""') or line.startswith('"""'):
                continue
            
            # Stop at structured sections
            if any(line.startswith(kw) for kw in stop_keywords):
                break
            
            # Stop at empty line if we already have content
            if not line:
                if clean_lines:
                    break
                continue
            
            clean_lines.append(line)
        
        # Join with single newline to preserve readability
        result = '\n'.join(clean_lines).strip()
        
        # Clean up multiple consecutive spaces within lines
        result = '\n'.join(' '.join(line.split()) for line in result.split('\n'))
        
        return result if result else f"{self.toolkit_name} toolkit"

    def get_metadata(self) -> Dict[str, Any]:
        r"""Get toolkit-level metadata for tool selection.

        Returns:
            Dict[str, Any]: Dictionary containing toolkit name and description.
        """
        return {
            "name": self.toolkit_name,
            "description": self.description,
        }

    def get_tools(self) -> List[FunctionTool]:
        r"""Get full tool list (lazy loading).

        Once toolkit is selected, this method loads all tools from the toolkit.

        Returns:
            List[FunctionTool]: List of FunctionTool objects.
        """
        if self._tools is None:
            self._tools = self.toolkit.get_tools()
        return self._tools

