# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
import json
from typing import List, Optional, Union

from pydantic import BaseModel

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.utils.response_format import model_from_json_schema


class SummarySchema(BaseModel):
    """Schema for structured message summaries.

    Attributes:
        roles (List[str]): The roles involved in the conversation
        key_entities (List[str]): Important entities/concepts discussed
        decisions (List[str]): Key decisions or conclusions reached
        task_progress (str): Summary of progress made on the main task
        context (str): Additional relevant contextual information
    """

    roles: List[str]
    key_entities: List[str]
    decisions: List[str]
    task_progress: str
    context: str


class MessageSummarizer:
    """Utility class for generating structured summaries of chat messages.

    Args:
        model (Union[str, ModelType], optional):
            The model to use for summarization.
            Defaults to ModelType.DEFAULT.
    """

    def __init__(
        self,
        model: Optional[Union[str, ModelType]] = None,
    ):
        self.model_backend = ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=model or ModelType.GPT_4O_MINI,
        )
        self.agent = ChatAgent(
            BaseMessage.make_assistant_message(
                role_name="Message Summarizer",
                content="You are a skilled conversation summarizer. "
                "Your task is to analyze chat messages and "
                "create structured summaries that "
                "capture:\n"
                "- The key roles involved\n"
                "- Important entities and concepts discussed\n"
                "- Key decisions or conclusions reached\n"
                "- Progress made on the main task\n"
                "- Relevant contextual information\n\n"
                "Provide summaries that are concise while "
                "preserving critical information.",
            ),
            model=self.model_backend,
        )

    def summarize(self, messages: List[BaseMessage]) -> SummarySchema:
        """Generate a structured summary of the provided messages.

        Args:
            messages (List[BaseMessage]): List of messages to summarize

        Returns:
            SummarySchema: Structured summary of the conversation

        Raises:
            ValueError: If the model's response cannot be parsed as valid JSON
        """
        # When messages is empty
        if len(messages) == 0:
            return SummarySchema(
                roles=[],
                key_entities=[],
                decisions=[],
                task_progress="",
                context="",
            )

        # Define the expected response schema
        response_schema = {
            "type": "object",
            "required": [
                "roles",
                "key_entities",
                "decisions",
                "task_progress",
                "context",
            ],
            "properties": {
                "roles": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of roles involved\
in the conversation",
                },
                "key_entities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of important \
entities/concepts discussed",
                },
                "decisions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of key decisions or \
conclusions reached",
                },
                "task_progress": {
                    "type": "string",
                    "description": "Summary of progress made on the \
main task",
                },
                "context": {
                    "type": "string",
                    "description": "Additional relevant \
contextual information",
                },
            },
        }

        # Create a Pydantic model from the schema
        ResponseModel = model_from_json_schema(
            "ResponseModel", response_schema
        )

        # Construct prompt from messages
        message_text = "\n".join(
            f"{msg.role_name}: {msg.content}" for msg in messages
        )
        prompt = (
            "Please analyze these messages and provide a structured summary:\n"
            + message_text
            + "\n\nYour response must be a JSON object with these fields:\n"
            "- roles: list of roles involved\n"
            "- key_entities: list of important entities/concepts\n"
            "- decisions: list of key decisions made\n"
            "- task_progress: summary of progress on main task\n"
            "- context: additional relevant context"
        )

        # Get structured summary from model with forced JSON response
        response = self.agent.step(prompt, response_format=ResponseModel)
        try:
            # The response should already be validated by the model
            content = response.msg.content
            if isinstance(content, str):
                content = json.loads(content)
            return SummarySchema(**content)
        except Exception as e:
            raise ValueError(f"Response validation failed: {e!s}")
