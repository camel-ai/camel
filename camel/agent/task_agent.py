from typing import Any, List, Optional, Tuple

from camel.agent import ChatAgent
from camel.configs import ChatGPTConfig
from camel.message import SystemMessage, UserChatMessage
from camel.typing import ModeType, RoleType, TaskType


class TaskSpecifyAgent(ChatAgent):

    def __init__(
        self,
        model: ModeType,
        task_type: TaskType = TaskType.AI_SOCIETY,
        model_config: Any = None,
        task_specify_prompt: Optional[str] = None,
        word_limit: int = 50,
    ) -> None:
        if task_specify_prompt is None:
            if task_type == TaskType.AI_SOCIETY:
                task_specify_prompt_path = (
                    "prompts/ai_society/task_specify_prompt.txt")

            if task_type == TaskType.CODE:
                task_specify_prompt_path = (
                    "prompts/code/task_specify_prompt.txt")

            with open(task_specify_prompt_path, "r") as f:
                self.task_specify_prompt = f.read().replace(
                    "<WORD_LIMIT>", str(word_limit))
        else:
            self.task_specify_prompt = task_specify_prompt

        model_config = model_config or ChatGPTConfig(temperature=1.0)

        system_message = SystemMessage(
            role_name="Task Specifier",
            role_type=RoleType.ASSISTANT,
            content="You can make a task more specific.",
        )
        super().__init__(system_message, model, model_config)

    def specify_task(
        self,
        original_task_prompt: str,
        replace_tuples: Optional[List[Tuple[str, str]]] = None,
    ) -> str:
        self.reset()
        self.task_specify_prompt = self.task_specify_prompt.replace(
            "<TASK>", original_task_prompt)

        # TODO: This is a hacky way to replace the role names.
        if replace_tuples is not None:
            for replace_tuple in replace_tuples:
                self.task_specify_prompt = self.task_specify_prompt.replace(
                    replace_tuple[0], replace_tuple[1])
        assert "<" and ">" not in self.task_specify_prompt
        task_msg = UserChatMessage(role_name="Task Specifier",
                                   content=self.task_specify_prompt)
        specified_task_msgs, terminated, _ = self.step(task_msg)
        specified_task_msg = specified_task_msgs[0]

        if terminated:
            raise RuntimeError("Task specification failed.")
        else:
            return specified_task_msg.content


class TaskPlannerAgent(ChatAgent):

    def __init__(
        self,
        model: ModeType,
        model_config: Any = None,
    ) -> None:

        self.task_planner_prompt = (
            "Divide this task into subtasks: <TASK>. Be concise.")

        system_message = SystemMessage(
            role_name="Task Planner",
            role_type=RoleType.ASSISTANT,
            content="You are a helpful task planner.",
        )
        super().__init__(system_message, model, model_config)

    def plan_task(
        self,
        task_prompt: str,
    ) -> str:
        # TODO: Maybe include roles information.
        self.reset()
        self.task_planner_prompt = self.task_planner_prompt.replace(
            "<TASK>", task_prompt)

        task_msg = UserChatMessage(role_name="Task Planner",
                                   content=self.task_planner_prompt)
        sub_tasks_msgs, terminated, _ = self.step(task_msg)
        sub_tasks_msg = sub_tasks_msgs[0]

        if terminated:
            raise RuntimeError("Task planning failed.")
        else:
            return sub_tasks_msg.content
