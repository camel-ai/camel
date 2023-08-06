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
from collections import deque
from typing import Dict, Optional

from colorama import Fore

from camel.agents import (
    ChatAgent,
    TaskCreationAgent,
    TaskPrioritizeAgent,
    TaskSpecifyAgent,
)
from camel.agents.chat_agent import ChatAgentResponse
from camel.generators import SystemMessageGenerator
from camel.messages import BaseMessage
from camel.prompts import TextPrompt
from camel.typing import RoleType, TaskType
from camel.utils import print_text_animated


class BabyAGI:
    r"""BabyAGI Agent.

    Args:
        assistant_role_name (str): The name of the role played by the
            assistant.
        user_role_name (str): The name of the role played by the user.
        task_prompt (str, optional): A prompt for the task to be performed.
            (default: :obj:`""`)
        with_task_specify (bool, optional): Whether to use a task specify
            agent. (default: :obj:`True`)
        task_type (TaskType, optional): The type of task to perform.
            (default: :obj:`TaskType.AI_SOCIETY`)
        assistant_agent_kwargs (Dict, optional): Additional arguments to pass
            to the assistant agent. (default: :obj:`None`)
        task_specify_agent_kwargs (Dict, optional): Additional arguments to
            pass to the task specify agent. (default: :obj:`None`)
        task_create_agent_kwargs (Dict, optional): Additional arguments to
            pass to the task create agent. (default: :obj:`None`)
        task_prioritize_agent_kwargs (Dict, optional): Additional arguments to
            pass to the task prioritize agent. (default: :obj:`None`)
        sys_msg_generator_kwargs (Dict, optional): Additional arguments to
            pass to the system message generator. (default: :obj:`None`)
        extend_task_specify_meta_dict (Dict, optional): A dict to extend the
            task specify meta dict with. (default: :obj:`None`)
        output_language (str, optional): The language to be output by the
            agents. (default: :obj:`None`)
        message_window_size (int, optional): The maximum number of previous
            messages to include in the context window. If `None`, no windowing
            is performed. (default: :obj:`None`)
    """

    def __init__(
        self,
        assistant_role_name: str,
        user_role_name: str,
        task_prompt: str = "",
        with_task_specify: bool = True,
        task_type: TaskType = TaskType.AI_SOCIETY,
        assistant_agent_kwargs: Optional[Dict] = None,
        task_specify_agent_kwargs: Optional[Dict] = None,
        task_create_agent_kwargs: Optional[Dict] = None,
        task_prioritize_agent_kwargs: Optional[Dict] = None,
        sys_msg_generator_kwargs: Optional[Dict] = None,
        extend_task_specify_meta_dict: Optional[Dict] = None,
        output_language: Optional[str] = None,
        message_window_size: Optional[int] = None,
    ) -> None:
        self.with_task_specify = with_task_specify
        self.task_type = task_type
        self.task_prompt = task_prompt
        self.specified_task_prompt: Optional[TextPrompt] = None
        self.init_specified_task_prompt(assistant_role_name, user_role_name,
                                        task_specify_agent_kwargs,
                                        extend_task_specify_meta_dict,
                                        output_language)

        sys_msg_generator = SystemMessageGenerator(
            task_type=self.task_type, **(sys_msg_generator_kwargs or {}))

        init_assistant_sys_msg = sys_msg_generator.from_dicts(
            meta_dicts=[dict(task=self.task_prompt)],
            role_tuples=[
                (assistant_role_name, RoleType.ASSISTANT),
            ],
        )

        self.assistant_agent: ChatAgent
        self.assistant_sys_msg: BaseMessage
        self.task_creation_agent: TaskCreationAgent
        self.task_prioritize_agent: TaskPrioritizeAgent
        self.init_agents(init_assistant_sys_msg[0], assistant_agent_kwargs,
                         task_create_agent_kwargs,
                         task_prioritize_agent_kwargs, output_language,
                         message_window_size)

        self.tasks = deque([])  # deque
        self.solved_tasks = []  # List[str]
        self.MAX_TASK_HISTORY = 10

    def init_specified_task_prompt(
            self, assistant_role_name: str, user_role_name: str,
            task_specify_agent_kwargs: Optional[Dict],
            extend_task_specify_meta_dict: Optional[Dict],
            output_language: Optional[str]):
        r"""Use a task specify agent to generate a specified task prompt.
        Generated specified task prompt will be used to replace original
        task prompt. If there is no task specify agent, specified task
        prompt will not be generated.

        Args:
            assistant_role_name (str): The name of the role played by the
                assistant.
            user_role_name (str): The name of the role played by the user.
            task_specify_agent_kwargs (Dict, optional): Additional arguments
                to pass to the task specify agent.
            extend_task_specify_meta_dict (Dict, optional): A dict to extend
                the task specify meta dict with.
            output_language (str, optional): The language to be output by the
                agents.
        """
        if self.with_task_specify:
            task_specify_meta_dict = dict()
            if self.task_type in [TaskType.AI_SOCIETY, TaskType.MISALIGNMENT]:
                task_specify_meta_dict.update(
                    dict(assistant_role=assistant_role_name,
                         user_role=user_role_name))
            task_specify_meta_dict.update(extend_task_specify_meta_dict or {})
            task_specify_agent = TaskSpecifyAgent(
                task_type=self.task_type,
                output_language=output_language,
                **(task_specify_agent_kwargs or {}),
            )
            self.specified_task_prompt = task_specify_agent.run(
                self.task_prompt,
                meta_dict=task_specify_meta_dict,
            )
            self.task_prompt = self.specified_task_prompt

    def init_agents(self, init_assistant_sys_msg: BaseMessage,
                    assistant_agent_kwargs: Optional[Dict],
                    task_create_agent_kwargs: Optional[Dict],
                    task_prioritize_agent_kwargs: Optional[Dict],
                    output_language: Optional[str],
                    message_window_size: Optional[int] = None):
        r"""Initialize assistant and user agents with their system messages.

        Args:
            init_assistant_sys_msg (BaseMessage): Assistant agent's initial
                system message.
            assistant_agent_kwargs (Dict, optional): Additional arguments to
                pass to the assistant agent.
            task_create_agent_kwargs (Dict, optional): Additional arguments to
                pass to the task creation agent.
            task_prioritize_agent_kwargs (Dict, optional): Additional arguments
                to pass to the task prioritize agent.
            output_language (str, optional): The language to be output by the
                agents.
            message_window_size (int, optional): The maximum number of previous
                messages to include in the context window. If `None`, no
                windowing is performed. (default: :obj:`None`)
        """
        self.assistant_agent = ChatAgent(
            init_assistant_sys_msg,
            output_language=output_language,
            message_window_size=message_window_size,
            **(assistant_agent_kwargs or {}),
        )
        self.assistant_sys_msg = self.assistant_agent.system_message
        self.assistant_agent.reset()

        self.task_creation_agent = TaskCreationAgent(
            objective=self.task_prompt,
            role_name=self.assistant_sys_msg.role_name,
            output_language=output_language,
            message_window_size=message_window_size,
            **(task_create_agent_kwargs or {}),
        )
        self.task_creation_agent.reset()

        self.task_prioritize_agent = TaskPrioritizeAgent(
            objective=self.task_prompt,
            output_language=output_language,
            message_window_size=message_window_size,
            **(task_prioritize_agent_kwargs or {}),
        )
        self.task_prioritize_agent.reset()

    def step(self) -> ChatAgentResponse:
        r"""BabyAGI agent would pull the first task from the task list,
        complete the task based on the context, then creates new tasks and
        reprioritizes the task list based on the objective and the result of
        the previous task. It returns assistant message.

        Returns:
            ChatAgentResponse: it contains the resulting assistant message,
            whether the assistant agent terminated the conversation,
            and any additional assistant information.

        """
        if not self.tasks:
            new_task_list = self.task_creation_agent.run()
            prio_task_list = self.task_prioritize_agent.run(new_task_list)
            self.tasks = deque(prio_task_list)

        task_name = self.tasks.popleft()
        assistant_msg_msg = BaseMessage.make_user_message(
            role_name=self.assistant_sys_msg.role_name, content=f"{task_name}")

        assistant_response = self.assistant_agent.step(assistant_msg_msg)
        assistant_msg = assistant_response.msgs[0]
        self.assistant_agent.submit_message(assistant_msg)
        self.task_creation_agent.submit_message(assistant_msg)
        self.task_prioritize_agent.submit_message(assistant_msg)

        self.solved_tasks.append(task_name)
        past_tasks = self.solved_tasks + list(self.tasks)

        new_task_list = self.task_creation_agent.run(
            task_list=past_tasks[-self.MAX_TASK_HISTORY:])

        if new_task_list:
            for task in new_task_list:
                self.tasks.append(task)
            prio_task_list = self.task_prioritize_agent.run(
                task_list=list(self.tasks)[-self.MAX_TASK_HISTORY:])
            self.tasks = deque(prio_task_list)
        else:
            print("no new tasks")
        assistant_response.info['task_name'] = task_name
        if not self.tasks:
            terminated = True
            assistant_response.info[
                'termination_reasons'] = "All tasks are solved"
            return ChatAgentResponse([assistant_msg], terminated,
                                     assistant_response.info)
        return ChatAgentResponse([assistant_msg],
                                 assistant_response.terminated,
                                 assistant_response.info)


if __name__ == "__main__":
    model_type = None
    task_prompt = "Develop a trading bot for the stock market"
    babyagi_session = BabyAGI(
        assistant_role_name="Python Programmer",
        assistant_agent_kwargs=dict(model=model_type),
        user_role_name="Stock Trader",
        task_prompt=task_prompt,
        with_task_specify=True,
        task_specify_agent_kwargs=dict(model=model_type),
        message_window_size=5,
    )

    print(Fore.GREEN +
          f"AI Assistant sys message:\n{babyagi_session.assistant_sys_msg}\n")

    print(Fore.YELLOW + f"Original task prompt:\n{task_prompt}\n")
    print(Fore.CYAN +
          f"Specified task prompt:\n{babyagi_session.specified_task_prompt}\n")
    print(Fore.RED + f"Final task prompt:\n{babyagi_session.task_prompt}\n")

    chat_turn_limit, n = 15, 0
    while n < chat_turn_limit:
        n += 1
        assistant_response = babyagi_session.step()

        input_assistant_msg = assistant_response.msg

        if assistant_response.terminated:
            print(Fore.GREEN +
                  ("AI Assistant terminated. Reason: "
                   f"{assistant_response.info['termination_reasons']}."))
            break
        print_text_animated(Fore.RED + "Task Name:\n\n"
                            f"{assistant_response.info['task_name']}\n")

        print_text_animated(Fore.GREEN + "AI Assistant:\n\n"
                            f"{assistant_response.msg.content}\n")
