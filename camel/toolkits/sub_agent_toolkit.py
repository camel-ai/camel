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

from typing import TYPE_CHECKING, Any, List, Optional

from camel.logger import get_logger
from camel.messages import BaseMessage
from camel.toolkits.base import BaseToolkit, RegisteredAgentToolkit
from camel.toolkits.function_tool import FunctionTool

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


class SubAgentToolkit(BaseToolkit, RegisteredAgentToolkit):
    r"""A toolkit for spawning sub-agents to handle specific tasks.

    This toolkit allows a parent agent to create sub-agents that can either:
    1. Inherit the parent agent's memory and context (clone mode)
    2. Start fresh with a custom system prompt (fresh mode)

    The sub-agents execute their tasks independently and return only their
    final results, keeping the parent agent's context clean.
    """

    def __init__(self):
        super(BaseToolkit, self).__init__()
        super(RegisteredAgentToolkit, self).__init__()

    def spawn_sub_agent(
        self,
        task: str,
        inherit_from_parent: bool = False,
        system_prompt: Optional[str] = None,
        model: Optional[Any] = None,
        tools: Optional[List[Any]] = None,
        **kwargs,
    ) -> str:
        r"""Spawn a sub-agent to handle a specific task.

        Args:
            task (str): The task or question for the sub-agent to handle.
            inherit_from_parent (bool, optional): If True, clone the parent
                agent with its memory and context. If False, create a fresh
                agent. (default: :obj:`False`)
            system_prompt (Optional[str], optional): Custom system prompt for
                the sub-agent. Only used when inherit_from_parent=False.
                (default: :obj:`None`)
            model (Optional[Any], optional): Model backend to use for the
                sub-agent. If not provided, uses the parent agent's model.
                (default: :obj:`None`)
            tools (Optional[List[Any]], optional): Tools to provide to the
                sub-agent. (default: :obj:`None`)
            **kwargs: Additional arguments to pass to the sub-agent
                constructor.

        Returns:
            str: The sub-agent's response to the task, or an error message
                if the operation fails.

        Raises:
            ValueError: If neither inherit_from_parent nor system_prompt is
                provided.
        """
        # ensure we have a registered parent agent
        if self.agent is None:
            error_msg = (
                f"No parent agent registered with {self.__class__.__name__}. "
                f"Ensure this toolkit is added to a ChatAgent via "
                f"toolkits_to_register_agent parameter."
            )
            logger.error(error_msg)
            return f"Error: {error_msg}"

        # validate input parameters
        if not inherit_from_parent and system_prompt is None:
            raise ValueError(
                "Either inherit_from_parent must be True or system_prompt "
                "must be provided."
            )

        logger.info(
            f"Spawning sub-agent for task: '{task[:50]}...' "
            f"(inherit: {inherit_from_parent})"
        )

        try:
            # import here to avoid circular imports
            from camel.agents import ChatAgent

            if inherit_from_parent:
                # clone the parent agent with memory
                sub_agent = self.agent.clone(with_memory=True)
                logger.info("Created sub-agent by cloning parent with memory")
            else:
                # create fresh agent with custom system prompt
                agent_model = model or self.agent.model_backend.models

                # create system message from prompt
                if system_prompt:
                    system_message = BaseMessage.make_assistant_message(
                        role_name="Assistant", content=system_prompt
                    )
                else:
                    system_message = None

                sub_agent = ChatAgent(
                    system_message=system_message,
                    model=agent_model,
                    tools=tools or [],
                    **kwargs,
                )
                logger.info("Created fresh sub-agent with custom prompt")

            # execute the task with the sub-agent
            response = sub_agent.step(task)

            # extract the content from the response
            if hasattr(response, 'msg') and hasattr(response.msg, 'content'):
                result = response.msg.content
            else:
                result = str(response)

            logger.info("Sub-agent completed task successfully")
            return result

        except Exception as e:
            error_msg = f"Failed to spawn sub-agent: {e!s}"
            logger.error(error_msg)
            return f"Error: {error_msg}"

    def get_tools(self) -> List[FunctionTool]:
        r"""Get the available tools from this toolkit.

        Returns:
            List[FunctionTool]: List of function tools available in this
                toolkit.
        """
        return [
            FunctionTool(self.spawn_sub_agent),
        ]
