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
from typing import Any, Dict, List, Optional, Union

from tenacity import retry, stop_after_attempt, wait_exponential

from camel.agents import ChatAgent
from camel.agents.insight_agent import InsightAgent
from camel.messages import BaseMessage
from camel.prompts import TextPrompt
from camel.typing import ModelType, RoleType


class RoleAssignmentAgent(ChatAgent):
    r"""An agent that generates role names based on the task prompt.
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
        system_message = BaseMessage(
            role_name="Role Assigner",
            role_type=RoleType.ASSISTANT,
            meta_dict=None,
            content="You assign roles based on tasks.",
        )
        super().__init__(system_message, model, model_config)

    @retry(wait=wait_exponential(min=5, max=60), stop=stop_after_attempt(5))
    def run(
        self,
        task_prompt: Union[str, TextPrompt],
        num_roles: int = 2,
        role_names: Optional[List[str]] = None,
        role_descriptions_instruction: Optional[Union[str, TextPrompt]] = None,
    ) -> Dict[str, str]:
        r"""Generate role names based on the input task prompt.

        Args:
            task_prompt (Union[str, TextPrompt]): The prompt
                for the task based on which the roles are to be generated.
            num_roles (int, optional): The number of roles to generate.
                (default: :obj:`2`)
            role_names (Optional[List[str]], optional): The names of the roles
                to generate. (default: :obj:`None`)
            role_descriptions_instruction (Optional[Union[str, TextPrompt]],
                optional): The instruction for the role descriptions.

        Returns:
            Dict[str, str]: A dictionary mapping role names to their
                descriptions.
        """
        self.reset()

        if num_roles < 1:
            raise ValueError("Number of roles must be greater than 0.")
        if role_names is not None and len(role_names) != num_roles:
            raise RuntimeError(
                "Got None or insufficient information of roles.")

        task_prompt = TextPrompt("===== TASK =====\n" + task_prompt + "\n\n")
        if role_names is None:
            expert_prompt = "===== ANSWER TEMPLATE =====\n" + "\n".join(
                f"Domain expert {i + 1}: <BLANK>\n"
                f"Associated competencies, characteristics, and duties: "
                f"<BLANK>.\nEnd." for i in range(num_roles)) + "\n\n"
        else:
            expert_prompt = "===== ANSWER TEMPLATE =====\n" + "\n".join(
                f"Domain expert {i + 1}: {role_name}\n"
                f"Associated competencies, characteristics, and duties: "
                f"<BLANK>.\nEnd."
                for i, role_name in enumerate(role_names)) + "\n\n"
        if role_descriptions_instruction is None:
            role_descriptions_instruction = ""
        role_assignment_generation_prompt = TextPrompt(
            "You are a role assignment agent, and you're in charge of " +
            "recruiting {num_roles} experts, who may have identical roles " +
            "but different names. Identify the domain experts you'd recruit " +
            "and detail descriptions, like their associated competencies, " +
            "characteristics and duties to complete the task. " +
            "Moreover, " + role_descriptions_instruction + "\n" +
            "Your answer MUST strictly adhere to the structure of ANSWER " +
            "TEMPLATE, ONLY fill in the BLANKs, and DO NOT alter or modify " +
            "any other part of the template.\n\n" + expert_prompt +
            task_prompt)
        role_assignment_generation = role_assignment_generation_prompt.format(
            num_roles=num_roles, task=task_prompt)

        role_assignment_generation_msg = BaseMessage.make_user_message(
            role_name="Role Assigner", content=role_assignment_generation)

        response = self.step(input_message=role_assignment_generation_msg)

        if response.terminated:
            raise RuntimeError("Role compatibility scoring failed.")
        msg = response.msg  # type: BaseMessage

        # Distribute the output completions into role names and descriptions
        role_names = [
            desc.replace("<", "").replace(">", "").strip('\n')
            for desc in re.findall(
                r"Domain expert \d: (.+?)\nAssociated competencies,",
                msg.content,
                re.DOTALL,
            )
        ]
        role_descriptions = [
            desc.replace("<", "").replace(">", "").strip('\n')
            for desc in re.findall(
                r"Associated competencies, characteristics, and duties:"
                r"(?:\n)?(.+?)\nEnd.", msg.content, re.DOTALL)
        ]

        if len(role_names) != num_roles or len(role_descriptions) != num_roles:
            raise RuntimeError(
                "Got None or insufficient information of roles.")

        role_descriptions_dict = {
            role_name: description
            for role_name, description in zip(role_names, role_descriptions)
        }

        return role_descriptions_dict

    def get_task_execution_order(
        self,
        subtasks_with_dependencies_dict: Dict[str, List[str]],
    ) -> List[List[str]]:
        r"""Assign dependencies between subtasks generated from the task
            prompt.

        Args:
            subtasks_with_dependencies_dict (Dict[str, List[str]]): The
                subtasks with their dependencies.

        Returns:
            List[List[str]]: A list of lists of subtasks that can be executed
                concurrently.
        """
        oriented_graph = {}
        for subtask, details in subtasks_with_dependencies_dict.items():
            dependencies = details["dependencies"]
            oriented_graph[subtask] = dependencies

        subtasks_execution_pipelines = \
            self.sort_oriented_graph(oriented_graph)

        return subtasks_execution_pipelines

    def sort_oriented_graph(
            self, oriented_graph: Dict[str, List[str]]) -> List[List[str]]:
        r"""Sort the subtasks in topological order and group them into
            concurrent pipelines.

        Args:
            oriented_graph (Dict[str, List[str]]): The DAG of subtasks and
                their dependencies.

        Returns:
            List[List[str]]: A list of lists of subtasks that can be executed
                concurrently.
        """
        # Compute the in-degree of each node
        in_degree = {u: 0 for u in oriented_graph}
        for u in oriented_graph:
            for v in oriented_graph[u]:
                in_degree[v] += 1

        # Initialize the queue with nodes that have no incoming edges
        queue = deque(filter(lambda i: in_degree[i] == 0, in_degree))
        parallel_subtask_pipelines = []

        while queue:
            # Collect nodes that can be processed concurrently in this round
            concurrent_nodes = list(queue)
            parallel_subtask_pipelines.insert(0, concurrent_nodes)

            # Clear the queue for the next round
            queue.clear()

            # Iterate over the nodes each of which has no incoming edges
            for u in concurrent_nodes:
                for i in oriented_graph[u]:
                    in_degree[i] -= 1
                    if in_degree[i] == 0:
                        queue.append(i)

        # If the graph is not a DAG, there exists a cycle
        if sum(len(sublist) for sublist in parallel_subtask_pipelines) != len(
                oriented_graph):
            return ("There exists a cycle in the graph. "
                    "Can't determine an order.")

        return parallel_subtask_pipelines

    @retry(wait=wait_exponential(min=5, max=60), stop=stop_after_attempt(5))
    def split_tasks(
        self,
        task_prompt: Union[str, TextPrompt],
        role_descriptions_dict: [Dict[str, str]],
        num_subtasks: Optional[int] = None,
        context_text: Optional[str] = None,
    ) -> Dict[str, Dict[str, Union[str, List[str]]]]:
        r"""Split the task into subtasks based on the input task prompt.

        Args:
            task_prompt (Union[str, TextPrompt]): The prompt
                for the task based on which the roles are to be generated.
            role_descriptions_dict ([Dict[str, str]]): The role
                descriptions of each role.
            num_subtasks (Optional[int], optional): The number of subtasks to
                split the task into. (default: :obj:`None`)
            context_text (Optional[str], optional): The context text to
                generate insights from. (default: :obj:`None`)

        Returns:
            Dict[str, Dict[str, Union[str, List[str]]]]: A dictionary mapping
                subtask names to their descriptions and dependencies.
        """
        self.reset()

        role_names = list(role_descriptions_dict.keys())

        # Generate insights from the context text to help split the task
        if context_text is not None:
            insight_agent = InsightAgent(model=self.model,
                                         model_config=self.model_config)
            task_insights_json = insight_agent.run(context_text=context_text)
            task_context_prompt = \
                TextPrompt("===== NovaDive&QuestXplorer FOR CONTEXT OF " +
                           "TASK =====\n")
            task_context_prompt += insight_agent.convert_json_to_str(
                task_insights_json)
        else:
            task_context_prompt = ""

        task_prompt = TextPrompt("===== TASK =====\n" + task_prompt + "\n\n")
        role_with_description_prompt = \
            "===== ROLES WITH DESCRIPTION =====\n" + "\n".join(
                f"{role_name}:\n{role_descriptions_dict[role_name]}\n"
                for role_name in role_names) + "\n\n"
        answer_prompt = \
            "===== ANSWER TEMPLATE =====\nGantt Chart with complex " + \
            "dependency in MarkDown format: <BLANK>\n" + "\n".join(
                f"Explanation for subtask {i + 1}: <BLANK>\n"
                f"Content of subtask {i + 1}: <BLANK>\n"
                f"Dependency of subtask {i + 1}: [subtask <i>, subtask <j>, "
                f"subtask <k>]/[None] (don't forget square brackets)\nEnd."
                for i in range(num_subtasks or 1)) + "\n\n"
        splict_task_prompt = TextPrompt(
            "You are a task splitter, and you're in asked to break down the" +
            " main TASK into {num_subtasks} manageable subtasks suitable " +
            "for a team comprising {num_roles} domain experts. The experts " +
            "will contribute to the {num_subtasks} subtasks. Please follow " +
            "the guidelines below to craft your answer:\n" +
            "  1. Foundation & Building Blocks: Remember that ensure each " +
            "subtask is distinct, actionable, and taps into the expertise " +
            "of the assigned roles. And recognize that not every subtask " +
            "needs to directly reflect the main TASK's ultimate aim. Some " +
            "subtasks serve as essential building blocks, paving the way " +
            "for more central subtasks.\n" +
            "  2. Balanced Granularity: While each subtask should be " +
            "distinct and actionable, it should not be so detailed that it " +
            "requires the input of more than two domain experts. Design " +
            "each subtask to be comprehensive but not overly complex.\n" +
            "  3. Dependencies & Gantt Chart: Identify and account for the " +
            "dependencies within these subtasks. Ensure that each subtask " +
            "logically flows from one to the next, or can run concurrently, " +
            "in a manner that could be efficiently represented on a Gantt " +
            "chart.\n" +
            "  4. The content of each subtask should avoid mentioning any " +
            "title or any role of the experts.\n" +
            "Your answer MUST strictly adhere to the structure of ANSWER " +
            "TEMPLATE, ONLY fill in the BLANKs, and DO NOT alter or modify " +
            "any other part of the template.\n\n" + answer_prompt +
            task_prompt + task_context_prompt + role_with_description_prompt)

        subtasks_generation = splict_task_prompt.format(
            num_subtasks=num_subtasks or "SEVERAL/ENOUGH",
            num_roles=len(role_names))
        subtasks_generation_msg = BaseMessage.make_user_message(
            role_name="Task Splitter", content=subtasks_generation)

        response = self.step(input_message=subtasks_generation_msg)

        if (response.terminated):
            raise RuntimeError("Role compatibility scoring failed.")
        msg = response.msg  # type: BaseMessage

        # Distribute the output completions into subtasks
        subtask_descriptions = [
            desc.replace("<", "").replace(">", "").strip('\n')
            for desc in re.findall(r"Content of subtask \d: (.+?)Dependency",
                                   msg.content, re.DOTALL)
        ]
        subtask_dependencies = [[
            dep.strip() for dep in re.findall(r"\[(.+?)\]", desc)[0].split(",")
        ] for desc in re.findall(r"Dependency of subtask \d: \[.+?\]",
                                 msg.content, re.DOTALL)]

        # Extracting dependencies and creating a dictionary
        dependent_subtasks_list = [[
            f"subtask {int(dep.split()[1])}" for dep in deps
            if "subtask" in dep.lower()
        ] for deps in subtask_dependencies]
        # Creating a dictionary of subtasks with dependencies
        subtasks_with_dependencies_dict = {
            f"subtask {index+1}": {
                "description": desp,
                "dependencies": deps
            }
            for index, (desp, deps) in enumerate(
                zip(subtask_descriptions, dependent_subtasks_list))
        }

        if (num_subtasks is not None
                and (len(subtask_descriptions) != num_subtasks
                     or len(dependent_subtasks_list) != num_subtasks)):
            raise RuntimeError(
                f"Got None or insufficient information of subtasks. "
                f"Length of generated subtasks: {len(subtask_descriptions)}, "
                f"length of required subtasks: {num_subtasks}")

        return subtasks_with_dependencies_dict

    @retry(wait=wait_exponential(min=5, max=60), stop=stop_after_attempt(5))
    def evaluate_role_compatibility(
        self,
        subtask_prompt: Union[str, TextPrompt],
        role_descriptions_dict: [Dict[str, str]],
    ) -> Dict[str, int]:
        r"""Evaluate the compatibility scores of each role in relation to the
            specified task.

            Args:
                subtask_prompt (Union[str, TextPrompt]): The prompt for the
                    subtask based on which the roles are to be evaluated.
                role_descriptions_dict ([Dict[str, str]]): The role
                    descriptions of each role.

            Returns:
                Dict[str, int]: A dictionary mapping role names to their
                    compatibility scores.
        """
        self.reset()

        role_names = list(role_descriptions_dict.keys())

        compatibility_instruction_prompt = TextPrompt(
            "===== INSTRUCTIONS OF COMPATIBILITY EVALUATION =====\n" +
            "To evaluate the compatibility scores, consider these guiding " +
            "principles:\n" +
            "1. Assess the alignment between the primary responsibilities " +
            "and expertise of the role with the task requirements. Factor " +
            "in the likelihood of the role successfully executing the task " +
            "based on its competencies.\n" +
            "2. Analyze the congruence between keywords or key concepts in " +
            "the task description and those present in the role " +
            "description. This will gauge the direct relevance of the role " +
            "to the task.\n" +
            "3. Drawing from a comprehensive knowledge base, ascertain the " +
            "potential value each role brings to the table when it comes to " +
            "accomplishing the specific task. This evaluation should be " +
            "based on empirical data or established norms in the relevant " +
            "domain.\n\n")
        task_prompt = TextPrompt("===== TASK =====\n" + subtask_prompt +
                                 "\n\n")
        role_with_description_prompt = \
            "===== ROLES WITH DESCRIPTION =====\n" + "\n".join(
                f"{role_name}:\n{role_descriptions_dict[role_name]}\n"
                for role_name in role_names) + "\n\n"
        answer_prompt = \
            "===== ANSWER TEMPLATE =====\n" + "\n".join(
                f"Explanation for role {role_name}: <BLANK>\n"
                f"Score of role {role_name}: <BLANK>\n"
                for role_name in role_names) + "\n\n"
        compatibility_scoring_prompt = TextPrompt(
            "You are a compatibility scorer, and you're in asked with " +
            "evaluating/calculating/generating the compatibility of each " +
            "role relative to a specific task (the score is an integer from " +
            "0 to 100). In your team consists of {num_roles} domain experts " +
            "each contributing to the TASK.\n" +
            "Your answer MUST strictly adhere to the structure of ANSWER " +
            "TEMPLATE, ONLY fill in the BLANKs, and DO NOT alter or modify " +
            "any other part of the template.\n\n" + answer_prompt +
            compatibility_instruction_prompt + task_prompt +
            role_with_description_prompt)

        compatibility_scoring = compatibility_scoring_prompt.format(
            num_roles=len(role_names))

        compatibility_scoring_msg = BaseMessage.make_user_message(
            role_name="Compatibility Scorer", content=compatibility_scoring)

        response = self.step(input_message=compatibility_scoring_msg)

        if response.terminated:
            raise RuntimeError("Role compatibility scoring failed.")
        msg = response.msg  # type: BaseMessage

        # Distribute the output completions into scores
        role_compatibility_scores = [
            desc.replace("<", "").replace(">", "").strip('\n')
            for desc in re.findall(r"Score of role .+?: (.+?)(?=\n|$)",
                                   msg.content, re.DOTALL)
        ]

        if len(role_compatibility_scores) != len(role_names):
            raise RuntimeError("Got None or insufficient information of " +
                               "role compatibility scores.")

        role_compatibility_scores_dict = {
            role_name: int(score)
            for role_name, score in zip(role_names, role_compatibility_scores)
        }

        return role_compatibility_scores_dict
