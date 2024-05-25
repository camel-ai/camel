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
import json

from camel.agents.chat_agent import ChatAgent
from camel.functions import OpenAIFunction
from camel.messages import BaseMessage
from camel.prompts import TextPrompt
from camel.types import ModelType, RoleType


def extract_json_from_string(input_str: str) -> dict:
    r"""Extract the the first JSON from a string, and returns it as a Python
    dictionary.

    Args:
        string (str): The string to extract JSON from.

    Returns:
        dict: The first JSON object found in the string as a Python dictionary.
    """
    input_str = input_str.replace('\\', '\\\\')  # escaping backslashes first

    in_quotes = False
    in_code_block = False
    escaped = False
    depth = 0
    start_index = -1
    clean_input = []

    i = 0
    while i < len(input_str):
        char = input_str[i]

        # Check for code block start or end
        if (
            input_str[i : i + 3] == '```' and input_str[i + 3 : i + 7] != 'json'
        ):  # assuming ``` as code block delimiter
            in_code_block = not in_code_block
            i += 3  # Skip the next two characters as well
            continue

        if char == '"' and not escaped and not in_code_block:
            in_quotes = not in_quotes

        if in_quotes or in_code_block:
            if char == '\\' and not escaped:
                escaped = True
            elif escaped:
                escaped = False
            else:
                if char == '\n':
                    clean_input.append('\\n')
                elif char == '"' and in_code_block:
                    # Escape quotes only inside code blocks
                    clean_input.append('\\"')
                else:
                    clean_input.append(char)
        else:
            clean_input.append(char)

        if char == '{' and not in_quotes and not in_code_block:
            depth += 1
            if depth == 1:
                start_index = i  # mark the start of a JSON object
        elif char == '}' and not in_quotes and not in_code_block:
            depth -= 1
            if depth == 0 and start_index != -1:
                cleaned_str = ''.join(clean_input[start_index : i + 1])
                try:
                    return json.loads(cleaned_str)
                except json.JSONDecodeError as e:
                    raise ValueError(
                        "Failed to decode JSON object:\n"
                        + cleaned_str
                        + "\n"
                        + str(e)
                    ) from e

        i += 1

    raise ValueError("No complete JSON object found:\n" + ''.join(clean_input))

class RoleAssignmentAgent(ChatAgent):
    r"""An agent that generates role names based on the task prompt.
    Attributes:
        role_assignment_prompt (TextPrompt): A prompt for the agent to generate
        role names.

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
            role_name="Role Assigner",
            role_type=RoleType.ASSISTANT,
            meta_dict=None,
            content="You assign roles based on tasks.",
        )
        super().__init__(system_message, model_type, model_config)

    def run(
        self,
        task_prompt: Union[str, TextPrompt],
        num_roles: int = 2,
        role_names: Optional[List[str]] = None,
        role_descriptions_instruction: Optional[Union[str, TextPrompt]] = None,
        function_list: Optional[list[OpenAIFunction]] = None,
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

        if num_roles is None:
            raise ValueError("Number of roles must be provided.")
        if num_roles < 1:
            raise ValueError("Number of roles must be greater than 0.")
        if role_names is not None and len(role_names) != num_roles:
            raise RuntimeError("Got None or insufficient information of roles.")

        task_prompt = TextPrompt("===== TASK =====\n" + task_prompt + "\n\n")
        if role_names is None:
            expert_json_prompt = """===== ANSWER TEMPLATE (JSON) =====
{
    "Domain expert <NUM>": {
        "Role name": "<BLANK>",
        "Associated competencies, characteristics, and duties": "<BLANK>"
    },
    // it is allowed to complete more domain experts
    "Domain expert <NUM2>": {
        "Role name": "<BLANK>",
        "Associated competencies, characteristics, and duties": "<BLANK>"
    },
}"""
        else:
            expert_json_prompt = (
                "===== ANSWER TEMPLATE (JSON) =====\n{\n"
                + ", \n".join(
                    f"    \"Domain expert {i + 1}\": {{\n"
                    f"        \"Role name\": \"{role_name}"
                    "\",\n        \"Associated competencies, "
                    "characteristics, and duties\": "
                    "\"<BLANK>\"\n    },"
                    for i, role_name in enumerate(role_names)
                )
                + "\n}"
            )

        if role_descriptions_instruction is None:
            role_descriptions_instruction = ""
        else:
            role_descriptions_instruction = (
                "Moreover, " + role_descriptions_instruction
            )
        if function_list is not None and len(function_list) > 0:
            function_docstring = """===== FUNCTION LIST (CONTEXT) =====
You have been provided with a list of tools for work. Each tool description explains the purpose and usage of a specific tool for work.
The tool descriptions are the context information of the potential competencies of the domain experts (for example, some experts may have the ability of Google searching).
"""
            for i, function in enumerate(function_list):
                description_lines = function.get_function_description().split(
                    '\n'
                )
                indented_description = '\n'.join(
                    '\t' + line for line in description_lines
                )
                function_docstring += (
                    f"{i + 1}. Ability or tool of "
                    f"{function.get_function_name()}:\n"
                    f"{indented_description}\n\n"
                )
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
            "experts, not to complete the TASK directly.\n"
            + role_descriptions_instruction
            + "\n"
            "Your answer MUST strictly adhere to the structure of ANSWER "
            "TEMPLATE, ONLY fill in the BLANKs, and DO NOT alter or modify "
            "any other part of the template.\n\n" + function_docstring
        )
        role_assignment_generation: str = (
            role_assignment_generation_prompt.format(
                num_roles=num_roles, task=task_prompt
            )
        )
        role_assignment_generation += expert_json_prompt + task_prompt
        print(f"expert_json_prompt:\n{expert_json_prompt}")

        role_assignment_generation_msg = BaseMessage.make_user_message(
            role_name="Role Assigner", content=role_assignment_generation
        )

        response = self.step(input_message=role_assignment_generation_msg)

        if response.terminated:
            raise RuntimeError(
                "Role compatibility scoring failed.\n"
                + f"Error:\n{response.info}"
            )
        msg = response.msg  # type: BaseMessage

        if "I'm sorry" in msg.content.strip():
            raise RuntimeError(
                "May violate the guidelines of the large "
                "language model.\n"
                f"Response of the LLM:\n{msg.content}"
            )

        json_dict = extract_json_from_string(msg.content)

        # Distribute the output completions into role names and descriptions
        role_descriptions_dict = {}
        for _, expert_data in json_dict.items():
            role_name = expert_data["Role name"]
            description = expert_data[
                "Associated competencies," + " characteristics, and duties"
            ]
            role_descriptions_dict[role_name] = description

        if num_roles != len(role_descriptions_dict):
            raise RuntimeError(
                "Got None or insufficient information of roles.\n"
                f"Response of the LLM:\n{msg.content}\n"
                f"Role names:{role_names!s}\n"
                f"Role descriptions:\n{role_descriptions_dict!s}"
            )

        return role_descriptions_dict
