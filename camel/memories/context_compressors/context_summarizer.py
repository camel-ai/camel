# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========

from typing import List, TYPE_CHECKING, Optional

from camel.logger import get_logger

if TYPE_CHECKING:
    from camel.agents import ChatAgent
    from camel.memories.records import MemoryRecord

logger = get_logger(__name__)

class ContextSummarizer:
    r"""Handles the summarization of the conversation context using an AI agent.

    This class takes the conversation history or a list of memory records and
    creates intelligent summaries that preserve important context about work completed.
    It supports iterative summarization by storing previous summaries.

    Args:
        summary_agent (ChatAgent): The agent used to generate the summaries.
    """

    def __init__(self, 
        summary_agent: "ChatAgent",
    ) -> None:
        self.summary_agent = summary_agent
        self.existing_summary: Optional[str] = ""

    def summarize_messages(self, 
        memory_records: List["MemoryRecord"],
    ) -> str:
        r"""Generate a summary of the conversation context.
        
        Args:
            memory_records (List["MemoryRecord"]): A list of memory records to summarize.

        Returns:
            str: The summary of the conversation context.
        """
        if not memory_records:
            logger.warning("No memory records provided. Returning existing summary.")
            return self.existing_summary

        try:
            # 1. format the conversation 
            conversation_text = self._format_conversation(memory_records)

            # 2. create the summary prompt
            summary_prompt = self._create_summary_prompt(conversation_text)

            # 3. generate summary using the agent
            response = self.summary_agent.step(summary_prompt)

            # 4. extract the summary from response and store
            summary_content = response.msgs[-1].content.strip()
            self.existing_summary = summary_content

            logger.info(f"Successfully generated summary for {len(memory_records)} messages.")
            return summary_content
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return self.existing_summary
    
    def _format_conversation(
        self,
        memory_records: List["MemoryRecord"],
    ) -> str:
        r"""Format the conversation into a text string.

        Args:
            memory_records (List["MemoryRecord"]): A list of memory records to format.

        Returns:
            str: The formatted conversation.
        """
        conversation_lines = []

        for record in memory_records:
            role = record.role_at_backend.value if \
                hasattr(record.role_at_backend, 'value')\
                else str(record.role_at_backend)
            content = record.message.content
            conversation_lines.append(f"{role}: {content}")
        
        return "\n".join(conversation_lines)
    
    def _create_summary_prompt(
        self,
        conversation_text: str,
    ) -> str:
        r"""Create a prompt for the summary agent.
        
        Args:
            conversation_text (str): The formatted conversation to summarize.

        Returns:
            str: The complete prompt for summarization.
        """
        
        base_prompt = """The following is a conversation history of a large language model agent.
Analyze it and extract the key information from it. The information will be
passed on to a new agent that will use it to understand the problem and continue
working on it without having to start from scratch. Focus on:
- Tasks that were accomplished
- Tools and methods that were used  
- Key decisions that were made
- Important discoveries or solutions found
- Technical approaches that worked"""

        # if we want to extend an existing summary
        if self.existing_summary:
            base_prompt += f"""

Existing summary from before:
{self.existing_summary}

Provide an updated summary that incorporates both the previous work and the new conversation."""

        prompt = f"""{base_prompt}

Conversation:
{conversation_text}

Summary:"""
        return prompt

    def reset(self) -> None:
        r"""Reset the summarizer by clearing the stored summary."""
        self.existing_summary = None
        logger.info("Context summarizer reset - previous summary cleared")

    def get_current_summary(self) -> Optional[str]:
        r"""Get the current stored summary without generating a new one.
        
        Returns:
            Optional[str]: The current summary, or None if no summary exists.
        """
        return self.existing_summary
    
    def set_summary(self, summary: str) -> None:
        r"""Manually set the current summary.
        
        Args:
            summary (str): The summary to store.
        """
        self.existing_summary = summary
        logger.info("Summary manually set")