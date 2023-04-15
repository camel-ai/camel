from typing import Dict, List, Optional, Tuple

from camel.generators import SystemMessageGenerator
from camel.human import Human
from camel.messages import AssistantChatMessage, ChatMessage, UserChatMessage
from camel.typing import ModelType, RoleType, TaskType

from .chat_agent import ChatAgent
from .task_agent import TaskPlannerAgent, TaskSpecifyAgent


class RolePlaying:
    r"""Role playing between two agents.

    Args:
        assistant_role_name (str): The name of the role played by the
            assistant.
        user_role_name (str): The name of the role played by the user.
        task_prompt (str, optional): A prompt for the task to be performed.
            (default: :obj:`""`)
        with_task_specify (bool, optional): Whether to use a task specify
            agent. (default: :obj:`True`)
        with_task_planner (bool, optional): Whether to use a task planner
            agent. (default: :obj:`False`)
        with_human_in_the_loop (bool, optional): Whether to include a human in
            the loop. (default: :obj:`False`)
        mode_type (ModelType, optional): The type of GPT model to use.
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
        human_kwargs (Dict, optional): Additional arguments to pass to the
            human. (default: :obj:`None`)
        sys_msg_generator_kwargs (Dict, optional): Additional arguments to
            pass to the system message generator. (default: :obj:`None`)
    """

    def __init__(
        self,
        assistant_role_name: str,
        user_role_name: str,
        task_prompt: str = "",
        with_task_specify: bool = True,
        with_task_planner: bool = False,
        with_human_in_the_loop: bool = False,
        mode_type: ModelType = ModelType.GPT_3_5_TURBO,
        task_type: Optional[TaskType] = TaskType.AI_SOCIETY,
        assistant_agent_kwargs: Optional[Dict] = None,
        user_agent_kwargs: Optional[Dict] = None,
        task_specify_agent_kwargs: Optional[Dict] = None,
        task_planner_agent_kwargs: Optional[Dict] = None,
        human_kwargs: Optional[Dict] = None,
        sys_msg_generator_kwargs: Optional[Dict] = None,
    ) -> None:
        self.with_task_specify = with_task_specify
        self.with_task_planner = with_task_planner
        self.with_human_in_the_loop = with_human_in_the_loop
        self.mode_type = mode_type

        if with_task_specify:
            task_specify_agent = TaskSpecifyAgent(
                self.mode_type,
                task_type=task_type,
                **(task_specify_agent_kwargs or {}),
            )
            self.specified_task_prompt = task_specify_agent.specify_task(
                task_prompt,
                [("<ASSISTANT_ROLE>", assistant_role_name),
                 ("<USER_ROLE>", user_role_name)],
            )
            task_prompt = self.specified_task_prompt
        else:
            self.specified_task_prompt = None

        if with_task_planner:
            task_planner_agent = TaskPlannerAgent(
                self.mode_type,
                **(task_planner_agent_kwargs or {}),
            )
            self.planned_task_prompt = task_planner_agent.plan_task(
                task_prompt)
            task_prompt = f"{task_prompt}\n{self.planned_task_prompt}"
        else:
            self.planned_task_prompt = None

        self.task_prompt = task_prompt

        sys_msg_generator = SystemMessageGenerator(
            task_type=task_type, **(sys_msg_generator_kwargs or {}))
        sys_msg_meta_dicts = [{
            "<ASSISTANT_ROLE>": assistant_role_name,
            "<USER_ROLE>": user_role_name,
            "<TASK>": task_prompt,
        }] * 2
        self.assistant_sys_msg, self.user_sys_msg = (
            sys_msg_generator.from_dicts(
                meta_dicts=sys_msg_meta_dicts,
                role_tuples=[
                    (assistant_role_name, RoleType.ASSISTANT),
                    (user_role_name, RoleType.USER),
                ],
            ))

        self.assistant_agent = ChatAgent(
            self.assistant_sys_msg,
            mode_type,
            **(assistant_agent_kwargs or {}),
        )
        self.user_agent = ChatAgent(
            self.user_sys_msg,
            mode_type,
            **(user_agent_kwargs or {}),
        )

        if with_human_in_the_loop:
            self.human = Human(**(human_kwargs or {}))

    def init_chat(self) -> Tuple[AssistantChatMessage, List[ChatMessage]]:
        r"""Initializes the chat by resetting both the assistant and user
        agents, and sending the system messages again to the agents using
        chat messages. Returns the assistant's introductory message and the
        user's response messages.

        Returns:
            A tuple containing an `AssistantChatMessage` representing the
            assistant's introductory message, and a list of `ChatMessage`s
            representing the user's response messages.
        """
        self.assistant_agent.reset()
        self.user_agent.reset()

        # Send the system messages again to the agents using chat messages
        assistant_msg = AssistantChatMessage(
            role_name=self.assistant_sys_msg.role_name,
            content=(f"{self.user_sys_msg.content}. "
                     "Now start to give me introductions one by one. "
                     "Only reply with Instruction and Input."))
        assistant_msg.role = "user"

        user_msg = UserChatMessage(role_name=self.user_sys_msg.role_name,
                                   content=f"{self.assistant_sys_msg.content}")
        msgs, _, _ = self.assistant_agent.step(user_msg)

        return assistant_msg, msgs

    def process_messages(
        self,
        msgs: List[ChatMessage],
    ) -> ChatMessage:
        r"""Processes a list of chat messages, returning the processed message.
        If multiple messages are provided and `with_human_in_the_loop`
        is `False`, raises a `ValueError`. If no messages are provided, also
        raises a `ValueError`.

        Args:
            msgs: A list of `ChatMessage`s to process.

        Returns:
            A single `ChatMessage` representing the processed message.
        """
        if len(msgs) == 0:
            raise ValueError("No messages to process.")
        if len(msgs) > 1 and not self.with_human_in_the_loop:
            raise ValueError("Got than one message to process. "
                             f"Num of messages: {len(msgs)}.")
        elif self.with_human_in_the_loop:
            processed_msg = self.human.step(msgs)
        else:
            processed_msg = msgs[0]

        processed_msg.role = "user"
        return processed_msg

    def step(
        self,
        assistant_msg: ChatMessage,
    ) -> Tuple[Tuple[Optional[ChatMessage], Optional[bool], Optional[Dict]],
               Tuple[Optional[ChatMessage], Optional[bool], Optional[Dict]]]:
        r"""Advances the conversation by taking a message from the assistant,
        processing it using the user agent, and then processing the resulting
        message using the assistant agent. Returns a tuple containing the
        resulting assistant message, whether or not the assistant agent
        terminated the conversation, and any additional assistant information,
        as well as a tuple containing the resulting user message, whether or
        not the user agent terminated the conversation, and any additional user
        information.

        Args:
            assistant_msg: A `ChatMessage` representing the message from the
                assistant.

        Returns:
            A tuple containing two tuples: the first tuple contains the
            resulting assistant message, whether or not the assistant agent
            terminated the conversation, and any additional assistant
            information; the second tuple contains the resulting user message,
            whether or not the user agent terminated the conversation, and
            any additional user information.
        """
        user_msgs, user_terminated, user_info = self.user_agent.step(
            assistant_msg)
        if user_terminated:
            return ((None, None, None), (None, user_terminated, user_info))
        user_msg = self.process_messages(user_msgs)

        (assistant_msgs, assistant_terminated,
         assistant_info) = self.assistant_agent.step(user_msg)
        if assistant_terminated:
            return ((None, assistant_terminated, assistant_info),
                    (user_msg, user_terminated, user_info))
        assistant_msg = self.process_messages(assistant_msgs)

        return (
            (assistant_msg, assistant_terminated, assistant_info),
            (user_msg, user_terminated, user_info),
        )
