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
from collections import deque
from typing import Any, Dict, List, Optional, Tuple, Union

from tenacity import retry, stop_after_attempt, wait_exponential

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.prompts import TextPrompt
from camel.typing import ModelType, RoleType


class RoleAssignmentAgent(ChatAgent):
    r"""An agent that generates role names based on the task prompt.
    Attributes:
        role_descriptions_dict (Dict[str, str]): A dictionary mapping role
            names to their descriptions.
        subtasks (List[str]): The subtasks to complete the whole task.
        role_assignment_prompt (TextPrompt): A prompt for the agent to generate
        role names.

    Args:
        model (ModelType, optional): The type of model to use for the agent.
            (default: :obj:`ModelType.GPT_3_5_TURBO`)
        model_config (Any, optional): The configuration for the model.
            (default: :obj:`None`)
    """

    def __init__(
        self,
        model: ModelType = ModelType.GPT_3_5_TURBO,
        model_config: Optional[Any] = None,
    ) -> None:
        self.role_descriptions_dict = {}
        self.subtasks = []

        system_message = BaseMessage(
            role_name="Role Assigner",
            role_type=RoleType.ASSISTANT,
            meta_dict=None,
            content="You assign roles based on tasks.",
        )
        super().__init__(system_message, model, model_config)

    @retry(wait=wait_exponential(min=5, max=60), stop=stop_after_attempt(5))
    def run_role_with_description(
        self,
        task_prompt: Union[str, TextPrompt],
        num_roles: int = 2,
    ) -> Dict[str, str]:
        r"""Generate role names based on the input task prompt.

        Args:
            task_prompt (Union[str, TextPrompt]): The prompt
                for the task based on which the roles are to be generated.
            num_roles (int, optional): The number of roles to generate.
                (default: :obj:`2`)

        Returns:
            Dict[str, str]: A dictionary mapping role names to their
                descriptions.
        """
        self.reset()

        expert_prompt = "===== ANSWER PROMPT =====\n" + "\n".join(
            f"Domain expert {i + 1}: <BLANK>\n"
            f"Associated competencies, characteristics, duties "
            f"and workflows: <BLANK>. End." for i in range(num_roles or 0))
        role_assignment_generation_prompt = TextPrompt(
            "You are a role assignment agent, and you're in charge of " +
            "recruiting {num_roles} experts for the following task." +
            "\n==== TASK =====\n {task}\n\n" +
            "Identify the domain experts you'd recruit and detail their " +
            "associated competencies, characteristics, duties and workflows " +
            "to complete the task.\n " +
            "Your answer MUST adhere to the format of ANSWER PROMPT, and " +
            "ONLY answer the BLANKs.\n" + expert_prompt)
        role_assignment_generation = role_assignment_generation_prompt.format(
            num_roles=num_roles, task=task_prompt)

        role_assignment_generation_msg = BaseMessage.make_user_message(
            role_name="Role Assigner", content=role_assignment_generation)

        response = super().step(input_message=role_assignment_generation_msg)

        msg = response.msg  # type: BaseMessage
        terminated = response.terminated

        # Distribute the output completions into role names and descriptions
        role_names = [
            desc.replace("<|", "").replace("|>", "") for desc in re.findall(
                r"Domain expert \d: (.+?)\nAssociated competencies,",
                msg.content,
                re.DOTALL,
            )
        ]
        role_descriptions = [
            desc.replace("<|", "").replace("|>", "") for desc in re.findall(
                r"Associated competencies, characteristics, "
                r"duties and workflows: (.+?) End.", msg.content, re.DOTALL)
        ]

        if len(role_names) != num_roles or len(role_descriptions) != num_roles:
            raise RuntimeError(
                "Got None or insufficient information of roles.")
        if terminated:
            raise RuntimeError("Role assignment failed.")

        role_descriptions_dict = {
            role_name: description
            for role_name, description in zip(role_names, role_descriptions)
        }

        return role_descriptions_dict

    def run_task_assignment():
        # TODO: Implement task assignment
        print("Not implemented yet.")

    @retry(wait=wait_exponential(min=5, max=60), stop=stop_after_attempt(5))
    def split_tasks(
        self,
        task_prompt: Union[str, TextPrompt],
        role_descriptions_dict: Dict[str, str],
        num_subtasks: Optional[int] = None,
        role_descriptions_dict: Optional[Dict[str, str]] = None,
    ) -> List[str]:
        r"""Split the task into subtasks based on the input task prompt.

        Args:
            task_prompt (Union[str, TextPrompt]): The prompt for the task
                based on which the roles are to be generated.
            role_descriptions_dict (Dict[str, str]): The role descriptions of
                each role.
            num_subtasks (Optional[int], optional): The number of subtasks to
                generate. (default: :obj:`None`)
            role_descriptions_dict (Optional[Dict[str, str]], optional): The
                role descriptions of each role. (default: :obj:`None`)

        Returns:
            List[str]: The subtasks to complete the whole task.
        """
        role_descriptions_dict = (role_descriptions_dict
                                  or self.role_descriptions_dict)
        role_names = list(role_descriptions_dict.keys())

        task_prompt = TextPrompt("===== TASK =====\n" + task_prompt + "\n\n")
        role_with_description_prompt = \
            "===== ROLES WITH DESCRIPTION =====\n" + "\n".join(
                f"{role_name}:\n{role_descriptions_dict[role_name]}\n"
                for role_name in role_names) + "\n\n"
        if num_subtasks is None:
            answer_prompt = """===== ANSWER TEMPLATE =====
PART I:
Details of subtask <NUM>:
<BLANK>
Contextual Parameters(only related to CONTEXT TEXT) of subtask <NUM>:
<BLANK>
PART II:
Gantt Chart with complex dependency in MarkDown format:
<BLANK>
PART III:
""" + "\n".join("Incorporate Contextual Parameters into Details of "
                "subtask <NUM>:\n<BLANK>\n"
                "Input of subtask <NUM>:\n<BLANK>/None\n"
                "Task completion standard of subtask <NUM>:\n<BLANK>\n"
                "Dependency of subtask <NUM>: [subtask <i>, subtask <j>, "
                "subtask <k>]/[None] (include square brackets)."
                for _ in range(1)) + "\n\n"
        else:
            answer_prompt = """===== ANSWER TEMPLATE =====
PART I:
Details of subtask <NUM>:
<BLANK>
Contextual Parameters of subtask <NUM>:
<BLANK>
PART II:
Gantt Chart with complex dependency in MarkDown format:
<BLANK>
PART III:
""" + "\n".join(f"Incorporate Contextual Parameters into Details of "
                f"subtask {i + 1}:\n<BLANK>\n"
                f"Input of subtask {i + 1}:\n<BLANK>/None\n"
                f"Task completion standard of subtask {i + 1}:\n<BLANK>\n"
                f"Dependency of subtask {i + 1}: [subtask <i>, subtask "
                f"<j>, subtask <k>]/[None] (include square brackets)"
                for i in range(num_subtasks)) + "\n\n"
        split_task_rules_prompt = """You are a task splitter, and you're in asked to break down the main TASK into {num_subtasks} manageable subtasks suitable for a team comprising {num_roles} domain experts. The experts will contribute to the {num_subtasks} subtasks. Please follow the guidelines below to craft your answer:
    1. Action-Oriented Foundation & Building Blocks: Ensure each subtask is actionable, distinct, tapping into the expertise of the assigned roles. Recognize that not every subtask needs to directly reflect the main TASK's ultimate aim. Some subtasks serve as essential building blocks, paving the way for more central subtasks, but avoid creating subtasks that are self-dependent or overly foundational.
    2. Balanced Granularity with a Bias for Action: While each subtask should be detailed and actionable, it should not be so ambiguous that it requires the input of more than two domain experts. Prioritize tangible actions in subtask such as implementation, creation, testing, or other tangible activities over mere understanding.
    3. Dependencies & Gantt Chart: Identify and account for the dependencies within the subtasks. Ensure that each subtask logically flows from one to the next, or can run concurrently where no subtask is dependent on itself, in a manner that could be efficiently represented on a Gantt chart.
    4. I define the tags of the Input of subtask:
        - Interlinking of Inputs: Ensure that the inputs are not siloed and can be interlinked within privous subtasks if necessary, providing a holistic view of what is required for the subtask.
        - Hierarchy and Prioritization: Identify and clearly state the priority and hierarchy (if applicable) among the inputs, ensuring the most critical elements are addressed promptly.
        - Accessibility and Clarity: Ensure that all provided inputs are accessible, clear, and understandable to the relevant team members.
        - Adjustability: Consider that inputs may need to be adjusted as the project progresses and ensure a mechanism for the same.
    5. I define the Task Completion Standard in order to implement a feature in the software that can identify and mark a task as completed:
        - A task is considered completed when its intended output is produced.
        - If possible, the completion standard should be quantifiable to facilitate automatic detection by the software or tool feature.
        - The completion standard should be applicable to common project management scenarios and adaptable to various types of tasks, such as development, testing, and review tasks.
    6. Refrain from mentioning specific titles or roles within the content of subtasks.
Your answer MUST strictly adhere to the structure of ANSWER TEMPLATE, ONLY fill in the BLANKs, and DO NOT alter or modify any other part of the template.\n\n"""  # noqa: E501
        split_task_prompt = TextPrompt(split_task_rules_prompt +
                                       answer_prompt + task_prompt +
                                       task_context_prompt +
                                       role_with_description_prompt)
        subtasks_generation = split_task_prompt.format(
            num_subtasks=num_subtasks or "SEVERAL/ENOUGH",
            num_roles=len(role_names))

        if num_subtasks is None:
            subtasks_generation = splict_task_prompt.format(
                num_subtasks=num_subtasks, num_roles=len(role_names))
        else:
            subtasks_generation = splict_task_prompt.format(
                num_subtasks=num_subtasks, num_roles=len(role_names))
        subtasks_generation_msg = BaseMessage.make_user_message(
            role_name="Task Splitter", content=subtasks_generation)

        response = super().step(input_message=subtasks_generation_msg)

        msg = response.msg  # type: BaseMessage
        terminated = response.terminated

        # Distribute the output completions into subtasks
        subtasks = [
            desc.replace("<|", "").replace("|>", "")
            for desc in re.findall(r"Content of subtask \d: (.+?)(?=\n|$)",
                                   msg.content, re.DOTALL)
        ]

        if num_subtasks is not None and len(subtasks) != num_subtasks:
            raise RuntimeError(
                "Got None or insufficient information of subtasks.")
        if terminated:
            raise RuntimeError("Subtask split failed.")

        role_compatibility_scores_dict = {
            role_name: int(score)
            for role_name, score in zip(role_names, role_compatibility_scores)
        }

        return role_compatibility_scores_dict

    @retry(wait=wait_exponential(min=5, max=60), stop=stop_after_attempt(5))
    def get_retrieval_index_from_environment(
        self,
        labels_sets: List[List[str]],
        target_labels: List[str],
    ) -> Tuple[List[int], List[int], List[str], List[List[str]]]:
        r"""Get the retrieval index of the target labels from the environment.
        The semantic retrieval is not used in this function.

        Args:
            labels_set (List[List[str]]): A list of lists of labels in the
                environment.
            target_labels (List[str]): A list of target labels to retrieve.

        Returns:
            Tuple[List[int], List[int], List[str], List[List[str]]]: A tuple
                of the indices of the target labels, the indices of the
                retrieved labels sets, the retrieved target labels, and the
                retrieved labels sets.
        """
        self.reset()

        labels_set_prompt = "===== LABELS SETS =====\n"
        for i, labels_set in enumerate(labels_sets):
            labels_set_prompt += f"[{i}]: "
            for label in labels_set:
                labels_set_prompt += f"{label}, "
            labels_set_prompt += "\n"
        target_labels_prompt = "===== TARGET LABELS =====\n"
        for i, target_label in enumerate(target_labels):
            target_labels_prompt += f"[{i}]: {target_label}\n"

        similarity_criteria_prompt = """You are a retrieval index getter, and you're in asked with getting the retrieval index of the target labels from the environment.
You are given multiple sets defined as TARGET LABELS (a List of strings) and LABELS SETS (a List of Lists of strings). You need to identify the subsets from LABELS SETS (referred to as LABELS SUBSETS) that have labels similar to those in a specific subset from TARGET LABELS (referred to as TARGET SUBSET). Your task is to return the indices from TARGET LABELS as a List of integers and the indices of the similar sets from LABELS SETS as a List of integers.
Your answer MUST strictly adhere to the structure of ANSWER TEMPLATE, ONLY fill in the BLANKs, and DO NOT alter or modify any other part of the template.

{target_labels_prompt}

{labels_set_prompt}

===== CRITERIA FOR DETERMINING SIMILARITY =====
1. Explicit Similarity: Labels that have an exact string match should be counted as similar.
2. Implicit Similarity: Labels that may not match word-for-word but have semantic or contextual similarities should also be considered.
    - For example, "apple" and "fruit" may be considered similar in a context where they are being used to describe food items.
Please ensure that you consider both explicit and implicit similarities while evaluating. The result should be a set of indices pointing to the similar labels and sets."""  # noqa: E501
        answer_prompt = "===== ANSWER TEMPLATE =====\n"
        for lable in target_labels:
            answer_prompt += (
                f"Label \"{lable}\" from TARGET LABELS has " +
                "an explicit or implicit similarity with \"<BLANK/NONE>\" " +
                "(or similar label) in LABELS SETS subsets " +
                "[<m>, <n>/NONE] (include square brackets).\n")
        answer_prompt += ("Indices of the similar labels in TARGET LABELS: " +
                          "[<i>, <j>] (include square brackets) \n" +
                          "Indices of the similar subset in LABELS SETS: " +
                          "[<x>, <y>] (include square brackets)")

        retrieval_index_prompt = TextPrompt(similarity_criteria_prompt +
                                            "\n\n" + answer_prompt)
        retrieval_index_generation = retrieval_index_prompt.format(
            target_labels_prompt=target_labels_prompt,
            labels_set_prompt=labels_set_prompt)

        retrieval_index_msg = BaseMessage.make_user_message(
            role_name="Retrieval Index Getter",
            content=retrieval_index_generation)

        response = self.step(input_message=retrieval_index_msg)

        msg = response.msg

        target_labels_indices = [
            int(idx) for idx in re.findall(
                r"Indices of the similar labels in TARGET LABELS: \[(.+?)\]",
                msg.content, re.DOTALL)[0].split(",")
        ]
        target_retrieved_labels = [
            target_labels[idx] for idx in target_labels_indices
        ]
        labels_sets_indices = [
            int(idx) for idx in re.findall(
                r"Indices of the similar subset in LABELS SETS: \[(.+?)\]",
                msg.content, re.DOTALL)[0].split(",")
        ]
        labels_retrieved_sets = [
            labels_sets[idx] for idx in labels_sets_indices
        ]

        return target_labels_indices, labels_sets_indices, \
            target_retrieved_labels, labels_retrieved_sets
