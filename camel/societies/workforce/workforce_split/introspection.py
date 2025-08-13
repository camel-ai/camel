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
from __future__ import annotations

from typing import Any, Dict, List, Set

from camel.societies.workforce.base import BaseNode
from camel.societies.workforce.role_playing_worker import RolePlayingWorker
from camel.societies.workforce.single_agent_worker import SingleAgentWorker


class IntrospectionHelper:
    r"""Helper class for introspection operations on workforce nodes."""

    def __init__(self):
        r"""Initialize the IntrospectionHelper."""
        pass

    def get_child_nodes_info(self, children: List[BaseNode]) -> str:
        r"""Get the information of all the child nodes under this node.

        Args:
            children (List[BaseNode]): List of child nodes.

        Returns:
            str: Formatted string containing information about all child nodes.
        """
        return "".join(
            f"<{child.node_id}>:<{child.description}>:<{self.get_node_info(child)}>\n"
            for child in children
        )

    def get_node_info(self, node: BaseNode) -> str:
        r"""Get descriptive information for a specific node type.

        Args:
            node (BaseNode): The node to get information for.

        Returns:
            str: Descriptive information about the node type.
        """
        # Import here to avoid circular import
        from camel.societies.workforce.workforce_split.core import (
            WorkforceCore as Workforce,
        )

        if isinstance(node, Workforce):
            return "A Workforce node"
        elif isinstance(node, SingleAgentWorker):
            return self.get_single_agent_info(node)
        elif isinstance(node, RolePlayingWorker):
            return "A Role playing node"
        else:
            return "Unknown node"

    def get_single_agent_info(self, worker: SingleAgentWorker) -> str:
        r"""Get formatted information for a SingleAgentWorker node.

        Args:
            worker (SingleAgentWorker): The single agent worker to get
                information for.

        Returns:
            str: Formatted string containing toolkit and tool information.
        """
        toolkit_tools = self.group_tools_by_toolkit(worker.worker.tool_dict)

        if not toolkit_tools:
            return "no tools available"

        toolkit_info = []
        for toolkit_name, tools in sorted(toolkit_tools.items()):
            tools_str = ', '.join(sorted(tools))
            toolkit_info.append(f"{toolkit_name}({tools_str})")

        return " | ".join(toolkit_info)

    def group_tools_by_toolkit(
        self, tool_dict: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        r"""Group tools by their parent toolkit class names.

        Args:
            tool_dict (Dict[str, Any]): Dictionary mapping tool names to
                tool objects.

        Returns:
            Dict[str, List[str]]: Dictionary mapping toolkit names to lists
                of tool names.
        """
        toolkit_tools: Dict[str, List[str]] = {}

        for tool_name, tool in tool_dict.items():
            if hasattr(tool.func, '__self__'):
                toolkit_name = tool.func.__self__.__class__.__name__
            else:
                toolkit_name = "Standalone"

            if toolkit_name not in toolkit_tools:
                toolkit_tools[toolkit_name] = []
            toolkit_tools[toolkit_name].append(tool_name)

        return toolkit_tools

    def get_valid_worker_ids(self, children: List[BaseNode]) -> Set[str]:
        r"""Get all valid worker IDs from child nodes.

        Args:
            children (List[BaseNode]): List of child nodes.

        Returns:
            Set[str]: Set of valid worker IDs that can be assigned tasks.
        """
        valid_worker_ids = {child.node_id for child in children}
        return valid_worker_ids
