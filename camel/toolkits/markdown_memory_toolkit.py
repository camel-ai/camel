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

import os
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.toolkits.note_taking_toolkit import NoteTakingToolkit
from camel.agents import ChatAgent
from camel.logger import get_logger
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from camel.memories.records import MemoryRecord

logger = get_logger(__name__)

class MarkdownMemoryToolkit(BaseToolkit):
    def __init__(
        self,
        agent: Optional[ChatAgent] = None,
        working_directory: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        r"""Initialize the MarkdownMemoryToolkit.

        Args:
            agent (ChatAgent, optional): The agent to use for the toolkit.
                If not provided, the toolkit will not be able to access the
                agent's memory.
            working_directory (str, optional): The directory path where notes
                will be stored. If not provided, a new unique working
                directory will be created.
            timeout (Optional[float]): The timeout for the toolkit.
        """
        super().__init__(timeout=timeout)
        
        self.agent = agent
        self.session_id = self._generate_session_id()
        self.summary_filename = "summary"
        self.history_filename = "history"

        if working_directory:
            self.working_directory = Path(working_directory).resolve
        else:
            camel_workdir = os.environ.get("CAMEL_WORKDIR")
            if camel_workdir:
                self.working_directory = Path(camel_workdir) / "markdown_memory"
            else:
                self.working_directory = Path("markdown_memory")
        
        self.working_directory = self.working_directory / self.session_id
        self.working_directory.mkdir(parents=True, exist_ok=True)

        # NoteTakingToolkit is used for file operations.
        self._note_taking_toolkit = NoteTakingToolkit(
            working_directory=working_directory,
            timeout=timeout,
        )

    
    def _generate_session_id(self) -> str:
        """Generate a unique session ID for the current session."""
        return datetime.now().strftime("session_%m_%d_%H%M")

    def _save_history(
        self,
        messages:List["MemoryRecord"],
    ) -> str:
        r"""Save the full history of context to a markdown file. 

        Args:
            messages (List[BaseMessage]): The list of messages to save.

        Returns:
            str: Success message or error message.
        """

        # formatting history with metadata
        history_content = f"# Conversation History: {self.session_id}\n\n"
        history_content += f"## Metadata\n\n"
        history_content += f"- Save Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        history_content += f"- Total Messages: {len(messages)}\n"
        history_content += f"## Full Transcript\n\n"

        for i, record in enumerate(messages):
            message = record.message
            role = getattr(message, "role_name", "unknown")
            content = getattr(message, "content", str(message))
            agent_id = record.agent_id or "unknown"
            role_at_backend = record.role_at_backend.value if \
                hasattr(record.role_at_backend, 'value') else \
                    str(record.role_at_backend)

            history_content += f"Message {i+1} - {role} \n"
            history_content += f"Agent ID: {agent_id}  \n"
            history_content += f"Backend Role: {role_at_backend}  \n"
            history_content += f"Content: \n{content}\n\n"
            history_content += f"-----------------------------------\n\n"

        return self._create_note(self.history_filename, history_content)
    
    def _save_summary(
        self,
        content: dict
    ) -> str:
        # TODO: update this to accept a string instead of a dict
        r""" Save a summary of the context in markdown file.

        Args:
            content (str): The content of the summary.

        Returns:
            str: Success message or error message.
        """
        # validate summary structure with warnings (not rigid)
        expected_keys = {'task_description', 'work_completed', 'user_preferences', 'next_steps'}
        provided_keys = set(content.keys())
        
        missing_keys = expected_keys - provided_keys
        if missing_keys:
            logger.warning(f"Summary missing recommended keys: {missing_keys}")
        
        extra_keys = provided_keys - expected_keys
        if extra_keys:
            logger.info(f"Summary contains additional keys: {extra_keys}")
        
        summary_content = f"# Conversation Summary: {self.session_id}\n\n"
        
        # handle keys dynamically 
        for key, value in content.items():
            header = key.replace('_', ' ').title()
            summary_content += f"## {header}\n"
            
            if isinstance(value, list):
                for item in value:
                    summary_content += f"- {item}\n"
            else:
                summary_content += f"{value}\n"
            summary_content += "\n"

        return self._create_note(self.summary_filename, summary_content)

    def _create_note(
        self,
        filename: str,
        content: str,
    ) -> str:
        r""" Create a note in the working directory using NoteTakingToolkit.
        
        Args:
            filename (str): The name of the note.
            content (str): The content of the note.

        Returns:
            str: Success message or error message.
        """
        try:
            self._note_taking_toolkit.create_note(filename, content)
            return f"Successfully created note: {filename}"
        except Exception as e:
            logger.error(f"Error creating note: {e}")
            return f"Error creating note: {e}"
    
    def _load_summary(
        self, 
    ) -> str:
        r""" Load the summary of the context from the markdown file.

        Returns:
            str: The summary in text format.
        """
        try:
            return self._note_taking_toolkit.read_note(self.summary_filename)
        except Exception as e:
            logger.error(f"Error loading summary: {e}")
            return ""
        
    def _load_history(
        self,
    ) -> str:
        r""" Load the history of the context from the markdown file.

        Returns:
            str: The history in text format.
        """
        try:
            return self._note_taking_toolkit.read_note(self.history_filename)
        except Exception as e:
            logger.error(f"Error loading history: {e}")
            return ""

    def save_conversation_memory(
        self,
        summary_notes: dict,
    ) -> str:
        r"""Saves the full history of the conversation and the summary of 
        important information in markdown files. The history can later be
        searched through and the summary can be read by the user. 

        This function must be used when the memory is cluttered with too many
        unrelated conversations or information that might be irrelevant to 
        the core task and goal of the agent.

        The summary is provided by the agent, while the history is retrieved
        from the memory programatically.

        Args:
            summary_notes (dict): The summary of the conversation. The keys 
                are "task_description", "work_completed", "user_preferences", and "next_steps".
                This is a valuable information about the task which can be
                used to guide the agent's future actions.

        Returns:
            str: Success message or error message.
        """
        if self.agent is None:
            raise ValueError("Agent is not provided. Please provide the agent to the toolkit.")
        
        # try to get memory records from the context
        try:
            context_records = self.agent.memory.retrieve()
            memory_records = [cr.memory_record for cr in context_records]
        except Exception as e:
            logger.error(f"Failed to retrieve memory from agent: {e}")
            return f"Error: Could not access agent memory - {e}"
        
        # save history and summary
        summary_saved = self._save_summary(summary_notes)
        history_saved = self._save_history(memory_records)

        if "Error" not in summary_saved and "Error" not in history_saved:
            logger.info(
                f"Conversation memory saved successfully at {self.working_directory}"
            )
            return f"Conversation memory saved successfully at {self.working_directory}"
        else:
            logger.error("Failed to save conversation memory")
            return f"Failed to save conversation memory. Summary: {summary_saved}, History: {history_saved}"

    def get_tools(self) -> List[FunctionTool]:
        r"""Get the tools for the MarkdownMemoryToolkit.

        Returns:
            List[FunctionTool]: The list of tools.
        """
        return [FunctionTool(self.save_conversation_memory)]
    

if __name__ == "__main__":
    from camel.memories.records import MemoryRecord
    from camel.messages.base import BaseMessage
    from camel.types import ModelPlatformType, ModelType

    agent = ChatAgent(
        model = "gpt-4o"
    )


    user_message = BaseMessage.make_user_message(
        role_name="User", content="Hello, how are you?"
    )
    assistant_message = BaseMessage.make_assistant_message(
        role_name="Assistant", content="I'm doing well, thank you!"
    )
    user_message2 = BaseMessage.make_user_message(
        role_name="User", content="Provide me a list of resources"
    )

    messages = [
        MemoryRecord(message=user_message, role_at_backend="user", agent_id="123"),
        MemoryRecord(message=assistant_message, role_at_backend="assistant", agent_id="123"),
        MemoryRecord(message=user_message2, role_at_backend="user", agent_id="123"),
    ]
    markdown_memory_toolkit = MarkdownMemoryToolkit(agent)
    markdown_memory_toolkit._save_history(messages)