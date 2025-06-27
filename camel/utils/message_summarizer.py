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
from typing import List, Optional

from pydantic import BaseModel

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import BaseModelBackend, ModelFactory
from camel.types import ModelPlatformType, ModelType


class SummarySchema(BaseModel):
    r"""Schema for structured message summaries.

    Attributes:
        roles (List[str]): The roles involved in the conversation.
        key_entities (List[str]): Important entities/concepts discussed.
        decisions (List[str]): Key decisions or conclusions reached.
        task_progress (str): Summary of progress made on the main task.
        context (str): Additional relevant contextual information.
    """

    roles: List[str]
    key_entities: List[str]
    decisions: List[str]
    task_progress: str
    context: str


class SummaryResponseSchema(BaseModel):
    r"""Schema for the model's structured summary response.

    Attributes:
        roles (List[str]): List of roles involved in the conversation.
        key_entities (List[str]): List of important entities discussed.
        decisions (List[str]): List of key decisions or conclusions reached.
        task_progress (str): Summary of progress made on the main task.
        context (str): Additional relevant contextual information.
    """

    roles: List[str]
    key_entities: List[str]
    decisions: List[str]
    task_progress: str
    context: str


class MessageSummarizer:
    r"""Utility class for generating structured summaries of chat messages.

    Args:
        model_backend (Optional[BaseModelBackend], optional):
            The model backend to use for summarization.
            If not provided, a default model backend will be created.
    """

    def __init__(
        self,
        model_backend: Optional[BaseModelBackend] = None,
    ):
        if model_backend is None:
            self.model_backend = ModelFactory.create(
                model_platform=ModelPlatformType.DEFAULT,
                model_type=ModelType.GPT_4O_MINI,
            )
        else:
            self.model_backend = model_backend
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
        r"""Generate a structured summary of the provided messages.

        Args:
            messages (List[BaseMessage]): List of messages to summarize.

        Returns:
            SummarySchema: Structured summary of the conversation.

        Raises:
            ValueError: If the messages list is empty or if the model's
            response cannot be parsed as valid JSON.
        """
        # When messages is empty
        if len(messages) == 0:
            raise ValueError("Cannot summarize an empty list of messages.")

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
        response = self.agent.step(
            prompt, response_format=SummaryResponseSchema
        )
        try:
            # The response should already be validated and parsed by the model
            parsed_response = response.msg.parsed
            if parsed_response is None:
                raise ValueError(
                    "Failed to parse response into structured format"
                )
            return SummarySchema(**parsed_response.model_dump())
        except Exception as e:
            raise ValueError(f"Response validation failed: {e!s}")
