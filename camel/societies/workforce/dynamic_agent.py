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

import json
from typing import List

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.prompts import TextPrompt
from camel.societies.workforce.tool_selector import (
    ToolSelector,
)
from camel.types import ModelPlatformType, ModelType


class DynamicAgentCreator:
    """
    A class to dynamically create agents based on task content.
    Supports multiple tool discovery strategies including local keyword
    matching, API-based tools, and MCP protocol.
    """

    def __init__(self, mcp_client=None):
        self.selectors: List[ToolSelector] = []

    def _generate_prompt(self, task_content: str) -> dict:
        prompt = TextPrompt(
            """Given the following task, create an optimized role and system
                message for the agent:

            Task: {task_content}

            Output format (JSON):
            {{
                "role": "Role Name",
                "sys_msg": "System message content"
            }}
            """
        ).format(task_content=task_content)

        model_config_dict = ChatGPTConfig(temperature=0.0).as_dict()
        model = ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
            model_config_dict=model_config_dict,
        )

        agent = ChatAgent(system_message=prompt, model=model)
        response = agent.step(task_content)
        result = json.loads(response[0].content)
        return result

    def select_tools(self, task_content: str) -> list:
        for selector in self.selectors:
            tools = selector.select_tools(task_content)
            if tools:
                return tools
        return []

    def create_agent(self, task_content: str) -> ChatAgent:
        # Step 1: Generate system prompt
        prompt_info = self._generate_prompt(task_content)

        # Step 2: Discover tools using all available strategies
        tools = self.select_tools(task_content)

        # Step 3: Build model configuration
        model_config_dict = ChatGPTConfig(
            tools=tools,
            temperature=0.0
        ).as_dict()

        model = ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
            model_config_dict=model_config_dict,
        )

        # Step 4: Create Agent
        sys_msg = BaseMessage.make_assistant_message(
            role_name=prompt_info["role"],
            content=prompt_info["sys_msg"]
        )
        return ChatAgent(sys_msg, model=model, tools=tools)
