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

from pydantic import BaseModel, Field

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
    r"""
    A class to dynamically create agents based on task content.
    Supports multiple tool discovery strategies.

    Attributes:
        tool_selector (ToolSelector): An instance of ToolSelector used for
            selecting tools based on the task.

    Methods:
        generate_prompt(task_content: str) -> dict:
            Generates a role and system message prompt using an LLM based on
                the provided task content.

        select_tools(task_content: str) -> list:
            Selects relevant tools for the given task using the tool selector.

        create_agent(task_content: str) -> ChatAgent:
            Creates and returns a ChatAgent configured with a generated system
                message and selected tools.
    """

    def __init__(self, tool_selector: ToolSelector):
        r"""
        Initializes the DynamicAgentCreator with a tool selector.

        Args:
            tool_selector (ToolSelector): The tool selector instance to be used
                for tool discovery.
        """
        self.tool_selector = tool_selector

    class PromptModel(BaseModel):
        role: str = Field(description="The role of the assistant.")
        sys_msg: str = Field(
            description="The system message for the assistant."
        )

    def generate_prompt(self, task_content: str) -> PromptModel:
        r"""
        Generates a JSON-formatted prompt containing a role name and system
            message for an agent,
        based on the provided task content using an LLM.

        Args:
            task_content (str): Description of the task for which the agent is
                being created.

        Returns:
            dict: A dictionary containing 'role' and 'sys_msg' keys
                representing the agent's role and system message.
        """
        prompt = TextPrompt(
            """Given the following task, create an optimized role and system
                message for the agent:

            Task: {task_content}
            """
        ).format(task_content=task_content)

        model_config_dict = ChatGPTConfig(temperature=0.0).as_dict()
        model = ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
            model_config_dict=model_config_dict,
        )

        agent = ChatAgent(system_message=prompt, model=model)

        response = agent.step(task_content, response_format=self.PromptModel)
        content_str = response.msgs[0].content
        content_dict = json.loads(content_str)
        return self.PromptModel(**content_dict)

    def select_tools(self, task_content: str) -> list:
        r"""
        Uses the tool selector to find relevant tools for the given task
            content.

        Args:
            task_content (str): Description of the task for which tools are
                being selected.

        Returns:
            list: A list of selected tools suitable for handling the task.
        """
        return self.tool_selector.select_tools(task_content)

    def create_agent(self, task_content: str) -> ChatAgent:
        r"""
        Orchestrates the agent creation process by:
        1. Generating a system prompt using the task content.
        2. Selecting appropriate tools.
        3. Configuring a model with the selected tools.
        4. Creating and returning a ChatAgent instance.

        Args:
            task_content (str): Description of the task for which the agent is
                being created.

        Returns:
            ChatAgent: A fully configured agent ready to execute the task.
        """
        # Step 1: Generate system prompt
        prompt_info = self.generate_prompt(task_content)

        # Step 2: Discover tools using all available strategies
        tools = self.select_tools(task_content)

        # Step 3: Build model configuration
        model_config_dict = ChatGPTConfig(
            tools=tools, temperature=0.0
        ).as_dict()

        model = ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
            model_config_dict=model_config_dict,
        )

        # Step 4: Create Agent
        sys_msg = BaseMessage.make_assistant_message(
            role_name=prompt_info.role, content=prompt_info.sys_msg
        )
        return ChatAgent(sys_msg, model=model, tools=tools)
