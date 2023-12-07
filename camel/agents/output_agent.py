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
from typing import Any, Optional

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.prompts import TextPrompt
from camel.types import ModelType, RoleType


class OutputAgent(ChatAgent):
    r"""An agent used to re-organize the chat history of multi-agent
    into detailed instruction.

    Attributes:
            SYSTEM_PROMPT (str): Prompt to explain the agent's role.
            USER_MESSAGE (str): User message to request a detailed instruction.

    Args:
        content (str): The content to be processed.
        model_type (ModelType): The type of the OpenAI model to use.
    """

    def __init__(
        self,
        model_type: ModelType = ModelType.GPT_3_5_TURBO,
        model_config: Optional[Any] = None,
    ) -> None:
        system_message = BaseMessage(
            role_name="Output Agent",
            role_type=RoleType.ASSISTANT,
            meta_dict=None,
            content="The assistant is an output agent.",
        )
        super().__init__(system_message, model_type, model_config)

    def generate_detailed_instruction(self, text: str) -> Optional[str]:
        r"""Generate a detailed instruction based on the provided content.

        Args:
            text (str): The content to be processed by the AI agent.

        Returns:
            str: The detailed instruction.
        """
        self.reset()

        text_generation_prompt = TextPrompt(
            "You are a helpful assistant to re-organize information "
            "into a detailed instruction, below is the CONTENT for you:\n"
            "===== CONTENT =====\n{content}\n===== CONTENT END =====\n\n"
            "Please extract the detailed action information "
            "from the provided content, "
            "make it useful for a human to follow the detailed instruction "
            "step by step to solve the task.")
        text_generation = text_generation_prompt.format(content=text)

        text_generation_msg = BaseMessage.make_user_message(
            role_name="Output Agent", content=text_generation)

        response = self.step(input_message=text_generation_msg)

        if response.terminated:
            raise RuntimeError("The agent was unexpectedly terminated.\n"
                               f"Error:\n{response.info}")

        msg: BaseMessage = response.msg

        return msg.content
