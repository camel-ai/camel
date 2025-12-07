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

from typing import List, Set, Tuple

from camel.agents import ChatAgent
from camel.logger import get_logger
from camel.models import BaseModelBackend
from camel.responses import ChatAgentResponse
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.toolkits.skill_based.toolkit_skill import ToolkitSkill

logger = get_logger(__name__)

class SkillBasedToolLoader:
    r"""Manages progressive tool loading using skill-based approach.

    This class implements a two-stage loading process:
    1. Toolkit selection: Select relevant toolkits based on user task
    2. Tool loading: Load all tools from selected toolkits

    Args:
        toolkits (List[BaseToolkit]): List of toolkits to manage.
    """

    def __init__(self, toolkits: List[BaseToolkit]):
        self.toolkit_skills = [ToolkitSkill(toolkit) for toolkit in toolkits]
        self.selected_toolkit_names: Set[str] = set()

    def _create_toolkit_selector(self) -> FunctionTool:
        r"""Create toolkit selection tool.

        Returns:
            FunctionTool: Tool for selecting toolkits.
        """
        def select_toolkits(
            selected_toolkit_names: List[str],
            reasoning: str = ""
        ) -> str:
            r"""Select relevant toolkits for the task.

            Args:
                selected_toolkit_names: List of toolkit names to select.
                reasoning: Optional reasoning for the selection.

            Returns:
                str: Confirmation message.
            """
            self.selected_toolkit_names = set(selected_toolkit_names)
            names_str = ', '.join(selected_toolkit_names)
            return f"Selected {len(selected_toolkit_names)} toolkit(s): {names_str}"

        return FunctionTool(select_toolkits)

    def _format_toolkit_metadata(self, metadata_list: List[dict]) -> str:
        r"""Format toolkit metadata for display.

        Args:
            metadata_list: List of toolkit metadata dictionaries.

        Returns:
            str: Formatted string for display.
        """
        lines = []
        for i, meta in enumerate(metadata_list, 1):
            lines.append(f"{i}. **{meta['name']}**: {meta['description']}")
        return "\n".join(lines)
    
    def select_toolkits_with_agent(
        self,
        user_task: str,
        model: BaseModelBackend
    ) -> Tuple[List[str], ChatAgentResponse]:
        r"""Select toolkits using an independent agent.

        Args:
            user_task: User's task description.
            model: Model backend for the selection agent.

        Returns:
            Tuple[List[str], ChatAgentResponse]: List of selected toolkit names
                and the agent response for token counting.
        """
        # Prepare toolkit metadata
        toolkit_metadata = [
            skill.get_metadata() for skill in self.toolkit_skills
        ]

        # Create toolkit selection tool
        select_tool = self._create_toolkit_selector()

        # Create independent selection agent
        system_message = f"""You are a toolkit selection assistant. Based on the user's task, select the most relevant toolkits from the available options.

Available toolkits:
{self._format_toolkit_metadata(toolkit_metadata)}

Only select toolkits that are directly relevant to the task. Do not select unnecessary toolkits."""

        selector_agent = ChatAgent(
            system_message=system_message,
            tools=[select_tool],
            model=model
        )

        # Build selection task
        selection_task = f"User task: {user_task}\n\nPlease use the select_toolkits tool to select relevant toolkits."

        # Call agent
        response = selector_agent.step(selection_task)

        # Extract selected toolkits from tool calls
        if response.info and 'tool_calls' in response.info:
            tool_calls = response.info['tool_calls']
            for tool_call in tool_calls:
                if tool_call.tool_name == 'select_toolkits':
                    args = tool_call.args
                    if 'selected_toolkit_names' in args:
                        self.selected_toolkit_names = set(
                            args['selected_toolkit_names']
                        )

        return list(self.selected_toolkit_names), response

    def get_selected_tools(self) -> List[FunctionTool]:
        r"""Get all tools from selected toolkits.

        Returns:
            List[FunctionTool]: List of all tools from selected toolkits.
        """
        selected_tools = []
        for skill in self.toolkit_skills:
            if skill.toolkit_name in self.selected_toolkit_names:
                tools = skill.get_tools()
                selected_tools.extend(tools)

        return selected_tools




    



