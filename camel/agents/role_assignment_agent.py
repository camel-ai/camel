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

from camel.agents import ChatAgent
from camel.agents.insight_agent import InsightAgent
from camel.configs import ChatGPTConfig
from camel.functions import OpenAIFunction
from camel.messages import BaseMessage
from camel.prompts import TextPrompt
from camel.types import ModelType, RoleType


class RoleAssignmentAgent(ChatAgent):
    r"""An agent that generates role names based on the task prompt.
    Args:
        model_type (ModelType, optional): The type of model to use for the
            agent. (default: :obj:`ModelType.GPT_3_5_TURBO`)
        model_config (Any, optional): The configuration for the model.
            (default: :obj:`None`)
    """

    def __init__(
        self,
        model_type: ModelType = ModelType.GPT_3_5_TURBO,
        model_config: Optional[Any] = None,
    ) -> None:
        system_message = BaseMessage(
            role_name="AI Assistant",
            role_type=RoleType.ASSISTANT,
            meta_dict=None,
            content="You are an AI.",
        )
        super().__init__(system_message, model_type, model_config)
        self.model_config = model_config or ChatGPTConfig()

    def run_role_with_description(
        self,
        task_prompt: Union[str, TextPrompt],
        num_roles: int = 2,
        role_names: Optional[List[str]] = None,
        role_descriptions_instruction: Optional[Union[str, TextPrompt]] = None,
        function_list: list[OpenAIFunction] = None,
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
                (default: :obj:`None`)
            function_list (list[OpenAIFunction], optional): The list of
                OpenAIFunctions to use. (default: :obj:`None`)

        Returns:
            Dict[str, Dict[str, List[str]]]: A dictionary mapping role names
                to their descriptions and dependencies.
        """
        self.reset()

        if num_roles is None:
            raise ValueError("Number of roles must be provided.")
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
        else:
            role_descriptions_instruction = "Moreover, " + \
                role_descriptions_instruction
        if function_list is not None and len(function_list) > 0:
            function_docstring = """===== FUNCTION LIST (CONTEXT) =====
You have been provided with a list of tools for work. Each tool description explains the purpose and usage of a specific tool for work.
The tool descriptions are the context information of the potential competencies of the domain experts (for example, some experts may have the ability of Google searching).
"""  # noqa: E501
            for i, function in enumerate(function_list):
                description_lines = function.description.split('\n')
                indented_description = '\n'.join('\t' + line
                                                 for line in description_lines)
                function_docstring += (f"{i + 1}. Ability or tool of "
                                       f"{function.name}:\n"
                                       f"{indented_description}\n\n")
        else:
            function_docstring = ""
        role_assignment_generation_prompt = TextPrompt(
            "You are a role assignment agent, and you're in charge of "
            "recruiting {num_roles} experts, who are conceptualized as "
            "the super advanced, abstract or specific facets of the Large "
            "Language Model (LLM), but they act or work as real roles. "
            "Identify these domain experts you'd recruit and detail "
            "descriptions, like their competencies, characteristics, "
            "and duties to complete the TASK. "
            "Remember, your role is to create the profiles of these "
            "experts, not to complete the TASK directly.\n" +
            role_descriptions_instruction + "\n"
            "Your answer MUST strictly adhere to the structure of ANSWER "
            "TEMPLATE, ONLY fill in the BLANKs, and DO NOT alter or modify "
            "any other part of the template.\n\n" + function_docstring +
            expert_prompt + task_prompt)
        role_assignment_generation = role_assignment_generation_prompt.format(
            num_roles=num_roles, task=task_prompt)

        role_assignment_generation_msg = BaseMessage.make_user_message(
            role_name="Role Assigner", content=role_assignment_generation)

        response = self.step(input_message=role_assignment_generation_msg)

        if response.terminated:
            raise RuntimeError("Role compatibility scoring failed.\n" +
                               f"Error:\n{response.info}")
        msg = response.msg  # type: BaseMessage

        if "I'm sorry" in msg.content.strip():
            raise RuntimeError("May violate the guidelines of the large "
                               "language model.\n"
                               f"Response of the LLM:\n{msg.content}")

        # Distribute the output completions into role names and descriptions
        role_names = [
            desc.replace("<", "").replace(">", "").strip()
            for desc in re.findall(
                r"Domain expert \d:[\s\n](.+?)\nAssociated competencies,",
                msg.content,
                re.DOTALL,
            )
        ]
        role_descriptions = [
            desc.lstrip('\n').replace("<", "").replace(">", "").strip()
            for desc in re.findall(
                r"Associated competencies, characteristics, and duties:"
                r"(?:\n)?(.+?)\nEnd.", msg.content, re.DOTALL)
        ]

        if len(role_names) != num_roles or len(role_descriptions) != num_roles:
            raise RuntimeError(
                "Got None or insufficient information of roles.\n"
                f"Response of the LLM:\n{msg.content}\n"
                f"Role names:{str(role_names)}\n"
                f"Role descriptions:\n{str(role_descriptions)}")
        role_descriptions_dict = {
            role_name: description
            for role_name, description in zip(role_names, role_descriptions)
        }

        return role_descriptions_dict

    def split_tasks(
        self,
        task_prompt: Union[str, TextPrompt],
        role_descriptions_dict: Dict[str, str],
        num_subtasks: Optional[int] = None,
        context_text: Optional[str] = None,
    ) -> Dict[str, Dict[str, Union[str, List[str]]]]:
        r"""Decompose the task into subtasks based on the input task prompt.

        Args:
            task_prompt (Union[str, TextPrompt]): The prompt for the task
                based on which the roles are to be generated.
            role_descriptions_dict (Dict[str, str]): The role descriptions of
                each role.
            num_subtasks (Optional[int], optional): The number of subtasks to
                decompose the task into. (default: :obj:`None`)
            context_text (Optional[str], optional): The context text to
                generate insights from. (default: :obj:`None`)

        Returns:
            Dict[str, Dict[str, Union[str, List[str]]]]: A dictionary mapping
                subtask names to their descriptions and dependencies.
        """
        self.reset()

        role_names = list(role_descriptions_dict.keys())

        split_task_rules_prompt = """You are a task decomposer, and you're in asked to break down the main TASK into {num_subtasks} manageable subtasks suitable for a team comprising {num_roles} domain experts. The experts will contribute to the {num_subtasks} subtasks. Please follow the guidelines below to craft your answer:
    1. Remember, your role is to compose the TASK, not to complete the TASK directly.
    2. Focus on LLM Capabilities: Each subtask should leverage the strengths of a large language model (LLM), such as data processing, writing code, content generation, and etc.. Avoid assigning tasks that require physical actions or direct interaction with software/hardware systems, which are outside the LLM's capabilities.
    3. Define clear LLM-Appropriate Actions: Ensure each subtask is actionable, distinct, tapping into the expertise of the assigned roles and aligning with LLM capabilities. The subtasks should be designed considering that the LLM can handle complex tasks typically managed by domain experts. Recognize that not every subtask needs to directly reflect the main TASK's ultimate aim. Some subtasks serve as essential building blocks, paving the way for more central subtasks, but avoid creating subtasks that are self-dependent or overly foundational.
    4. Balanced Granularity with a Bias for Action: Details of subtask should be detailed, actionable, and not be ambiguous. Prioritize tangible actions in subtask such as implementation, creation, testing, or other tangible activities over mere understanding.
    5. Contextual Parameters: Please ensure that each subtask has the relevant context information from the TASK to avoid missing or contradicting the context information of the TASK. And try to provide as much information from CONTEXT TEXT as possible here.
    6. Dependencies & Gantt Chart: Identify and account for the dependencies within the subtasks. Ensure that each subtask logically flows from one to the next, or can run concurrently where no subtask is dependent on itself and with no subtask being dependent on the completion of another in a way that creates a cycle., in a manner that could be efficiently represented on a Gantt chart.
    7. Definitions of the Input of subtask:
        - Interlinking of Inputs: Ensure that the inputs are not siloed and can be interlinked within privous subtasks if necessary, providing a holistic view of what is required for the subtask.
        - Hierarchy and Prioritization: Identify and clearly state the priority and hierarchy (if applicable) among the inputs, ensuring the most critical elements are addressed promptly.
        - Accessibility and Clarity: Ensure that all provided inputs are accessible, clear, and understandable to the relevant team members.
        - Adjustability: Consider that inputs may need to be adjusted as the project progresses and ensure a mechanism for the same.
        - Subtask Dependency: Take into account the dependencies between different subtasks, ensuring that inputs for one subtask are aligned and coordinated with the needs and outputs of other related subtasks.
    8. Definitions of the Task Completion Standard in order to implement a feature in the software that can identify and mark a task as completed:
        - A task is considered completed when its intended output is produced.
        - If possible, the completion standard should be quantifiable to facilitate automatic detection by the software or tool feature.
        - The completion standard should be applicable to common project management scenarios and adaptable to various types of tasks, such as development, testing, and review tasks.
    9. Don't generate subtasks that might violate OpenAI's guidelines, which triggers the following error message: "I'm sorry, but I cannot fulfill your request.".
    10. Refrain from mentioning specific titles or roles (who are mentioned in the section of ROLES WITH DESCRIPTION) within the content of subtasks, unless the titles and personal names are mentioned in the TASK.
Your answer MUST strictly adhere to the structure of ANSWER TEMPLATE, ONLY fill in the BLANKs, and DO NOT alter or modify any other part of the template.\n\n\n"""  # noqa: E501

        # Generate insights from the context text to help decompose the task
        if context_text is not None:
            model_config = self.model_config
            insight_agent = InsightAgent(model_type=self.model_type,
                                         model_config=model_config)
            task_insights_json = insight_agent.run(context_text=context_text)
            task_context_prompt = (
                "===== CONTEXT TEXT =====\n"
                "The CONTEXT TEXT is related to TASK and "
                "Contextual Parameters of subtask. When "
                "decomposing the task, ensure that each subtask "
                "incorporates specific details from the "
                "INSIGHTS of CONTEXT TEXT.\n" +
                insight_agent.convert_json_to_str(task_insights_json) + "\n\n")
        else:
            task_context_prompt = ""

        task_prompt = TextPrompt("===== TASK =====\n" + task_prompt + "\n\n")
        role_with_description_prompt = \
            "===== ROLES WITH DESCRIPTION =====\n" + "\n".join(
                f"{role_name}:\n{role_descriptions_dict[role_name]}\n"
                for role_name in role_names) + "\n\n"
        if num_subtasks is None:
            answer_prompt = (
                "===== ANSWER TEMPLATE =====\n"
                "PART I (all subtasks):\n"
                "Details of subtask <NUM>:\n<BLANK>\n"
                "Contextual Parameters of subtask <NUM>:\n<BLANK>\n"
                "Content of the Input of subtask <NUM>:\n<BLANK>\n"
                "Input tags of subtask <NUM>: [<BLANK>, ..., <BLANK>]/[None] "
                "(must include square brackets)\n"
                "Task completion standard of subtask <NUM>:\n<BLANK>\n"
                "Dependency of subtask <NUM>: [subtask <i>, subtask <j>, "
                "subtask <k>]/[None] (must include square brackets).\n"
                "PART II:\nGantt Chart with complex dependency in MarkDown "
                "format:\n<BLANK>\n\n\n")
        else:
            answer_prompt = "===== ANSWER TEMPLATE =====\n" + \
                "PART I (all subtasks):\n" + \
                "\n".join(
                    f"Details of subtask {i + 1}:\n<BLANK>\n"
                    f"Contextual Parameters of subtask {i + 1}:\n<BLANK>\n"
                    f"Content of the Input of subtask {i + 1}:\n<BLANK>\n"
                    f"Input tags of subtask {i + 1}: [<BLANK>, ..., "
                    "<BLANK>]/[None] (must include square brackets)\n"
                    f"Task completion standard of subtask {i + 1}:\n<BLANK>\n"
                    f"Dependency of subtask {i + 1}: [subtask <i>, subtask "
                    f"<j>, subtask <k>]/[None] (must include square brackets)."
                    for i in range(num_subtasks)) + \
                "\nPART II:\nGantt Chart with complex dependency in " + \
                "MarkDown format:\n<BLANK>\n\n\n"
        split_task_prompt = TextPrompt(split_task_rules_prompt +
                                       answer_prompt + task_prompt + "\n\n" +
                                       task_context_prompt +
                                       role_with_description_prompt)
        subtasks_generation = split_task_prompt.format(
            num_subtasks=num_subtasks or "SEVERAL/ENOUGH",
            num_roles=len(role_names))

        subtasks_generation_msg = BaseMessage.make_user_message(
            role_name="Task Decomposer", content=subtasks_generation)

        model_type = self.model_type
        self.model_type = ModelType.GPT_4_TURBO
        response = self.step(input_message=subtasks_generation_msg)
        self.model_type = model_type

        if response.terminated:
            raise RuntimeError("Role compatibility scoring failed.\n" +
                               f"Error:\n{response.info}")
        msg = response.msg  # type: BaseMessage

        # Distribute the output completions into subtasks
        subtask_descriptions = [
            desc.replace("<", "").replace(">", "").strip('\n')
            for desc in re.findall(
                r"Details of subtask \d:[\s\n](.+?)Contextual Parameters of ",
                msg.content, re.DOTALL)
        ]
        subtask_contexts = [
            ctx.replace("<", "").replace(">", "").strip('\n')
            for ctx in re.findall(
                r"Contextual Parameters of subtask \d:[\s\n](.+?)Content of "
                r"the Input of subtask ", msg.content, re.DOTALL)
        ]
        subtask_inputs_content = [
            ipt.replace("<", "").replace(">", "").strip('\n')
            for ipt in re.findall(
                r"Content of the Input of subtask \d:[\s\n](.+?)"
                r"Input tags of ", msg.content, re.DOTALL)
        ]
        subtask_inputs_tags = [[
            tag.strip() for tag in re.findall(r"\[(.+?)\]", tag)[0].split(",")
        ] for tag in re.findall(r"Input tags of subtask \d:[\s\n]*\[.+?\]",
                                msg.content, re.DOTALL)]
        subtask_outputs_standard = [
            opt_std.replace("<", "").replace(">", "").strip('\n')
            for opt_std in re.findall(
                r"Task completion standard of subtask \d:[\s\n]"
                r"(.+?)Dependency of subtask", msg.content, re.DOTALL)
        ]
        subtask_dependencies = [[
            dep.strip() for dep in re.findall(r"\[(.+?)\]", dep)[0].split(",")
        ] for dep in re.findall(r"Dependency of subtask \d:[\s\n]*\[.+?\]",
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
                "context": ctx,
                "dependencies": deps,
                "input_tags": tags,
                "input_content": ipt,
                "output_standard": opt_std
            }
            for index, (desp, ctx, deps, tags, ipt, opt_std) in enumerate(
                zip(subtask_descriptions, subtask_contexts,
                    dependent_subtasks_list, subtask_inputs_tags,
                    subtask_inputs_content, subtask_outputs_standard))
        }

        if len(subtasks_with_dependencies_dict) == 0:
            raise RuntimeError("The task is not decomposed into subtasks.")
        if (num_subtasks is not None
                and (len(subtask_descriptions) != num_subtasks
                     or len(dependent_subtasks_list) != num_subtasks)):
            raise RuntimeError(
                f"Got None or insufficient information of subtasks. "
                f"Response of the LLM:\n{msg.content}\n"
                f"Length of generated subtasks: {len(subtask_descriptions)}, "
                "Length of generated dependencies: "
                f"{len(dependent_subtasks_list)}, "
                f"Length of required subtasks: {num_subtasks}")

        return subtasks_with_dependencies_dict

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
        oriented_graph: Dict[str, List[str]] = {}
        for subtask_idx, details in subtasks_with_dependencies_dict.items():
            assert isinstance(details, dict), \
                f"{subtask_idx} does not map to a dictionary: {details}"
            assert "dependencies" in details, \
                f"{subtask_idx} does not have a 'dependencies' key: {details}"
            deps = details["dependencies"]
            oriented_graph[subtask_idx] = deps

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
        parallel_subtask_pipelines: List[List[str]] = [[]]

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

    def draw_subtasks_graph(self, oriented_graph: Dict[str, List[str]],
                            graph_file_path: Optional[str] = None) -> str:
        r"""Draw the task dependency graph.

        Args:
            oriented_graph (Dict[str, List[str]]): The DAG of subtasks and
                their dependencies.
            graph_file_path (Optional[str], optional): The filepath of the
                saved graph. (default: :obj:`None`)

        Returns:
            str: The filepath of the saved graph.
        """

        # Initialize the graph
        G = nx.DiGraph()
        if len(oriented_graph) == 0:
            raise RuntimeError("The graph is empty since there are no "
                               "subtasks to be executed in the oriented "
                               "graph.")

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

        return graph_file_path

    def evaluate_role_compatibility(
        self,
        subtask_prompt: Union[str, TextPrompt],
        role_descriptions_dict: Dict[str, str],
    ) -> Dict[str, Dict[str, int]]:
        r"""Evaluate the compatibility scores of each role in relation to the
            specified task.

            Args:
                subtask_prompt (Union[str, TextPrompt]): The prompt for the
                    subtask based on which the roles are to be evaluated.
                role_descriptions_dict (Dict[str, str]): The role
                    descriptions of each role.

            Returns:
                Dict[str, Dict[str, int]]: A dictionary mapping role names to
                    their compatibility scores as user and assistant.
        """
        self.reset()

        role_names = list(role_descriptions_dict.keys())

        compatibility_instruction_prompt = """===== INSTRUCTIONS OF COMPATIBILITY EVALUATION =====
To evaluate the compatibility scores, consider these guiding principles:
    1. Remember, your role is to evaluate the compatibility of each role, not to complete the TASK directly.
    2. Assess the alignment between the primary responsibilities and expertise of the role with the task requirements. Factor in the likelihood of the role successfully executing the task based on its competencies.
    3. Analyze the congruence between keywords or key concepts in the task description and those present in the role description. This will gauge the direct relevance of the role to the task.
    4. Drawing from a comprehensive knowledge base, ascertain the potential value each role brings to the table when it comes to accomplishing the specific task. This evaluation should be based on empirical data or established norms in the relevant domain.
Definition of USER: The user is the role that guides the entire task process. They provide instructions and direction, ensuring that the task aligns with their needs and goals. Users need to utilize their expertise and understanding of the task to propose specific subtasks, expecting the assistant to execute these tasks.
Definition of ASSISTANT: The assistant is the role that executes instructions given by the user. They apply their professional skills and knowledge to complete specific tasks assigned by the user. Assistants must act flexibly according to the user's instructions and provide professional solutions and feedback.

"""  # noqa: E501
        task_prompt = TextPrompt("===== TASK =====\n" + subtask_prompt +
                                 "\n\n")
        role_with_description_prompt = \
            "===== ROLES WITH DESCRIPTION =====\n" + "\n".join(
                f"{role_name}:\n{role_descriptions_dict[role_name]}\n"
                for role_name in role_names) + "\n\n"
        answer_prompt = \
            "===== ANSWER TEMPLATE =====\n" + "\n".join(
                f"Explanation for role {role_name} as USER: <BLANK>\n"
                f"Score of role {role_name} as USER: <BLANK>\n"
                f"Explanation for role {role_name} as ASSISTANT: <BLANK>\n"
                f"Score of role {role_name} as ASSISTANT: <BLANK>\n"
                for role_name in role_names) + "\n"
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

        if "I'm sorry" in msg.content.strip():
            raise RuntimeError(
                "May violate the guidelines of the large language "
                "model.\n"
                f"Response of the LLM:\n{msg.content}\n")

        # Distribute the output completions into scores
        user_compatibility_scores = [
            desc.replace("<", "").replace(">", "").strip('\n')
            for desc in re.findall(r"Score of role .+? as USER: (.+?)(?=\n|$)",
                                   msg.content)
        ]
        assistant_compatibility_scores = [
            desc.replace("<", "").replace(">", "").strip('\n')
            for desc in re.findall(
                r"Score of role .+? as ASSISTANT: (.+?)(?=\n|$)", msg.content)
        ]

        if len(user_compatibility_scores) != len(role_names):
            raise RuntimeError("Got None or insufficient information of "
                               "compatibility scores as USER.\n"
                               f"Response of the LLM:\n{msg.content}\n")
        if len(assistant_compatibility_scores) != len(role_names):
            raise RuntimeError("Got None or insufficient information of " +
                               "compatibility scores as ASSISTANT."
                               f"Response of the LLM:\n{msg.content}\n")

        role_compatibility_scores_dict = {
            role_name: {
                "score_user": int(user_score),
                "score_assistant": int(assistant_score)
            }
            for role_name, user_score, assistant_score in zip(
                role_names, user_compatibility_scores,
                assistant_compatibility_scores)
        }

        return role_compatibility_scores_dict

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
3. If the content of the square brackets is "NONE", meaning that there is no similar label or subset, you should fill in "NONE" in the BLANKs.
4. For example, "apple" and "fruit" may be considered similar in a context where they are being used to describe food items.
Please ensure that you consider both explicit and implicit similarities while evaluating. The result should be a set of indices pointing to the similar labels and sets."""  # noqa: E501
        answer_prompt = "===== ANSWER TEMPLATE =====\n"
        for lable in target_labels:
            answer_prompt += (
                f"Label \"{lable}\" from TARGET LABELS has "
                "an explicit or implicit similarity with \"<BLANK>/NONE\" "
                "(or similar label) in LABELS SETS subsets [<m>, <n>] "
                "(must include square brackets even if it is none).\n")
        answer_prompt += (
            "Indices of the similar labels in TARGET LABELS: "
            "[<i>, <j>] (must include square brackets even if it is none) \n"
            "Indices of the similar subset in LABELS SETS: "
            "[<x>, <y>] (must include square brackets even if it is none)")

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
            if idx.isdigit()
        ] if match_target_labels else []

        target_retrieved_labels = \
            [target_labels[idx] for idx in target_labels_indices]

        match_labels_sets = re.findall(
            r"Indices of the similar subset in LABELS SETS: \[(.+?)\]",
            msg.content, re.DOTALL)
        labels_sets_indices = [
            int(idx) for idx in match_labels_sets[0].split(",")
            if idx.isdigit()
        ] if match_labels_sets else []

        labels_retrieved_sets = \
            [labels_sets[idx] for idx in labels_sets_indices]

        return target_labels_indices, labels_sets_indices, \
            target_retrieved_labels, labels_retrieved_sets

    def transform_dialogue_into_text(
            self, user_name: str, assistant_name: str, task_prompt: str,
            user_conversation: str,
            assistant_conversation: str) -> Dict[str, Any]:
        r"""Synthesize a narrative from the chat history.

        Args:
            user_name (str): The name of the user.
            assistant_name (str): The name of the assistant.
            task_prompt (str): The prompt for the task.
            user_conversation (str): The conversation of the user.
            assistant_conversation (str): The conversation of the assistant.

        Returns:
            Dict[str, Any]: A dictionary with two keys: `categories`: a list
                of cleaned and validated category names; `text`: a single
                string of cleaned reproduced text.
        """
        self.reset()

        text_synthesis = """You are a conversation analyst, and you are asked to identify the category of the assistant's response in the PROVIDED TEXT based on the definition of CATEGORY OF RESPONSES.
Then, retell the user's conversation in a way that corresponds to the category of response, rather than using the tone of dialogue, during the retelling you need to use as much information and expression from the assistant's response as possible to help you retell it.
reproduce the assistant's original response into text according to the definition of CATEGORY OF RESPONSES and without losing the ability and quality to solve TASK.
Your answer MUST strictly adhere to the structure of ANSWER TEMPLATE, ONLY fill in the BLANKs, and DO NOT alter or modify any other part of the template.


===== CATEGORY OF RESPONSES =====
1. Direct Task Assistance (noted as "ASSISTANCE")
    a. Definition:
        - Replies under this category provide concrete information, steps, or solutions that directly aid in completing a task. They contain the core elements and direct methods for task execution.
    b. Relevant Information:
        - Explicit instructions or steps to complete the task
        - Task-specific data, code, solutions, or technical methodologies
        - Analysis, implementation plans or text generation related to the task
2. Substantial Analysis and Optimization (noted as "ANALYSIS")
    a. Definition:
        - This category includes in-depth analysis of existing information or methods, offering insights, suggestions for improvement, or optimization strategies for task completion.
    b. Relevant Information:
        - Evaluation of the efficiency and effectiveness of task methodologies
        - Predictions and solutions for potential problems or challenges in the task
        - Recommendations for improving and optimizing current methods
3. Auxiliary Information Provision (noted as "AUXILIARY")
    a. Definition:
        - Answers in this category provide background knowledge or supplementary information indirectly related to the task, helping to better understand the context of the task.
    b. Relevant Information:
        - Background knowledge or additional information to understand the overall context or specific details of the task
        - Fundamental concepts, terminology explanations, or background situations related to the task area
        - Case studies or examples in relevant fields or topics
4. Non-Substantial or Indirect Assistance (noted as "NON-SUBSTANTIAL")
    a. Definition:
        - These responses may offer emotional support, encouragement, or non-specific advice but do not directly contribute concrete help towards the actual completion of a task.
    b. Relevant Information:
        - Responses with emotional support or encouragement
        - General advice or guidance without specific solutions for the task
        - General insights or opinions not directly related to the task completion


===== PROVIDED TEXT =====
[Global TASK of Conversation]\n{task_prompt}
[User: {user_name}]:\n{user_conversation}
[Assistant: {assistant_name}]:\n{assistant_conversation}


===== ANSWER TEMPLATE =====
Category of Assistant's Response: [<BLANK>, ..., <BLANK>] (choose from "ASSISTANCE", "ANALYSIS", "AUXILIARY", "NON-SUBSTANTIAL", must include square brackets, multiple choices are separated by commas)
Retold Text:\n<BLANK>"""  # noqa: E501
        text_synthesis_prompt = TextPrompt(text_synthesis)

        text_synthesis_generation = text_synthesis_prompt.format(
            user_name=user_name, assistant_name=assistant_name,
            task_prompt=task_prompt, user_conversation=user_conversation,
            assistant_conversation=assistant_conversation)

        text_synthesis_generation_msg = BaseMessage.make_user_message(
            role_name="Conversation Analyst",
            content=text_synthesis_generation)

        response = self.step(input_message=text_synthesis_generation_msg)

        if response.terminated:
            raise RuntimeError("Generating reproduced text failed." +
                               f"Error:\n{response.info}")
        msg = response.msg  # type: BaseMessage

        # Distribute the output completions into narrative synthesis
        category_of_responses = re.findall(
            r"Category of Assistant's Response: \[(.+?)\]", msg.content)
        reproduced_texts = re.findall(r"Retold Text:\n\s*(.+)", msg.content,
                                      re.DOTALL)

        if category_of_responses is None or len(category_of_responses) == 0:
            raise RuntimeError("Got None of category of responses."
                               f"Response of the LLM:\n{msg.content}\n")
        categories = [
            category.strip().strip('"\'')
            for category in category_of_responses[0].split(',')
        ]
        for category in categories:
            if category not in [
                    "ASSISTANCE", "ANALYSIS", "AUXILIARY", "NON-SUBSTANTIAL"
            ]:
                raise RuntimeError("Got invalid category of responses."
                                   f"Response of the LLM:\n{msg.content}\n")

        if reproduced_texts is None or len(reproduced_texts) == 0:
            raise RuntimeError("Got None of reproduced text."
                               f"Response of the LLM:\n{msg.content}\n")
        reproduced_text = reproduced_texts[0].strip('\n')

        reproduced_text_with_category = {
            "categories": categories,
            "text": reproduced_text
        }

        return reproduced_text_with_category
