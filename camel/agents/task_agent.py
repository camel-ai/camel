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
from typing import Any, Dict, List, Optional, Tuple, Union

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
        model_config: Any = None,
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


class RoleAssignmentAgent(ChatAgent):
    r"""
    An agent that generates role names based on the task prompt.
    Attributes:
        role_assignment_prompt (TextPrompt): A prompt for the agent to generate
        role names.
    args:
        model (ModelType): The tupe of model to use for the agent.
            (default: :obj: 'ModelType.TEXT_DAVINCI_003')
        model_config (Any): The configuration for the model.
            (default: :obj: 'None')
    """

    def __init__(
        self,
        model: ModelType = ModelType.TEXT_DAVINCI_003,
        model_config: Optional[Any] = None,
    ) -> None:
        self.role_assignment_prompt = TextPrompt(
            'Given this task, "{task}", generate two role names, ' +
            'one for the AI user and one for the AI assistant.')

        system_message = BaseMessage(
            role_name="Role Assigner",
            role_type=RoleType.ASSISTANT,
            meta_dict=None,
            content="You assign roles based on tasks.",
        )
        super().__init__(system_message, model, model_config)

    def run_role_with_description(
        self,
        num_roles: Optional[int] = 2,
        task_prompt: Union[str, TextPrompt] = None,
    ) -> Tuple[List[str], Dict[str, str], bool, Dict[str, Any]]:
        r""" "
        Generate role names based on the input task prompt.

        Args:
            num_roles (int): The number of roles to generate.
                (default: :obj:`2`)
            task_prompt (Union[str, TextPrompt]): The prompt
                for the task based on which the roles are to be generated.

        Returns:
            Tuple[List[str], Dict[str, str], bool, Dict[str, Any]]: A tuple
        """
        self.reset()

        expert_prompt = "\n".join(
            f"Domain expert {i + 1}: <|blank|>\n"
            f"Associated competencies, professional characteristics, duties "
            f"and workflows: <|blank|>. End.\n" for i in range(num_roles))
        role_assignment_generation_prompt = TextPrompt(
            "You are the boss, you need to recruit experts in {num_roles} " +
            "different fields to solve the task.\n" +
            "Please tell me which domain experts should be recruited, " +
            "and what competencies, professional characteristics, duties " +
            "and workflows to complete the task.\n" +
            "ONLY return the content in BLANK.\n\n" + "===== TASK =====\n" +
            "{task}\n\n" + "===== PROMPT =====\n" + expert_prompt)
        role_assignment_generation = role_assignment_generation_prompt.format(
            num_roles=num_roles, task=task_prompt)

        role_assignment_generation_msg = BaseMessage.make_user_message(
            role_name="Role Assigner", content=role_assignment_generation)

        ChatAgentResponse = super().step_completion(
            input_prompt_for_completion=role_assignment_generation_msg, )

        output_completion = ChatAgentResponse.msg  # type: BaseMessage
        terminated = ChatAgentResponse.terminated
        info = ChatAgentResponse.info

        # Distribute the output completions into role names and descriptions
        role_names = re.findall(
            r"Domain expert \d: (.+?)\nAssociated competencies,",
            output_completion.content,
            re.DOTALL,
        )
        role_descriptions = re.findall(
            r"Associated competencies, professional characteristics, duties"
            " and workflows: (.+?) End.",
            output_completion.content,
            re.DOTALL,
        )

        if len(role_names) != num_roles or len(role_descriptions) != num_roles:
            raise RuntimeError("Got None or insufficient Role messages. ")
        if terminated:
            raise RuntimeError("Role assignment failed.")

        role_descriptions_dict = {
            role_name: description
            for role_name, description in zip(role_names, role_descriptions)
        }

        return role_names, role_descriptions_dict, terminated, info
