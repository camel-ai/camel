from typing import Dict, List, Optional, Tuple

from camel.generator import SystemMessageGenerator
from camel.message import AssistantChatMessage, ChatMessage, UserChatMessage
from camel.typing import ModeType, RoleType, TaskType

from .chat_agent import ChatAgent
from .task_agent import TaskPlannerAgent, TaskSpecifyAgent


class RolePlaying:
    """Role playing between two agents."""

    def __init__(
        self,
        assistant_role_name: str,
        user_role_name: str,
        task_prompt: str = "",
        with_task_specify: bool = True,
        with_task_planner: bool = False,
        mode_type: ModeType = ModeType.GPT_3_5_TURBO,
        task_type: Optional[TaskType] = TaskType.AI_SOCIETY,
        assistant_agent_kwargs: Optional[Dict] = None,
        user_agent_kwargs: Optional[Dict] = None,
        task_specify_agent_kwargs: Optional[Dict] = None,
        task_planner_agent_kwargs: Optional[Dict] = None,
        system_message_generator_kwargs: Optional[Dict] = None,
    ) -> None:
        self.with_task_specify = with_task_specify
        self.with_task_planner = with_task_planner

        if with_task_specify:
            task_specify_agent = TaskSpecifyAgent(
                ModeType.GPT_3_5_TURBO,
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
                ModeType.GPT_3_5_TURBO,
                **(task_planner_agent_kwargs or {}),
            )
            self.planned_task_prompt = task_planner_agent.plan_task(
                task_prompt)
            task_prompt = f"{task_prompt}\n{self.planned_task_prompt}"
        else:
            self.planned_task_prompt = None

        self.task_prompt = task_prompt

        sys_msg_generator = SystemMessageGenerator(
            task_type=task_type, **(system_message_generator_kwargs or {}))
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

    def init_chat(self) -> Tuple[AssistantChatMessage, List[ChatMessage]]:
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

    def step(
        self,
        assistant_msg: ChatMessage,
    ) -> Tuple[Tuple[ChatMessage, bool, Dict], Tuple[ChatMessage, bool, Dict]]:
        user_msgs, user_terminated, user_info = self.user_agent.step(
            assistant_msg)
        if user_terminated:
            raise RuntimeError("User agent is terminated.")
        user_msg = user_msgs[0]
        user_msg.role = "user"

        (assistant_msgs, assistant_terminated,
         assistant_info) = self.assistant_agent.step(user_msg)
        if assistant_terminated:
            raise RuntimeError("Assistant agent is terminated.")
        assistant_msg = assistant_msgs[0]
        assistant_msg.role = "user"

        return (
            (assistant_msg, assistant_terminated, assistant_info),
            (user_msg, user_terminated, user_info),
        )
