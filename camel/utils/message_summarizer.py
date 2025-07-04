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

from pydantic import BaseModel, Field

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import BaseModelBackend, ModelFactory
from camel.types import ModelPlatformType, ModelType


class MessageSummary(BaseModel):
    r"""Schema for structured message summaries.

    Attributes:
        summary (str): A brief, one-sentence summary of the conversation.
        participants (List[str]): The roles of participants involved.
        key_topics_and_entities (List[str]): Important topics, concepts, and
            entities discussed.
        decisions_and_outcomes (List[str]): Key decisions, conclusions, or
            outcomes reached.
        action_items (List[str]): A list of specific tasks or actions to be
            taken, with assignees if mentioned.
        progress_on_main_task (str): A summary of progress made on the
            primary task.
    """

    summary: str = Field(
        description="A brief, one-sentence summary of the conversation."
    )
    participants: List[str] = Field(
        description="The roles of participants involved."
    )
    key_topics_and_entities: List[str] = Field(
        description="Important topics, concepts, and entities discussed."
    )
    decisions_and_outcomes: List[str] = Field(
        description="Key decisions, conclusions, or outcomes reached."
    )
    action_items: List[str] = Field(
        description=(
            "A list of specific tasks or actions to be taken, with assignees "
            "if mentioned."
        )
    )
    progress_on_main_task: str = Field(
        description="A summary of progress made on the primary task."
    )


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
                content=(
                    "You are an expert conversation summarizer. Your task is "
                    "to analyze chat messages and create a structured summary "
                    "in JSON format. The summary should capture:\n"
                    "- summary: A brief, one-sentence summary of the "
                    "conversation.\n"
                    "- participants: The roles of participants involved.\n"
                    "- key_topics_and_entities: Important topics, concepts, "
                    "and entities discussed.\n"
                    "- decisions_and_outcomes: Key decisions, conclusions, or "
                    "outcomes reached.\n"
                    "- action_items: A list of specific tasks or actions to "
                    "be taken, with assignees if mentioned.\n"
                    "- progress_on_main_task: A summary of progress made on "
                    "the primary task.\n\n"
                    "Your response must be a JSON object that strictly "
                    "adheres to this structure. Be concise and accurate."
                ),
            ),
            model=self.model_backend,
        )

    def summarize(self, messages: List[BaseMessage]) -> MessageSummary:
        r"""Generate a structured summary of the provided messages.

        Args:
            messages (List[BaseMessage]): List of messages to summarize.

        Returns:
            MessageSummary: Structured summary of the conversation.

        Raises:
            ValueError: If the messages list is empty or if the model's
            response cannot be parsed as valid JSON.
        """
        if not messages:
            raise ValueError("Cannot summarize an empty list of messages.")

        # Construct prompt from messages
        message_text = "\n".join(
            f"{msg.role_name}: {msg.content}" for msg in messages
        )
        prompt = (
            "Please analyze the following chat messages and generate a "
            "structured summary.\n\n"
            f"MESSAGES:\n\"\"\"\n{message_text}\n\"\"\"\n\n"
            "Your response must be a JSON object that strictly adheres to the "
            "required format."
        )

        # Get structured summary from model with forced JSON response
        response = self.agent.step(prompt, response_format=MessageSummary)

        if response.msg is None or response.msg.parsed is None:
            raise ValueError(
                "Failed to get a structured summary from the model."
            )

        summary = response.msg.parsed
        if not isinstance(summary, MessageSummary):
            raise ValueError("The parsed response is not a MessageSummary.")

        return summary
