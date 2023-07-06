# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
from typing import Any, Dict, Optional, Tuple

from colorama import Fore

from camel.agents import BaseToolAgent, ChatAgent
from camel.agents.chat_agent import ChatAgentResponse
from camel.messages import BaseMessage
from camel.typing import ModelType
from camel.utils import print_text_animated

# Color settings for logging
TASK_COLOR = Fore.LIGHTYELLOW_EX
THOUGHT_COLOR = Fore.LIGHTCYAN_EX
ACTION_COLOR = Fore.LIGHTRED_EX
OBSERVE_COLOR = Fore.LIGHTGREEN_EX


class ReActAgent(ChatAgent):
    r"""
    Class for managing conversions of a CAMEL agent following ReAct pattern.

    Args:
        system_message (BaseMessage): The system message for ReAct agent,
            to be augmented by descriptions of actions
        model (ModelType, optional): The LLM model to use for generating
            responses. (default :obj:`ModelType.GPT_4`)
        model_config (Any, optional): Configuration options for the LLM model.
            (default: :obj:`None`)
        message_window_size (int, optional): The maximum number of previous
            messages to include in the context window. If `None`, no windowing
            is performed. (default: :obj:`None`)
        action_space (Dict[Any], optional): The action space for the ReAct
            agent. (default: :obj:`None`)
        verbose (bool, optional): Whether to print the critic's messages.
    """

    def __init__(
        self,
        system_message: BaseMessage,
        model: ModelType = ModelType.GPT_4,
        model_config: Optional[Any] = None,
        message_window_size: Optional[int] = None,
        action_space: Dict[str, BaseToolAgent] = None,
        verbose: bool = False,
    ) -> None:
        self.action_space = action_space

        action_space_prompt = self.get_action_space_prompt()
        system_message.content += action_space_prompt

        self.verbose = verbose
        super().__init__(
            system_message=system_message,
            model=model,
            model_config=model_config,
            message_window_size=message_window_size,
        )

    def get_action_space_prompt(self) -> str:
        r"""Returns the action space prompt.

        Returns:
            str: The action space prompt.
        """
        tool_agents = set()
        for agent in self.action_space.values():
            tool_agents.add(agent)

        return "\n".join(agent.description for agent in tool_agents)

    @staticmethod
    def parse_thought_and_action(
            response: ChatAgentResponse) -> Tuple[str, str, str]:
        r"""
        Parse the given response into a Thought and an Action with
        the keyword

        Args:
            response (ChatAgentResponse): the response returned
                by the agent

        Returns:
            Tuple[str, str, str]: the tuple of the thought, the action name
                and the input to the action
        """

        response_msg = response.msg.content

        tht_idx = response_msg.find('Thought')
        act_idx = response_msg.find('Action')

        if tht_idx == -1:
            raise ValueError(
                f"No valid action found in the response: {response_msg}")
        elif act_idx == -1:
            raise ValueError(
                f"No valid thought found in the response: {response_msg}")
        else:
            tht_idx += len('Thought: ')
            thought = response_msg[tht_idx:act_idx]

            act_idx += len('Action: ')
            act_str = response_msg[act_idx:]
            action = act_str.split('[')[0]
            action_input = act_str[:-1].split('[')[1]

            return thought, action, action_input

    def step(
        self,
        input_message: BaseMessage,
        max_turns: int = 10,
    ) -> Tuple[BaseMessage, Dict[str, Any]]:
        r"""Performs a step in the conversation.

        Args:
            input_message (BaseMessage): The input message,
                which should specify a task to do

        Returns:
            Tuple[BaseMessage, int Dict[str, Any]]: A tuple
                containing the output messages, the number of turns
                and additional information.
        """
        response = super().step(input_message)

        if response.msgs is None or len(response.msgs) == 0:
            raise RuntimeError("Got None output messages.")
        if response.terminated:
            raise RuntimeError(f"{self.__class__.__name__} step failed.")

        if self.verbose:
            print_text_animated(TASK_COLOR +
                                f"> Task: {input_message.content}")

        cnt = 0
        content = input_message.content
        while cnt < max_turns:
            cnt += 1
            content += f"\n{response.msg.content}"

            # Add the thought and action into the agent's conversation history
            self.submit_message(
                BaseMessage(role_name=self.role_name, role_type=self.role_type,
                            meta_dict=self.system_message.meta_dict,
                            content=response.msg.content))

            # Parse the new output containing a pair of Thought and Action
            thought, action, action_input = \
                self.parse_thought_and_action(response)

            if self.verbose:
                print_text_animated(THOUGHT_COLOR + f"> Thought: {thought}")
                print_text_animated(ACTION_COLOR +
                                    f"> Action: {action}[{action_input}]")

            # Terminate
            if action == 'Finish' or cnt == max_turns:
                break

            # operation argument is for ToolAgent providing multiple actions
            obs = str(self.action_space[action].step(action_input,
                                                     operation=action))
            if self.verbose:
                print_text_animated(OBSERVE_COLOR + f"> Observation: {obs}")

            # TODO not sure which type of message should be used
            obs = BaseMessage(
                role_type=self.role_type,
                role_name=self.system_message.role_name,
                meta_dict=self.system_message.meta_dict,
                content=obs,
            )
            response = super().step(obs)

        # Note the output emits all previous messages which has already
        # been added into the Agent's conversation history in the previous
        # loop. RolePlaying should not update the conversation history by
        # this output again.
        finish_msg = BaseMessage(role_name=self.role_name,
                                 role_type=self.role_type,
                                 meta_dict=input_message.meta_dict,
                                 content=content)
        return finish_msg, cnt, response.info
