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
from typing import Any, Dict, List, Optional, Union

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.messages import BaseMessage
from camel.prompts import PromptTemplateGenerator, TextPrompt
from camel.typing import ModelType, RoleType, TaskType
from camel.utils import get_task_list


class TaskSpecifyAgent(ChatAgent):
    r"""An agent that specifies a given task prompt by prompting the user to
    provide more details.

    Attributes:
        DEFAULT_WORD_LIMIT (int): The default word limit for the task prompt.
        task_specify_prompt (TextPrompt): The prompt for specifying the task.

    Args:
        model (ModelType, optional): The type of model to use for the agent.
            (default: :obj:`ModelType.GPT_3_5_TURBO`)
        task_type (TaskType, optional): The type of task for which to generate
            a prompt. (default: :obj:`TaskType.AI_SOCIETY`)
        model_config (Any, optional): The configuration for the model.
            (default: :obj:`None`)
        task_specify_prompt (Union[str, TextPrompt], optional): The prompt for
            specifying the task. (default: :obj:`None`)
        word_limit (int, optional): The word limit for the task prompt.
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
            meta_dict (Dict[str, Any], optional): A dictionary containing
                additional information to include in the prompt.
                (default: :obj:`None`)

        Returns:
            TextPrompt: The specified task prompt.
        """
        self.reset()
        task_specify_prompt = self.task_specify_prompt.format(task=task_prompt)

        if meta_dict is not None:
            task_specify_prompt = task_specify_prompt.format(**meta_dict)

        task_msg = BaseMessage.make_user_message(role_name="Task Specifier",
                                                 content=task_specify_prompt)
        specifier_response = self.step(task_msg)
        if len(specifier_response.msgs) == 0:
            raise RuntimeError("Got no specification message.")
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
        model (ModelType, optional: The type of model to use for the agent.
            (default: :obj:`ModelType.GPT_3_5_TURBO`)
        model_config (Any, optional): The configuration for the model.
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
        task_planner_prompt = self.task_planner_prompt.format(task=task_prompt)

        task_msg = BaseMessage.make_user_message(role_name="Task Planner",
                                                 content=task_planner_prompt)

        task_response = self.step(task_msg)

        if len(task_response.msgs) == 0:
            raise RuntimeError("Got no task planning message.")
        if task_response.terminated:
            raise RuntimeError("Task planning failed.")

        sub_tasks_msg = task_response.msgs[0]
        return TextPrompt(sub_tasks_msg.content)


class TaskCreationAgent(ChatAgent):
    r"""An agent that helps create new tasks based on the objective
    and last completed task. Compared to :obj:`TaskPlannerAgent`,
    it's still a task planner, but it has more context information
    like last task and incomplete task list. Modified from
    `BabyAGI <https://github.com/yoheinakajima/babyagi>`_.

    Attributes:
        task_creation_prompt (TextPrompt): A prompt for the agent to create
            new tasks.

    Args:
        objective (Union[str, TextPrompt]): The objective of the Agent to
            perform the task.
        model (ModelType, optional): The type of model to use for the agent.
            (default: :obj:`ModelType.GPT_3_5_TURBO`)
        model_config (Any, optional): The configuration for the model.
            (default: :obj:`None`)
        output_language (str, optional): The language to be output by the
            agent. (default: :obj:`None`)
    """

    def __init__(
        self,
        objective: Union[str, TextPrompt],
        model: Optional[ModelType] = None,
        model_config: Optional[Any] = None,
        output_language: Optional[str] = None,
    ) -> None:

        task_creation_prompt = TextPrompt(
            """Create new tasks with the following objective: {objective}.
The last completed task has the result:
{task_result}.
This result was based on this task: {task}.
Based on the result, return a list of tasks to be completed in order to meet \
the objective.

{unsolved_tasks}

Return one task per line in your response.
The result must be a numbered list in the format:

1. First task
2. Second task

The number of each entry must be followed by a period. Be concise.""")

        self.task_creation_prompt = task_creation_prompt.format(
            objective=objective)
        self.objective = objective

        system_message = BaseMessage(
            role_name="Task Creator",
            role_type=RoleType.ASSISTANT,
            meta_dict=None,
            content="You are a helpful task creator.",
        )

        super().__init__(system_message, model, model_config,
                         output_language=output_language)

    def run(
        self,
        previous_task: Union[str, TextPrompt],
        task_result: Union[str, TextPrompt],
        task_list: Optional[List[str]] = None,
    ) -> List[str]:
        r"""Generate subtasks based on the previous task results and
        incomplete task list.

        Args:
            previous_task (Union[str, TextPrompt]): The last completed task to
                be used to create future plans.
            task_result (Union[str, TextPrompt]): The result of last completed
                task to be used to create future plans.
            task_list (List[str], optional): The incomplete task list
                which should not overlap with new created tasks.
                (default: :obj:`None`)
        Returns:
            List[str]: The new task list generated by the Agent.
        """
        self.reset()
        task_creation_prompt = self.task_creation_prompt.format(
            task=previous_task, task_result=task_result)
        if task_list is not None:
            unsolved = (
                f"These are unsolved tasks: {task_list}.\n"
                "These new tasks must not overlap with incomplete tasks.")

            task_creation_prompt = task_creation_prompt.format(
                unsolved_tasks=unsolved)
        else:
            task_creation_prompt = task_creation_prompt.format(
                unsolved_tasks="")

        task_msg = BaseMessage.make_user_message(role_name="Task Creator",
                                                 content=task_creation_prompt)

        task_response = self.step(task_msg)

        if len(task_response.msgs) == 0:
            raise RuntimeError("Got no task creation message.")
        if task_response.terminated:
            raise RuntimeError("Task creation failed.")

        sub_tasks_msg = task_response.msgs[0]
        return get_task_list(sub_tasks_msg.content)


class TaskPrioritizationAgent(ChatAgent):
    r"""An agent that helps re-prioritize the task list and
    returns numbered prioritized list. Modified from
    `BabyAGI <https://github.com/yoheinakajima/babyagi>`_.

    Attributes:
        task_prioritization_prompt (TextPrompt): A prompt for the agent to
            prioritize tasks.

    Args:
        objective (Union[str, TextPrompt]): The objective of the Agent to
            perform the task.
        model (ModelType, optional): The type of model to use for the agent.
            (default: :obj:`ModelType.GPT_3_5_TURBO`)
        model_config (Any, optional): The configuration for the model.
            (default: :obj:`None`)
        output_language (str, optional): The language to be output by the
            agent. (default: :obj:`None`)
    """

    def __init__(
        self,
        objective: Union[str, TextPrompt],
        model: Optional[ModelType] = None,
        model_config: Optional[Any] = None,
        output_language: Optional[str] = None,
    ) -> None:

        task_prioritization_prompt = TextPrompt(
            """Prioritize the following tasks : {task_list}.
Consider the ultimate objective of you: {objective}.
Tasks should be sorted from highest to lowest priority,
where higher-priority tasks are those that act as pre-requisites \
or are more essential for meeting the objective.
Return one task per line in your response. Do not remove any tasks.
The result must be a numbered list in the format:

1. First task
2. Second task

The entries must be consecutively numbered, starting with 1.
The number of each entry must be followed by a period.
Be concise.""")

        self.task_prioritization_prompt = task_prioritization_prompt.format(
            objective=objective)
        self.objective = objective

        system_message = BaseMessage(
            role_name="Task Prioritizer",
            role_type=RoleType.ASSISTANT,
            meta_dict=None,
            content="You are a helpful task prioritizer.",
        )

        super().__init__(system_message, model, model_config,
                         output_language=output_language)

    def run(
        self,
        task_list: List[str],
    ) -> List[str]:
        r"""Prioritize the task list given the agent objective.

        Args:
            task_list (List[str]): The un-prioritized task list of agent.
        Returns:
            List[str]: The new prioritized task list generated by the Agent.
        """
        self.reset()
        task_prioritization_prompt = self.task_prioritization_prompt.format(
            task_list=task_list)

        task_msg = BaseMessage.make_user_message(
            role_name="Task Prioritizer", content=task_prioritization_prompt)

        task_response = self.step(task_msg)

        if len(task_response.msgs) == 0:
            raise RuntimeError("Got no task prioritization message.")
        if task_response.terminated:
            raise RuntimeError("Task prioritization failed.")

        sub_tasks_msg = task_response.msgs[0]
        return get_task_list(sub_tasks_msg.content)
