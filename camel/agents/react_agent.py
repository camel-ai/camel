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
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field

from camel.agents import ChatAgent
from camel.logger import get_logger
from camel.messages import BaseMessage
from camel.models import BaseModelBackend
from camel.responses import ChatAgentResponse
from camel.toolkits import FunctionTool
from camel.types import RoleType
from camel.utils import track_agent

logger = get_logger(__name__)


class ReActStep(BaseModel):
    r"""Structured format for ReAct steps"""

    thought: str = Field(description="Reasoning about current situation")
    action: str = Field(description="Action to take (Search/Lookup/Finish)")
    observation: Optional[str] = Field(
        None, description="Results of the action"
    )


class ReActActionSpace(Enum):
    r"""Available actions in the ReAct framework as
    defined in the original paper.

    References:
        https://arxiv.org/pdf/2210.03629
    """

    SEARCH = "Search"
    LOOKUP = "Lookup"
    FINISH = "Finish"


@track_agent(name="ReActAgent")
class ReActAgent(ChatAgent):
    r"""ReAct Agent that combines reasoning and acting through:
    - Thought: Reasoning about current state
    - Action: Deciding what action to take
    - Observation: Getting results of actions

    Args:
        system_message (BaseMessage): The system message for initializing the
            agent's conversation context.
        model (Optional[BaseModelBackend], optional): The model backend to use
            for response generation. (default: :obj:`None`)
        tools (Optional[List[Union[FunctionTool, Callable]]], optional): List
            of available tools that can be used to execute actions. Tools can
            be either FunctionTool instances or callable functions.
            (default: :obj:`None`)
        max_steps (int, optional): Maximum number of reasoning steps before
            forced termination. Prevents infinite loops.
            (default: :obj:`10`)
    """

    def __init__(
        self,
        system_message: BaseMessage,
        model: Optional[BaseModelBackend] = None,
        tools: Optional[List[Union[FunctionTool, Callable]]] = None,
        max_steps: int = 10,
    ) -> None:
        self._set_react_prompt()

        # Combine original system message with ReAct prompt
        combined_content = (
            f"{system_message.content}\n\n" f"{self.react_prompt}"
        )
        react_system_message = system_message.create_new_instance(
            combined_content
        )

        super().__init__(
            system_message=react_system_message, model=model, tools=tools
        )
        self.scratchpad: List[Dict[str, Optional[str]]] = []
        self._set_react_prompt()
        self.step_count = 0
        self.max_steps = max_steps
        logger.debug("ReActAgent initialized with %d tools", len(self.tools))

    def _set_react_prompt(self) -> None:
        r"""Set up the ReAct prompt template following the paper's format.

        This method initializes the prompt template that guides the agent's
        response format and behavior.
        """
        self.react_prompt = (
            "You MUST ALWAYS use EXACTLY ONE of the following actions. "
            "You MUST ALWAYS include a 'thought' and 'action'.\n"
            "- Search(query=<search terms>):Use this to search information\n"
            "- Lookup(key=<exact key>): Use this to look up specific info\n"
            "- Finish(answer=<final answer>): ONLY use this when you have ALL "
            "information needed to fully answer the question\n\n"
            "IMPORTANT: DO NOT use Finish until you are completely certain you"
            "gathered all necessary information to provide complete answer\n\n"
            "Respond with JSON object with the keys 'thought' and 'action'.\n"
            "The 'action' value must be one of the three options above.\n"
            "\nExample response for Search:\n"
            '{\n'
            '    "thought": "I need to find current population data",\n'
            '    "action": "Search(query=Paris population estimate 2024)"\n'
            '}\n\n'
            "Example response for continuing research:\n"
            '{\n'
            '    "thought": "I found the population,but need to verify.",\n'
            '    "action": "Search(query=Paris census official data latest)"\n'
            '}\n\n'
            "Example response for Finish (only when task is fully complete):\n"
            '{\n'
            '    "thought":"I have found and verified needed information",\n'
            '    "action": "Finish(answer=Paris population is 2.1M)"\n'
            '}\n\n'
            "Current scratchpad:\n"
            "{scratchpad}"
        )
        logger.debug("ReAct prompt template set")

    def _format_scratchpad(self) -> str:
        r"""Format the scratchpad history for inclusion in prompts.

        Returns:
            str: A formatted string containing the history of thoughts,
                actions, and observations. Returns empty string if no
                history exists.
        """
        if not self.scratchpad:
            return ""

        formatted = ""
        for step in self.scratchpad:
            for key, value in step.items():
                if value:
                    formatted += f"{key}: {value}\n"
            formatted += "\n"
        return formatted.rstrip()

    def _handle_max_steps(self) -> ChatAgentResponse:
        r"""Handle the case when maximum steps are reached.

        Returns:
            ChatAgentResponse: A response object containing:
                - msgs: List[BaseMessage] with termination message
                - terminated: Set to True
                - info: Dictionary with thought, action, observation details
        """
        logger.warning("Maximum steps reached, terminating execution")
        final_message = BaseMessage(
            role_name="Assistant",
            role_type=RoleType.ASSISTANT,
            meta_dict={},
            content="Maximum number of steps reached. Terminating execution.",
        )

        return ChatAgentResponse(
            msgs=[final_message],
            terminated=True,
            info={
                "thought": "Maximum steps reached",
                "action": "",
                "observation": "Task terminated due to step limit",
            },
        )

    def _parse_action(self, action: str) -> Tuple[str, Dict[str, Any]]:
        r"""Parse action string into function name and arguments.

        Args:
            action (str): Action string in format,
                         "Action(param1=value1, param2=value2)"

        Returns:
            Tuple[str, Dict[str, Any]]: Function name and arguments dictionary

        Raises:
            ValueError: If action string is malformed
        """
        try:
            # Check if action is empty or malformed
            if not action or '(' not in action or not action.endswith(')'):
                raise ValueError(f"Malformed action: {action}")

            # Extract function name
            func_name = action[: action.find('(')].strip()
            if not func_name:
                raise ValueError("Empty function name")

            # Extract arguments string
            args_str = action[action.find('(') + 1 : action.rfind(')')].strip()

            # Handle empty arguments case
            if not args_str:
                return func_name, {}

            # Convert to proper JSON format
            # Replace "=" with ": " and add quotes around keys
            json_str = "{"
            for param in args_str.split(','):
                if '=' not in param:
                    continue
                key, value = param.split('=', 1)
                key = key.strip()
                value = value.strip()
                # Add quotes if not already present
                if not (value.startswith('"') and value.endswith('"')):
                    value = f'"{value}"'
                json_str += f'"{key}": {value},'
            json_str = json_str.rstrip(',') + "}"

            # Parse JSON string
            args = json.loads(json_str)
            return func_name, args

        except Exception as e:
            logger.error(f"Failed to parse action '{action}': {e!s}")
            raise ValueError(f"Failed to parse action: {e!s}")

    def _execute_action(self, action: str) -> str:
        r"""Execute an action using available tools.

        Args:
            action (str): The action string in format Action(params)
                e.g., "Search(query=Paris population 2024)"
                or "Finish(answer=The population is 2.1M)"

        Returns:
            str: The result of the action execution
        """
        logger.debug("Executing action: %s", action)

        if action.startswith("Finish"):
            logger.info("Task completion requested")
            return "Task completed."

        if not self.tools:
            logger.warning("No tools available to execute action")
            return "No tools available to execute action."

        try:
            # Parse action using robust parser
            func_name, params = self._parse_action(action)

            # Find and execute matching tool
            for tool in self.tools:
                if isinstance(tool, FunctionTool):
                    if (
                        tool.openai_tool_schema["function"]["name"].lower()
                        == func_name.lower()
                    ):
                        return tool(**params)
                elif callable(tool):
                    return tool(action)

            logger.warning(f"No suitable tool found for action: {action}")
            return f"No tool found matching {func_name}"

        except ValueError as e:
            error_msg = f"Invalid action format: {e}"
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Error executing action: {e}"
            logger.error(error_msg)
            return error_msg

    def step(
        self,
        input_message: Union[BaseMessage, str],
        response_format: Optional[type[BaseModel]] = None,
        **kwargs: Any,
    ) -> ChatAgentResponse:
        r"""Perform ReAct cycles until task completion or max steps reached.

        Args:
            input_message (Union[BaseMessage, str]): Initial input message.
            response_format (Optional[type[BaseModel]], optional): Expected
                    response format.
            **kwargs: Additional arguments passed to underlying model call.

        Returns:
            ChatAgentResponse: Final response containing:
                - msgs: List with final message containing thought, action,
                        observation
                - terminated: True if task finished or max steps reached
                - info: Dictionary with final thought, action,
                        observation details
        """
        # Convert string input to BaseMessage if needed
        if isinstance(input_message, str):
            input_message = BaseMessage(
                role_name="User",
                role_type=RoleType.USER,
                meta_dict={},
                content=input_message,
            )

        current_message = input_message
        final_thought = ""
        final_action = ""
        final_observation = ""

        while True:
            # Check for max steps
            if self.step_count >= self.max_steps:
                logger.warning("Maximum steps (%d) reached", self.max_steps)
                return self._handle_max_steps()

            self.step_count += 1
            logger.debug("Starting step %d", self.step_count)

            # Format history and augment message with scratchpad
            history = self._format_scratchpad()
            augmented_content = (
                f"Question: {input_message.content}\n\n"
                f"Previous steps:\n{history if history else 'None'}\n\n"
                "Let's approach this step-by-step:\n"
            )

            augmented_message = BaseMessage(
                role_name=current_message.role_name,
                role_type=current_message.role_type,
                meta_dict=current_message.meta_dict,
                content=augmented_content,
            )

            # Get model response
            response = super().step(
                augmented_message, response_format=ReActStep
            )

            # Parse response
            if (
                hasattr(response.msgs[0], 'parsed')
                and response.msgs[0].parsed
                and isinstance(response.msgs[0].parsed, ReActStep)
            ):
                react_step = response.msgs[0].parsed
                thought = react_step.thought
                action = react_step.action
                observation = react_step.observation
            else:
                logger.error(
                    "Failed to parse model response into ReActStep format"
                )
                thought = ""
                action = ""
                observation = None

            # Execute action if specified
            if action:
                logger.debug("Executing action: %s", action)
                actual_observation = self._execute_action(action)
                observation = actual_observation
            else:
                observation = None

            # Update scratchpad
            scratchpad_entry: Dict[str, Optional[str]] = {
                "Thought": thought or "",
                "Action": action or "",
            }
            if action:
                scratchpad_entry["Observation"] = observation or None
            self.scratchpad.append(scratchpad_entry)

            # Store the latest step's information
            final_thought = thought
            final_action = action
            final_observation = observation or ""

            # Check for termination conditions
            terminated = bool(action and action.startswith("Finish"))
            if terminated:
                logger.info("Task completed after %d steps", self.step_count)
                break

            # Update current message with observation for next iteration
            current_message = BaseMessage(
                role_name=response.msgs[0].role_name,
                role_type=RoleType.ASSISTANT,
                meta_dict={},
                content=str(observation) if observation else "",
            )

        # Create final response message
        final_content = "\n".join(
            filter(
                None,
                [
                    f"Thought: {final_thought}" if final_thought else None,
                    f"Action: {final_action}" if final_action else None,
                    f"Observation: {final_observation}"
                    if final_action and final_observation
                    else None,
                ],
            )
        )

        final_message = BaseMessage(
            role_name=response.msgs[0].role_name,
            role_type=RoleType.ASSISTANT,
            meta_dict=response.msgs[0].meta_dict,
            content=final_content,
        )

        return ChatAgentResponse(
            msgs=[final_message],
            terminated=terminated,
            info={
                "thought": final_thought or "",
                "action": final_action or "",
                "observation": final_observation or "",
            },
        )
