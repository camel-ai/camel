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

from tenacity import retry, stop_after_attempt, wait_exponential

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.prompts import TextPrompt
from camel.typing import ModelType, RoleType


class RoleAssignmentAgent(ChatAgent):
    r"""An agent that generates role names based on the task prompt.
    Attributes:
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

    @retry(wait=wait_exponential(min=5, max=60), stop=stop_after_attempt(5))
    def run_role_with_description(
        self,
        num_roles: Optional[int] = 2,
        task_prompt: Union[str, TextPrompt] = "",
    ) -> Tuple[List[str], Dict[str, str], bool, Dict[str, Any]]:
        r"""Generate role names based on the input task prompt.

        Args:
            num_roles (int, optional): The number of roles to generate.
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
            f"and workflows: <|blank|>. End.\n" for i in range(num_roles or 0))
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

        response_completion = super().step(
            input_message=role_assignment_generation_msg)

        output_completion = response_completion.msg  # type: BaseMessage
        terminated = response_completion.terminated
        info = response_completion.info

        # Distribute the output completions into role names and descriptions
        role_names = [
            desc.replace("<|", "").replace("|>", "") for desc in re.findall(
                r"Domain expert \d: (.+?)\nAssociated competencies,",
                output_completion.content,
                re.DOTALL,
            )
        ]
        role_descriptions = [
            desc.replace("<|", "").replace("|>", "") for desc in re.findall(
                r"Associated competencies, professional characteristics, "
                r"duties and workflows: (.+?) End.", output_completion.content,
                re.DOTALL)
        ]

        if len(role_names) != num_roles or len(role_descriptions) != num_roles:
            raise RuntimeError("Got None or insufficient Role messages. ")
        if terminated:
            raise RuntimeError("Role assignment failed.")

        role_descriptions_dict = {
            role_name: description
            for role_name, description in zip(role_names, role_descriptions)
        }

        return role_names, role_descriptions_dict, terminated, info
