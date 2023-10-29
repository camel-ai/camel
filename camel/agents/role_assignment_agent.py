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

import matplotlib.pyplot as plt
import networkx as nx
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
    ) -> Dict[str, Dict[str, List[str]]]:
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
            Dict[str, Dict[str, List[str]]]: A dictionary mapping role names
                to their descriptions and dependencies.
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
            raise RuntimeError("Role compatibility scoring failed.\n" +
                               f"Error:\n{response.info}")
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
            desc.lstrip('\n').replace("<", "").replace(">", "").strip('\n')
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
        for subtask_idx, details in subtasks_with_dependencies_dict.items():
            deps = details["dependencies"]
            oriented_graph[subtask_idx] = deps

        subtasks_execution_pipelines = \
            self.sort_oriented_graph(oriented_graph)

        return subtasks_execution_pipelines

    def draw_subtasks_graph(self, oriented_graph: Dict[str, List[str]],
                            graph_file_path: str = None) -> str:
        r"""Draw the task dependency graph.

        Args:
            oriented_graph (Dict[str, List[str]]): The DAG of subtasks and
                their dependencies.
            graph_file_path (str, optional): The filepath to save the graph.
                (default: :obj:`None`)

        Returns:
            str: The filepath of the saved graph.
        """

        # Initialize the graph
        G = nx.DiGraph()
        for subtask, details in oriented_graph.items():
            for dep in details:
                G.add_edge(dep, subtask)
        pos = nx.spring_layout(G, k=0.5)
        plt.figure(figsize=(10, 6))
        plt.title("Task Dependency Graph")

        # Draw the graph
        nx.draw(G, pos, with_labels=True, node_size=2000, node_color='skyblue',
                alpha=0.5, font_size=15, width=2, edge_color='gray',
                font_weight='bold')

        # Save the figure locally
        if graph_file_path is None:
            graph_file_path = \
                "examples/multi_agent/task_dependency_graph.png"
        plt.savefig(graph_file_path)
        plt.close()

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
            raise RuntimeError("There exists a cycle in the graph. "
                               "Can't determine an order.")

        return parallel_subtask_pipelines

    @retry(wait=wait_exponential(min=5, max=60), stop=stop_after_attempt(5))
    def split_tasks(
        self,
        task_prompt: Union[str, TextPrompt],
        role_descriptions_dict: Dict[str, str],
        num_subtasks: Optional[int] = None,
        context_text: Optional[str] = None,
    ) -> Dict[str, Dict[str, Union[str, List[str]]]]:
        r"""Split the task into subtasks based on the input task prompt.

        Args:
            task_prompt (Union[str, TextPrompt]): The prompt for the task
                based on which the roles are to be generated.
            role_descriptions_dict (Dict[str, str]): The role descriptions of
                each role.
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
                TextPrompt("===== CONTEXT TEXT =====\n" +
                           "The CONTEXT TEXT is related to TASK and " +
                           "Contextual Parameters of subtask. When " +
                           "splitting the task, ensure that each subtask " +
                           "incorporates specific details from the " +
                           "INSIGHTS of CONTEXT TEXT.\n")
            task_context_prompt += insight_agent.convert_json_to_str(
                task_insights_json)
        else:
            task_context_prompt = ""

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

        subtasks_generation_msg = BaseMessage.make_user_message(
            role_name="Task Splitter", content=subtasks_generation)

        response = self.step(input_message=subtasks_generation_msg)

        if (response.terminated):
            raise RuntimeError("Role compatibility scoring failed.\n" +
                               f"Error:\n{response.info}")
        msg = response.msg  # type: BaseMessage

        # Distribute the output completions into subtasks
        subtask_descriptions = [
            desc.replace("<", "").replace(">", "").strip('\n')
            for desc in re.findall(
                r"Incorporate Contextual Parameters into Details "
                r"of subtask \d:\n(.+?)Input of ", msg.content, re.DOTALL)
        ]
        subtask_inputs = [
            ipt.replace("<", "").replace(">", "").strip('\n')
            for ipt in re.findall(
                r"Input of subtask \d:\n(.+?)Task completion standard",
                msg.content, re.DOTALL)
        ]
        subtask_outputs_standard = [
            opt_std.replace("<", "").replace(">", "").strip('\n')
            for opt_std in re.findall(
                r"Task completion standard of subtask \d:\n(.+?)Dependency "
                r"of subtask", msg.content, re.DOTALL)
        ]
        subtask_dependencies = [[
            dep.strip() for dep in re.findall(r"\[(.+?)\]", dep)[0].split(",")
        ] for dep in re.findall(r"Dependency of subtask \d: \[.+?\]",
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
                "dependencies": deps,
                "input": ipt,
                "output_standard": opt_std
            }
            for index, (desp, deps, ipt, opt_std) in enumerate(
                zip(subtask_descriptions, dependent_subtasks_list,
                    subtask_inputs, subtask_outputs_standard))
        }

        if len(subtasks_with_dependencies_dict) == 0:
            raise RuntimeError("The task is not split into subtasks.")
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
            raise RuntimeError("Role compatibility scoring failed." +
                               f"Error:\n{response.info}")
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

        if labels_sets is None or len(labels_sets) == 0:
            raise ValueError("Labels sets must be provided.")
        if target_labels is None or len(target_labels) == 0:
            raise ValueError("Target labels must be provided.")

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
                "an explicit or implicit similarity with \"<BLANK>/NONE\" " +
                "(or similar label) in LABELS SETS subsets " +
                "[<m>, <n>]/NONE (include square brackets).\n")
        answer_prompt += ("Indices of the similar labels in TARGET LABELS: " +
                          "[<i>, <j>]/NONE (include square brackets) \n" +
                          "Indices of the similar subset in LABELS SETS: " +
                          "[<x>, <y>]/NONE (include square brackets)")

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

        match_target_labels = re.findall(
            r"Indices of the similar labels in TARGET LABELS: \[(.+?)\]",
            msg.content, re.DOTALL)
        target_labels_indices = [
            int(idx) for idx in match_target_labels[0].split(",")
        ] if match_target_labels else []

        target_retrieved_labels = \
            [target_labels[idx] for idx in target_labels_indices]

        match_labels_sets = re.findall(
            r"Indices of the similar subset in LABELS SETS: \[(.+?)\]",
            msg.content, re.DOTALL)
        labels_sets_indices = [
            int(idx) for idx in match_labels_sets[0].split(",")
        ] if match_labels_sets else []

        labels_retrieved_sets = \
            [labels_sets[idx] for idx in labels_sets_indices]

        return target_labels_indices, labels_sets_indices, \
            target_retrieved_labels, labels_retrieved_sets

    @retry(wait=wait_exponential(min=5, max=60), stop=stop_after_attempt(5))
    def transform_dialogue_into_text(self, chat_history: str, user: str,
                                     assistant: str,
                                     task_prompt: Optional[str] = None) -> str:
        r"""Synthesize a narrative from the chat history.

        Args:
            chat_history (str): The chat history.
            user (str): The name of the user.
            assistant (str): The name of the assistant.
            task_prompt (Optional[str], optional): The task of the chat
                history. (default: :obj:`None`)

        Returns:
            str: The synthesized narrative.
        """
        self.reset()

        if task_prompt is not None:
            chat_history_prompt = "===== CHAT HISTORY =====\n" + \
                f"[TASK of the conversation]:\n{task_prompt}\n" + \
                f"{chat_history}\n\n"
        else:
            chat_history_prompt = "===== CHAT HISTORY =====\n" + \
                f"{chat_history}\n\n"

        text_synthesis = """You are an insightful conversation analyst. Your MISSION is to transform a CHAT HISTORY into an objective and coherent text. This transformation should focus on a specific TASK outlined at the beginning of the CHAT HISTORY. While the MISSION and the TASK are interconnected, they are distinct in nature.

===== KEY POINTS TO CONSIDER =====
1. Chat History Context:
   - The CHAT HISTORY is segmented into multiple rounds, indicated by “===== [{n}] =====”. Despite this segmentation, the conversation is continuous and cohesive.
   - Two participants are involved, A: [{user}] and B: [{assistant}]. Participant A provides prompts and guidance, while Participant B offers solutions and answers.
2. Analysis and Synthesis Focus:
   - Your primary focus should be on Participant B's solutions and answers. Use Participant A's contributions for context and logical structure.
   - Be mindful of the emotional tone and contextual nuances in the conversation. These should be acknowledged in your synthesis but should not dominate the objective nature of the TASK.
3. Content Filtering:
   - The CHAT HISTORY may contain irrelevant keywords or commands. It is crucial to filter out these elements without compromising the original intent of the conversation.
4. Synthesis Guidelines:
   - Your final text should be an objective and comprehensive synthesis of Participant B's answers, closely aligned with the central TASK.
   - Incorporate relevant emotional and contextual elements where necessary, but maintain an objective and professional tone.
   - Aim for a synthesis that captures the essence and critical points of the CHAT HISTORY, balancing between quality and accuracy rather than strictly adhering to its original length.
5. Instructions for Text Generation:
   - Your answer MUST strictly adhere to the structure of the ANSWER TEMPLATE.
   - ONLY fill in the BLANKs in the template and DO NOT alter or modify any other part of it.
   - NEVER forget the MISSION I've assigned to you and your role, and NEVER let the CHAT HISTORY distract you from your MISSION.


===== ANSWER TEMPLATE =====
TRANSFORMED TEXT:\n<BLANK>


{chat_history_prompt}"""  # noqa: E501
        text_synthesis_prompt = TextPrompt(text_synthesis)

        text_synthesis_generation = text_synthesis_prompt.format(
            user=user, assistant=assistant,
            chat_history_prompt=chat_history_prompt)

        text_synthesis_generation_msg = BaseMessage.make_user_message(
            role_name="Conversation Analyst",
            content=text_synthesis_generation)

        response = self.step(input_message=text_synthesis_generation_msg)

        if response.terminated:
            raise RuntimeError("Generating transformed text failed." +
                               f"Error:\n{response.info}")
        msg = response.msg  # type: BaseMessage

        # Distribute the output completions into narrative synthesis
        transformed_texts = re.findall(r"TRANSFORMED TEXT:\s*(.+)",
                                       msg.content, re.DOTALL)

        if transformed_texts is None or len(transformed_texts) == 0:
            raise RuntimeError("Got None of transformed text.")

        transformed_text = transformed_texts[0].strip('\n')

        return transformed_text
