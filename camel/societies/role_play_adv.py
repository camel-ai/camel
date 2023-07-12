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
from typing import Dict, List, Optional, Sequence, Tuple, Union
import re

from camel.agents import (
    ChatAgent,
    CriticAgent,
    TaskPlannerAgent,
    TaskSpecifyAgent,
    PlayerAgent,
)
from camel.agents.chat_agent import ChatAgentResponse
from camel.generators import SystemMessageGenerator
from camel.human import Human
from camel.messages import BaseMessage
from camel.prompts import TextPrompt
from camel.typing import ModelType, RoleType, TaskType


class RolePlaying:
    r"""Role playing between two agents.

    Args:
        assistant_role_name (str): The name of the role played by the
            assistant.
        user_role_name (str): The name of the role played by the user.
        critic_role_name (str): The name of the role played by the critic.
            (default: :obj:`"critic"`)
        task_prompt (str, optional): A prompt for the task to be performed.
            (default: :obj:`""`)
        with_task_specify (bool, optional): Whether to use a task specify
            agent. (default: :obj:`True`)
        with_task_planner (bool, optional): Whether to use a task planner
            agent. (default: :obj:`False`)
        with_critic_in_the_loop (bool, optional): Whether to include a critic
            in the loop. (default: :obj:`False`)
        model_type (ModelType, optional): The type of backend model to use.
            (default: :obj:`ModelType.GPT_3_5_TURBO`)
        task_type (TaskType, optional): The type of task to perform.
            (default: :obj:`TaskType.AI_SOCIETY`)
        assistant_agent_kwargs (Dict, optional): Additional arguments to pass
            to the assistant agent. (default: :obj:`None`)
        user_agent_kwargs (Dict, optional): Additional arguments to pass to
            the user agent. (default: :obj:`None`)
        task_specify_agent_kwargs (Dict, optional): Additional arguments to
            pass to the task specify agent. (default: :obj:`None`)
        task_planner_agent_kwargs (Dict, optional): Additional arguments to
            pass to the task planner agent. (default: :obj:`None`)
        critic_kwargs (Dict, optional): Additional arguments to pass to the
            critic. (default: :obj:`None`)
        sys_msg_generator_kwargs (Dict, optional): Additional arguments to
            pass to the system message generator. (default: :obj:`None`)
        extend_sys_msg_meta_dicts (List[Dict], optional): A list of dicts to
            extend the system message meta dicts with. (default: :obj:`None`)
        extend_task_specify_meta_dict (Dict, optional): A dict to extend the
            task specify meta dict with. (default: :obj:`None`)
        output_language (str, optional): The language to be output by the
            agents. (default: :obj:`None`)
    """

    def __init__(
        self,
        assistant_role_name: str,
        user_role_name: str,
        critic_role_name: str = "critic",
        task_prompt: str = "",
        with_task_specify: bool = True,
        with_task_planner: bool = False,
        with_critic_in_the_loop: bool = False,
        critic_criteria: Optional[str] = None,
        model_type: ModelType = ModelType.GPT_3_5_TURBO,
        task_type: TaskType = TaskType.AI_SOCIETY,
        assistant_agent_kwargs: Optional[Dict] = None,
        user_agent_kwargs: Optional[Dict] = None,
        task_specify_agent_kwargs: Optional[Dict] = None,
        task_planner_agent_kwargs: Optional[Dict] = None,
        critic_kwargs: Optional[Dict] = None,
        sys_msg_generator_kwargs: Optional[Dict] = None,
        extend_sys_msg_meta_dicts: Optional[List[Dict]] = None,
        extend_task_specify_meta_dict: Optional[Dict] = None,
        output_language: Optional[str] = None,
    ) -> None:
        self.with_task_specify = with_task_specify
        self.with_task_planner = with_task_planner
        self.with_critic_in_the_loop = with_critic_in_the_loop
        self.model_type = model_type
        self.task_type = task_type
        sys_msg_generator = SystemMessageGenerator(
            task_type=self.task_type, **(sys_msg_generator_kwargs or {})
        )

        self.round_prompt = sys_msg_generator.sys_prompts[RoleType.PLAYER]

        init_player_1_sys_msg, init_player_2_sys_msg = sys_msg_generator.from_dicts(
            meta_dicts=[{}, {}],
            role_tuples=[
                (assistant_role_name, "begin_prompt"),
                (user_role_name, "begin_prompt"),
            ],
        )

        self.assistant_agent: PlayerAgent = PlayerAgent(
            init_player_2_sys_msg,
            model_type,
            output_language=output_language,
            **(assistant_agent_kwargs or {}),
        )
        self.assistant_sys_msg = self.assistant_agent.system_message

        self.user_agent: PlayerAgent = PlayerAgent(
            init_player_1_sys_msg,
            model_type,
            output_language=output_language,
            **(user_agent_kwargs or {}),
        )
        self.user_sys_msg = self.user_agent.system_message
        self.value_dict = {
            ("J", "J"): [8, 8],
            ("J", "F"): [0, 10],
            ("F", "J"): [10, 0],
            ("F", "F"): [5, 5],
        }
        self.option_res = {assistant_role_name: [], user_role_name: []}

    def init_chat(self) -> Tuple[BaseMessage, List[BaseMessage]]:
        r"""Initializes the chat by resetting both of the assistant and user
        agents, and sending the system messages again to the agents using
        chat messages. Returns the assistant's introductory message and the
        user's response messages.

        Returns:
            A tuple containing an `BaseMessage` representing the
            assistant's introductory message, and a list of `BaseMessage`s
            representing the user's response messages.
        """
        self.assistant_agent.reset()
        self.user_agent.reset()

        # Send the system messages again to the agents using chat messages
        assistant_msg = BaseMessage(
            role_name=self.assistant_sys_msg.role_name,
            role_type="begin_prompt",
            meta_dict=None,
            content=(f"{self.user_sys_msg.content}. "),
        )

        user_msg = BaseMessage(
            role_name=self.user_agent.role_name,
            role_type="begin_prompt",
            meta_dict=None,
            content=f"{self.assistant_sys_msg.content}",
        )

        # assistant_response = self.assistant_agent.step(user_msg)
        # if assistant_response.terminated or assistant_response.msgs is None:
        #     raise ValueError(f"Assistant agent terminated unexpectedly. "
        #                      f"Error info: {assistant_response.info}")

        return user_msg, assistant_msg

    def reduce_message_options(self, messages: Sequence[BaseMessage],) -> BaseMessage:
        r"""Processes a sequence of chat messages, returning the processed
        message. If multiple messages are provided and
        `with_critic_in_the_loop` is `False`, raises a `ValueError`.
        If no messages are provided, a `ValueError` will be raised.

        Args:
            messages: A sequence of `BaseMessage` objects to process.

        Returns:
            A single `BaseMessage` representing the processed message.
        """
        if len(messages) == 0:
            raise ValueError("No messages to process.")
        if len(messages) > 1 and not self.with_critic_in_the_loop:
            raise ValueError(
                "Got than one message to process. " f"Num of messages: {len(messages)}."
            )
        elif self.with_critic_in_the_loop and self.critic is not None:
            critic_response = self.critic.reduce_step(messages)
            processed_msg = critic_response.msg
        else:
            processed_msg = messages[0]

        return processed_msg

    def step(
        self, user_msg: BaseMessage, assistant_msg: BaseMessage,
    ) -> Tuple[ChatAgentResponse, ChatAgentResponse]:
        r"""Advances the conversation by taking a message from the assistant,
        processing it using the user agent, and then processing the resulting
        message using the assistant agent. Returns a tuple containing the
        resulting assistant message, whether the assistant agent terminated
        the conversation, and any additional assistant information, as well as
        a tuple containing the resulting user message, whether the user agent
        terminated the conversation, and any additional user information.

        Args:
            assistant_msg: A `BaseMessage` representing the message from the
                assistant.

        Returns:
            A tuple containing two ChatAgentResponse: the first struct contains
            the resulting assistant message, whether the assistant agent
            terminated the conversation, and any additional assistant
            information; the second struct contains the resulting user message,
            whether the user agent terminated the conversation, and any
            additional user information.
        """
        user_response = self.user_agent.step(user_msg)
        if user_response.terminated or user_response.msgs is None:
            return (
                ChatAgentResponse([], False, {}),
                ChatAgentResponse([], user_response.terminated, user_response.info),
            )
        user_msg_next = self.reduce_message_options(user_response.msgs)
        self.user_agent.submit_message(user_msg_next)

        assistant_response = self.assistant_agent.step(assistant_msg)
        if assistant_response.terminated or assistant_response.msgs is None:
            return (
                ChatAgentResponse(
                    [], assistant_response.terminated, assistant_response.info
                ),
                ChatAgentResponse([user_msg], False, user_response.info),
            )
        assistant_msg_next = self.reduce_message_options(assistant_response.msgs)
        self.assistant_agent.submit_message(assistant_msg_next)

        return (
            ChatAgentResponse(
                [assistant_msg_next],
                assistant_response.terminated,
                assistant_response.info,
            ),
            ChatAgentResponse(
                [user_msg_next], user_response.terminated, user_response.info
            ),
        )

    def return_choice(self, choice: str) -> Union[str, None]:
        """
        Returns a specific choice based on the input.
        
        Parameters:
        self (object): The object itself.
        choice (str): The input choice.
        
        Returns:
        str or None: The specific choice "J" if "Option J" is in the input,
                    "F" if "Option F" is in the input,
                    None if neither "Option J" nor "Option F" is in the input.
        """
        if "Option J" in choice:
            return "J"
        elif "Option F" in choice:
            return "F"
        else:
            return None

    def generate_next_round_msg(
        self,
        round_num: int,
        you_response: ChatAgentResponse,
        other_response: ChatAgentResponse,
        Player_num: str,
    ) -> BaseMessage:
        """
        Generates the next round message based on the given inputs.
        
        Parameters:
            self (object): The object itself.
            round_num (int): The current round number.
            you_response (ChatAgentResponse): The response from the user agent.
            other_response (ChatAgentResponse): The response from the other agent.
            Player_num (str): The player number.
        
        Returns:
            BaseMessage: The generated message for the next round.
        """
        you_content = you_response.msgs[0].content
        other_content = other_response.msgs[0].content
        you_content = self.return_choice(you_content)
        other_content = self.return_choice(other_content)
        res = self.value_dict[(you_content, other_content)]
        meta_dict = dict(
            pre=round_num,
            ans1=you_content,
            ans2=other_content,
            res1=res[0],
            res2=res[1],
            now=round_num + 1,
        )
        content = self.round_prompt.format(**meta_dict)
        self.option_res[Player_num].append(you_content)
        if Player_num == "Player 1":
            return BaseMessage(
                role_name=self.user_agent.role_name,
                role_type="user",
                meta_dict=meta_dict,
                content=content,
            )
        return BaseMessage(
            role_name=self.assistant_agent.role_name,
            role_type="user",
            meta_dict=meta_dict,
            content=content,
        )
