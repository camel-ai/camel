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
import re
from typing import Any, Dict, List, Optional, Union

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.messages import BaseMessage
from camel.prompts import PromptTemplateGenerator, TextPrompt
from camel.typing import ModelType, RoleType, TaskType


class TaskSpecifyAgent(ChatAgent):
    r"""An agent that specifies a given task prompt by prompting the user to
    provide more details.

    Attributes:
        DEFAULT_WORD_LIMIT (int): The default word limit for the task prompt.
        task_specify_prompt (TextPrompt): The prompt for specifying the task.

    Args:
        model (ModelType): The type of model to use for the agent.
            (default: :obj:`ModelType.GPT_3_5_TURBO`)
        task_type (TaskType): The type of task for which to generate a prompt.
            (default: :obj:`TaskType.AI_SOCIETY`)
        model_config (Any): The configuration for the model.
            (default: :obj:`None`)
        task_specify_prompt (Optional[TextPrompt]): The prompt for specifying
            the task. (default: :obj:`None`)
        word_limit (int): The word limit for the task prompt.
            (default: :obj:`50`)
        output_language (str, optional): The language to be output by the
        agent. (default: :obj:`None`)
    """
    DEFAULT_WORD_LIMIT = 50

    def __init__(
        self,
        model: Optional[ModelType] = None,
        task_type: TaskType = TaskType.AI_SOCIETY,
        model_config: Optional[Any] = None,
        task_specify_prompt: Optional[Union[str, TextPrompt]] = None,
        word_limit: int = DEFAULT_WORD_LIMIT,
        output_language: Optional[str] = None,
    ) -> None:

        self.task_specify_prompt: Union[str, TextPrompt]
        if task_specify_prompt is None:
            task_specify_prompt_template = PromptTemplateGenerator(
            ).get_task_specify_prompt(task_type)

            self.task_specify_prompt = task_specify_prompt_template.format(
                word_limit=word_limit)
        else:
            self.task_specify_prompt = TextPrompt(task_specify_prompt)

        model_config = model_config or ChatGPTConfig(temperature=1.0)

        system_message = BaseMessage(
            role_name="Task Specifier",
            role_type=RoleType.ASSISTANT,
            meta_dict=None,
            content="You can make a task more specific.",
        )

        super().__init__(system_message, model, model_config,
                         output_language=output_language)

    def run(
        self,
        task_prompt: Union[str, TextPrompt],
        meta_dict: Optional[Dict[str, Any]] = None,
    ) -> TextPrompt:
        r"""Specify the given task prompt by providing more details.

        Args:
            task_prompt (Union[str, TextPrompt]): The original task
                prompt.
            meta_dict (Optional[Dict[str, Any]]): A dictionary containing
                additional information to include in the prompt.
                (default: :obj:`None`)

        Returns:
            TextPrompt: The specified task prompt.
        """
        self.reset()
        self.task_specify_prompt = self.task_specify_prompt.format(
            task=task_prompt)

        if meta_dict is not None:
            self.task_specify_prompt = (self.task_specify_prompt.format(
                **meta_dict))

        task_msg = BaseMessage.make_user_message(
            role_name="Task Specifier", content=self.task_specify_prompt)
        specifier_response = self.step(task_msg)
        if (specifier_response.msgs is None
                or len(specifier_response.msgs) == 0):
            raise RuntimeError("Task specification failed.")
        specified_task_msg = specifier_response.msgs[0]

        if specifier_response.terminated:
            raise RuntimeError("Task specification failed.")

        return TextPrompt(specified_task_msg.content)


class TaskPlannerAgent(ChatAgent):
    r"""An agent that helps divide a task into subtasks based on the input
    task prompt.

    Attributes:
        task_planner_prompt (TextPrompt): A prompt for the agent to divide
            the task into subtasks.

    Args:
        model (ModelType): The type of model to use for the agent.
            (default: :obj:`ModelType.GPT_3_5_TURBO`)
        model_config (Any): The configuration for the model.
            (default: :obj:`None`)
        output_language (str, optional): The language to be output by the
        agent. (default: :obj:`None`)
    """

    def __init__(
        self,
        model: Optional[ModelType] = None,
        model_config: Optional[Any] = None,
        output_language: Optional[str] = None,
    ) -> None:

        self.task_planner_prompt = TextPrompt(
            "Divide this task into subtasks: {task}. Be concise.")
        system_message = BaseMessage(
            role_name="Task Planner",
            role_type=RoleType.ASSISTANT,
            meta_dict=None,
            content="You are a helpful task planner.",
        )

        super().__init__(system_message, model, model_config,
                         output_language=output_language)

    def run(
        self,
        task_prompt: Union[str, TextPrompt],
    ) -> TextPrompt:
        r"""Generate subtasks based on the input task prompt.

        Args:
            task_prompt (Union[str, TextPrompt]): The prompt for the task to
                be divided into subtasks.

        Returns:
            TextPrompt: A prompt for the subtasks generated by the agent.
        """
        # TODO: Maybe include roles information.
        self.reset()
        self.task_planner_prompt = self.task_planner_prompt.format(
            task=task_prompt)

        task_msg = BaseMessage.make_user_message(
            role_name="Task Planner", content=self.task_planner_prompt)

        task_response = self.step(task_msg)

        if task_response.msgs is None:
            raise RuntimeError("Got None Subtasks messages.")
        if task_response.terminated:
            raise RuntimeError("Task planning failed.")

        sub_tasks_msg = task_response.msgs[0]
        return TextPrompt(sub_tasks_msg.content)


class TaskCreationAgent(ChatAgent):
    r"""An agent that helps create new tasks based on the objective
    and last completed task. Compared to TaskPlannerAgent, it's still
    a task planner, but it has more context information like last task
    and incompleted task list.

    Attributes:
        task_planner_prompt (TextPrompt): A prompt for the agent to create
            new tasks.

    Args:
        model (ModelType): The type of model to use for the agent.
            (default: :obj:`ModelType.GPT_3_5_TURBO`)
        model_config (Any): The configuration for the model.
            (default: :obj:`None`)
        output_language (str, optional): The language to be output by the
        agent. (default: :obj:`None`)
        objective: The objective for the AI to perform the task.
    """

    def __init__(
        self,
        model: Optional[ModelType] = None,
        model_config: Optional[Any] = None,
        output_language: Optional[str] = None,
        objective: Optional[str] = None,
    ) -> None:

        self.task_creator_prompt = TextPrompt(
            "Create new tasks with the following objective: {objective}.\n\
The last completed task has the result: \n{task_result}.\n\
This result was based on this task: {task}.\n\
Based on the result, return a list of tasks to \
be completed in order to meet the objective. \
Return one task per line in your response. \
The result must be a numbered list in the format:\n\n\
#. First task\n\
#. Second task\n\n\
The number of each entry must be followed by a period.\
Be concise. {unsolved_tasks}\n")

        system_message = BaseMessage(
            role_name="Task Planner",
            role_type=RoleType.ASSISTANT,
            meta_dict=None,
            content="You are a helpful task planner.",
        )

        super().__init__(system_message, model, model_config,
                         output_language=output_language)

        if (objective):
            self.objective = objective
            self.task_creator_prompt = self.task_creator_prompt.format(
                objective=self.objective)

    def run(
        self,
        previous_task: Union[str, TextPrompt],
        task_result: Union[str, TextPrompt],
        task_list: Optional[List[str]] = None,
    ) -> List[dict]:
        r"""Generate subtasks based on the previous task results and
        incomplete task list.

        Args:
            previous_task (Union[str, TextPrompt]): The last completed task to
                be used to create future plans.
            task_result (Union[str, TextPrompt]): The result of last completed
                task to be used to create future plans.
            task_list (List[str], optional): The incompleted task list
                which should not overlap with new created tasks.
        Returns:
            List[dict]: The new task list generated by the AI.
        """
        self.reset()
        self.task_creator_prompt = self.task_creator_prompt.format(
            task=previous_task, task_result=task_result)
        if (task_list):
            unsolved = f"These are unsolved tasks: {task_list}.\n\
                These new tasks must not overlap with incomplete tasks."

            self.task_creator_prompt = self.task_creator_prompt.format(
                unsolved_tasks=unsolved)
        else:
            self.task_creator_prompt = self.task_creator_prompt.format(
                unsolved_tasks="No incomplete tasks.")

        task_msg = BaseMessage.make_user_message(
            role_name="Task Planner", content=self.task_creator_prompt)

        task_response = self.step(task_msg)

        if task_response.msgs is None:
            raise RuntimeError("Got None Subtasks messages.")
        if task_response.terminated:
            raise RuntimeError("Task planning failed.")

        sub_tasks_msg = task_response.msgs[0]
        new_tasks = sub_tasks_msg.content.strip().split('\n')
        new_tasks_list = []
        for task_string in new_tasks:
            task_parts = task_string.strip().split(".", 1)
            if len(task_parts) == 2:
                # this may cause error as LLM may generated # instead of number
                # task_id = ''.join(s for s in task_parts[0] if s.isnumeric())
                task_name = re.sub(r'[^\w\s_]+', '', task_parts[1]).strip()
                if task_name.strip():  # and task_id.isnumeric():
                    new_tasks_list.append(task_name)
        out = [{"task_name": task_name} for task_name in new_tasks_list]
        return out


class TaskPrioritizeAgent(ChatAgent):
    r"""An agent that helps reprioritize the task list and
    returns numbered prioritized list.

    Attributes:
        task_planner_prompt (TextPrompt): A prompt for the agent to
        prioritize tasks.

    Args:
        model (ModelType): The type of model to use for the agent.
            (default: :obj:`ModelType.GPT_3_5_TURBO`)
        model_config (Any): The configuration for the model.
            (default: :obj:`None`)
        output_language (str, optional): The language to be output by the
            agent. (default: :obj:`None`)
        objective: The objective for the AI to perform the task.
    """

    def __init__(
        self,
        model: Optional[ModelType] = None,
        model_config: Optional[Any] = None,
        output_language: Optional[str] = None,
        objective: Optional[str] = None,
    ) -> None:

        self.task_prioritizer_prompt = TextPrompt(
            "Prioritize the following tasks : {task_names}.\n\
Consider the ultimate objective of you: {objective}.\n\
Tasks should be sorted from highest to lowest priority, \
where higher-priority tasks are those \
that act as pre-requisites or are more essential for meeting the objective.\n\
Return one task per line in your response. \
Do not remove any tasks. \
The result must be a numbered list in the format:\n\n\
#. First task\n\
#. Second task\n\n\
The entries must be consecutively numbered, starting with 1.\n\
The number of each entry must be followed by a period.\
Be concise.\n")

        system_message = BaseMessage(
            role_name="Task Prioritizer",
            role_type=RoleType.ASSISTANT,
            meta_dict=None,
            content="You are a helpful task prioritizer.",
        )

        super().__init__(system_message, model, model_config,
                         output_language=output_language)

        if (objective):
            self.objective = objective
            self.task_prioritizer_prompt = self.task_prioritizer_prompt.format(
                objective=self.objective)

    def run(
        self,
        task_names: List[str],
    ) -> List[dict]:
        r"""Prioritize the task list given the agent objective.

        Args:
            task_names (List[str]): The unprioritized task list of agent.
        Returns:
            List[dict]: The new prioritized task list generated by the AI.
        """
        self.reset()
        self.task_prioritizer_prompt = self.task_prioritizer_prompt.format(
            task_names=task_names)

        task_msg = BaseMessage.make_user_message(
            role_name="Task Prioritizer", content=self.task_prioritizer_prompt)

        task_response = self.step(task_msg)

        if task_response.msgs is None:
            raise RuntimeError("Got None Subtasks messages.")
        if task_response.terminated:
            raise RuntimeError("Task Prioritizing failed.")

        sub_tasks_msg = task_response.msgs[0]
        new_tasks = sub_tasks_msg.content.strip().split('\n')
        new_tasks_list = []
        for task_string in new_tasks:
            task_parts = task_string.strip().split(".", 1)
            if len(task_parts) == 2:
                task_name = re.sub(r'[^\w\s_]+', '', task_parts[1]).strip()
                if task_name.strip():
                    new_tasks_list.append({"task_name": task_name})

        return new_tasks_list
