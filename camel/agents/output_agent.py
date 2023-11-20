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
from typing import Optional

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.models.openai_model import OpenAIModel
from camel.types import ChatCompletion, ChatCompletionChunk, ModelType


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

    SYSTEM_PROMPT = (
        "You are a helpful assistant to re-organize information "
        "into a detailed instruction, below is the content for you:\n{content}"
    )
    USER_MESSAGE = (
        "Please extract the detailed action information "
        "from the provided content, "
        "make it useful for a human to follow the detailed instruction "
        "step by step to solve the task.")

    def __init__(self, content: str,
                 model_type: ModelType = ModelType.GPT_3_5_TURBO_16K):
        r"""
        Initialize the OutputAgent.
        """
        self.content = content
        self.model = self._create_model(model_type)

    @staticmethod
    def _create_model(model_type: ModelType) -> OpenAIModel:
        r"""
        Creates and returns an OpenAI model.
        Args:
            model_type (ModelType): The type of the OpenAI model to use.
        Returns:
            OpenAIModel: The initialized model.
        """
        config = ChatGPTConfig()
        return OpenAIModel(model_type=model_type,
                           model_config_dict=config.__dict__)

    def _construct_task_prompt(self) -> list:
        r"""
        Constructs the task prompt based on the content.
        Returns:
            list: List of messages forming the prompt.
        """
        return [{
            "role": "system",
            "content": self.SYSTEM_PROMPT.format(content=self.content)
        }, {
            "role": "user",
            "content": self.USER_MESSAGE
        }]

    def generate_detailed_instruction(self) -> Optional[str]:
        r"""
        Generate a detailed instruction based on the provided content.
        Returns:
            str: The detailed instruction.
        """
        response = self.model.run(messages=self._construct_task_prompt())

        # Check if response is of type ChatCompletion
        if isinstance(response, ChatCompletion):
            if response.choices:
                return response.choices[0].message.content
        # Check if response is a Stream of ChatCompletionChunk
        elif isinstance(response, ChatCompletionChunk):
            # Handle the Stream[ChatCompletionChunk] case
            # and aggregate the results or handle them differently.
            for chunk in response:
                # Process each chunk as needed
                pass
        return None
