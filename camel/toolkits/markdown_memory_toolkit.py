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

from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.memories.context_compressors.context_summarizer import ContextCompressionService
from camel.logger import get_logger
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from camel.agents import ChatAgent

logger = get_logger(__name__)

class MarkdownMemoryToolkit(BaseToolkit):
    r"""A toolkit that provides memory storage in Markdown files for agents.
    With this toolkit, agents can save and manage their conversation 
    memory using markdown files.
    """

    def __init__(
        self,
        agent: "ChatAgent",
        working_directory: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        r"""Initialize the MarkdownMemoryToolkit.

        Args:
            agent (ChatAgent): The agent to use for the toolkit.
                This is required to access the agent's memory.
            working_directory (str, optional): The directory path where notes
                will be stored. If not provided, a default directory will be used.
            timeout (Optional[float]): The timeout for the toolkit.
        """
        super().__init__(timeout=timeout)
        
        self.agent = agent
        self.working_directory = working_directory
        
        # Initialize the context compression service
        self.compression_service = ContextCompressionService(
            summary_agent=self.agent,
            working_directory=self.working_directory,
        )

    def save_conversation_memory(self) -> str:
        r"""Save the conversation history and generate an intelligent summary.
        
        This function should be used when the memory becomes cluttered with too many
        unrelated conversations or information that might be irrelevant to 
        the core task. It will generate a summary and save both the summary 
        and full conversation history to markdown files. Finally, it replaces
        the memory with the new summary for a context refresh.

        Returns:
            str: Success message with brief summary, or error message.
        """
        try:
            # Get memory records from the agent
            context_records = self.agent.memory.retrieve()
            memory_records = [cr.memory_record for cr in context_records]
            
            if not memory_records:
                return "No conversation history found to save."
            
            # Use the compression service to handle the full pipeline
            summary = self.compression_service.compress_and_save(memory_records)
            
            # Create concise success message
            summary_preview = summary[:100] + "..." if len(summary) > 100 else summary
            
            success_msg = (
                f"Memory saved successfully to {self.compression_service.working_directory.name}\n"
                f"Messages saved: {len(memory_records)}\n"
                f"Summary: {summary_preview}"
            )
            
            logger.info("Conversation memory saved successfully")
            return success_msg
            
        except Exception as e:
            error_msg = f"Failed to save conversation memory: {e}"
            logger.error(error_msg)
            return error_msg

    def load_memory_context(self) -> str:
        r"""Load the saved summary to restore previous context.
        
        This function loads the previously saved summary file to help the agent
        understand the prior conversation context without loading the full history.

        Returns:
            str: The loaded summary content, or message if no summary found.
        """
        try:
            summary_content = self.compression_service.load_summary()
            
            if summary_content.strip():
                return f"Previous context loaded:\n\n{summary_content}"
            else:
                return "No previous summary found to load."
                
        except Exception as e:
            error_msg = f"Failed to load memory context: {e}"
            logger.error(error_msg)
            return error_msg

    def get_memory_info(self) -> str:
        r"""Get information about the current memory state and saved files.
        
        Returns:
            str: Information about current memory and saved files.
        """
        try:
            # Current memory info
            current_records = self.agent.memory.retrieve()
            current_count = len(current_records)
            
            info_msg = f"Current messages in memory: {current_count}\n"
            info_msg += f"Save directory: {self.compression_service.working_directory}\n"
            
            # Check if saved files exist
            try:
                summary_content = self.compression_service.load_summary()
                history_content = self.compression_service.load_history()
                
                if summary_content.strip():
                    info_msg += f"Summary file: Available ({len(summary_content)} chars)\n"
                else:
                    info_msg += f"Summary file: Not found\n"
                    
                if history_content.strip():
                    info_msg += f"History file: Available ({len(history_content)} chars)\n"
                else:
                    info_msg += f"History file: Not found\n"
                    
            except Exception:
                info_msg += f"Saved files: Unable to check\n"
            
            return info_msg
            
        except Exception as e:
            error_msg = f"Failed to get memory info: {e}"
            logger.error(error_msg)
            return error_msg

    def get_tools(self) -> List[FunctionTool]:
        r"""Get the tools for the MarkdownMemoryToolkit.

        Returns:
            List[FunctionTool]: The list of tools.
        """
        return [
            FunctionTool(self.save_conversation_memory),
            FunctionTool(self.load_memory_context),
            FunctionTool(self.get_memory_info),
        ]