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
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel, Field

from camel.logger import get_logger
from camel.messages import BaseMessage, OpenAIMessage
from camel.models import BaseModelBackend, ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.utils.context_utils import ContextUtility

logger = get_logger(__name__)


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

        # Import ChatAgent here to avoid circular import
        from camel.agents import ChatAgent

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

    def build_default_summary_prompt(self, conversation_text: str) -> str:
        r"""Create the default prompt used for conversation summarization.

        Args:
            conversation_text (str): The conversation to be summarized.

        Returns:
            str: A formatted prompt instructing the model to produce a
                structured markdown summary.
        """
        template = textwrap.dedent(
            """\
            Summarize the conversation below.
            Produce markdown that strictly follows this outline and numbering:

            Summary:
            1. **Primary Request and Intent**:
            2. **Key Concepts**:
            3. **Errors and Fixes**:
            4. **Problem Solving**:
            5. **Pending Tasks**:
            6. **Current Work**:
            7. **Optional Next Step**:

            Requirements:
            - Use bullet lists under each section (`- item`). If a section
            has no information, output `- None noted`.
            - Keep the ordering, headings, and formatting as written above.
            - Focus on concrete actions, findings, and decisions.
            - Do not invent details that are not supported by the conversation.

            Conversation:
            {conversation_text}
            """
        )
        return template.format(conversation_text=conversation_text)

    @staticmethod
    def _append_user_messages_section(
        summary_content: str, user_messages: List[str]
    ) -> str:
        r"""Append a section with user messages to the summary content.

        Args:
            summary_content (str): The existing summary content.
            user_messages (List[str]): List of user messages to append.

        Returns:
            str: Updated summary content with user messages section.
        """
        section_title = "- **All User Messages**:"
        sanitized_messages: List[str] = []
        for msg in user_messages:
            if not isinstance(msg, str):
                msg = str(msg)
            cleaned = " ".join(msg.strip().splitlines())
            if cleaned:
                sanitized_messages.append(cleaned)

        bullet_block = (
            "\n".join(f"- {m}" for m in sanitized_messages)
            if sanitized_messages
            else "- None noted"
        )
        user_section = f"{section_title}\n{bullet_block}"

        summary_clean = summary_content.rstrip()
        return f"{summary_clean}\n\n{user_section}"

    @staticmethod
    def _convert_messages_to_text(
        messages: List[OpenAIMessage], include_summaries: bool
    ) -> tuple[str, List[str]]:
        r"""Convert OpenAI messages to conversation text.

        Args:
            messages (List[OpenAIMessage]): List of OpenAI messages.
            include_summaries (bool): Whether to include summary messages.

        Returns:
            tuple[str, List[str]]: Conversation text and list of user messages.
        """
        conversation_lines = []
        user_messages: List[str] = []
        for message in messages:
            role = message.get('role', 'unknown')
            content = message.get('content', '')

            # Skip summary messages if include_summaries is False
            if not include_summaries and isinstance(content, str):
                # Check if this is a summary message by looking for marker
                if content.startswith('[CONTEXT_SUMMARY]'):
                    continue

            # Handle tool call messages (assistant calling tools)
            tool_calls = message.get('tool_calls')
            if tool_calls and isinstance(tool_calls, (list, tuple)):
                for tool_call in tool_calls:
                    # Handle both dict and object formats
                    if isinstance(tool_call, dict):
                        func_name = tool_call.get('function', {}).get(
                            'name', 'unknown_tool'
                        )
                        func_args_str = tool_call.get('function', {}).get(
                            'arguments', '{}'
                        )
                    else:
                        # Handle object format (Pydantic or similar)
                        func_name = getattr(
                            getattr(tool_call, 'function', None),
                            'name',
                            'unknown_tool',
                        )
                        func_args_str = getattr(
                            getattr(tool_call, 'function', None),
                            'arguments',
                            '{}',
                        )

                    # Parse and format arguments for readability
                    try:
                        args_dict = json.loads(func_args_str)
                        args_formatted = ', '.join(
                            f"{k}={v}" for k, v in args_dict.items()
                        )
                    except (json.JSONDecodeError, ValueError, TypeError):
                        args_formatted = func_args_str

                    conversation_lines.append(
                        f"[TOOL CALL] {func_name}({args_formatted})"
                    )

            # Handle tool response messages
            elif role == 'tool':
                tool_name = message.get('name', 'unknown_tool')
                if not content:
                    content = str(message.get('content', ''))
                conversation_lines.append(
                    f"[TOOL RESULT] {tool_name} → {content}"
                )

            # Handle regular content messages (user/assistant/system)
            elif content:
                content = str(content)
                if role == 'user':
                    user_messages.append(content)
                conversation_lines.append(f"{role}: {content}")

        conversation_text = "\n".join(conversation_lines).strip()
        return conversation_text, user_messages

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

    async def asummarize(
        self,
        messages: List[OpenAIMessage],
        agent_id: str = "agent",
        filename: Optional[str] = None,
        summary_prompt: Optional[str] = None,
        response_format: Optional[Type[BaseModel]] = None,
        working_directory: Optional[Union[str, Path]] = None,
        include_summaries: bool = False,
        add_user_messages: bool = True,
    ) -> Dict[str, Any]:
        r"""Asynchronously summarize conversation messages and persist to file.

        This method converts OpenAI-format messages to a readable conversation
        text, generates a summary using an LLM, and saves the result to a
        markdown file.

        Args:
            messages (List[OpenAIMessage]): List of OpenAI messages to
                summarize.
            agent_id (str): Identifier for the agent generating the summary.
                (default: :obj:`"agent"`)
            filename (Optional[str]): The base filename (without extension) to
                use for the markdown file. Defaults to a timestamped name when
                not provided.
            summary_prompt (Optional[str]): Custom prompt for the summarizer.
                When omitted, a default prompt highlighting key decisions,
                action items, and open questions is used.
            response_format (Optional[Type[BaseModel]]): A Pydantic model
                defining the expected structure of the response. If provided,
                the summary will be generated as structured output and included
                in the result.
            working_directory (Optional[str|Path]): Optional directory to save
                the markdown summary file. If provided, overrides the default
                directory used by ContextUtility.
            include_summaries (bool): Whether to include previously generated
                summaries in the content to be summarized. If False (default),
                only non-summary messages will be summarized. If True, all
                messages including previous summaries will be summarized
                (full compression). (default: :obj:`False`)
            add_user_messages (bool): Whether add user messages to summary.
                (default: :obj:`True`)

        Returns:
            Dict[str, Any]: A dictionary containing the summary text, file
                path, status message, and optionally structured_summary if
                response_format was provided.
        """
        result: Dict[str, Any] = {
            "summary": "",
            "file_path": None,
            "status": "",
        }

        try:
            # Initialize context utility
            if working_directory is not None:
                context_util = ContextUtility(
                    working_directory=str(working_directory)
                )
            else:
                context_util = ContextUtility()

            if not messages:
                status_message = (
                    "No conversation context available to summarize."
                )
                result["status"] = status_message
                return result

            # Convert messages to conversation text
            conversation_text, user_messages = self._convert_messages_to_text(
                messages, include_summaries
            )

            if not conversation_text:
                status_message = (
                    "Conversation context is empty; skipping summary."
                )
                result["status"] = status_message
                return result

            # Reset agent for fresh summarization
            self.agent.reset()

            # Build prompt
            if summary_prompt:
                prompt_text = (
                    f"{summary_prompt.rstrip()}\n\n"
                    f"AGENT CONVERSATION TO BE SUMMARIZED:\n"
                    f"{conversation_text}"
                )
            else:
                prompt_text = self.build_default_summary_prompt(
                    conversation_text
                )

            try:
                # Use structured output if response_format is provided
                if response_format:
                    response = await self.agent.astep(
                        prompt_text, response_format=response_format
                    )
                else:
                    response = await self.agent.astep(prompt_text)

            except Exception as step_exc:
                error_message = (
                    f"Failed to generate summary using model: {step_exc}"
                )
                logger.error(error_message)
                result["status"] = error_message
                return result

            if not response.msgs:
                status_message = (
                    "Failed to generate summary from model response."
                )
                result["status"] = status_message
                return result

            summary_content = response.msgs[-1].content.strip()
            if not summary_content:
                status_message = "Generated summary is empty."
                result["status"] = status_message
                return result

            # Handle structured output if response_format was provided
            structured_output = None
            if response_format and response.msgs[-1].parsed:
                structured_output = response.msgs[-1].parsed

            # Determine filename: use provided filename, or extract from
            # structured output, or generate timestamp
            if filename:
                base_filename = filename
            elif structured_output and hasattr(
                structured_output, 'task_title'
            ):
                # Use task_title from structured output for filename
                task_title = structured_output.task_title
                clean_title = ContextUtility.sanitize_workflow_filename(
                    task_title
                )
                base_filename = (
                    f"{clean_title}_workflow" if clean_title else "workflow"
                )
            else:
                base_filename = f"context_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}"  # noqa: E501

            base_filename = Path(base_filename).with_suffix("").name

            metadata = context_util.get_session_metadata()
            metadata.update(
                {
                    "agent_id": agent_id,
                    "message_count": len(messages),
                }
            )

            # Convert structured output to custom markdown if present
            if structured_output:
                # Convert structured output to custom markdown
                summary_content = context_util.structured_output_to_markdown(
                    structured_data=structured_output, metadata=metadata
                )
            if add_user_messages:
                summary_content = self._append_user_messages_section(
                    summary_content, user_messages
                )

            # Save the markdown (either custom structured or default)
            save_status = context_util.save_markdown_file(
                base_filename,
                summary_content,
                title="Conversation Summary"
                if not structured_output
                else None,
                metadata=metadata if not structured_output else None,
            )

            file_path = (
                context_util.get_working_directory() / f"{base_filename}.md"
            )

            summary_content = (
                f"[CONTEXT_SUMMARY] The following is a summary of our "
                f"conversation from a previous session: {summary_content}"
            )

            # Prepare result dictionary
            result_dict = {
                "summary": summary_content,
                "file_path": str(file_path),
                "status": save_status,
                "structured_summary": structured_output,
            }

            result.update(result_dict)
            logger.info("Conversation summary saved to %s", file_path)
            return result

        except Exception as exc:
            error_message = f"Failed to summarize conversation context: {exc}"
            logger.error(error_message)
            result["status"] = error_message
            return result
