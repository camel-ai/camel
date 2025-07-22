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
import os
from datetime import datetime
from typing import List, Optional

import requests

from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.toolkits.note_taking_toolkit import NoteTakingToolkit

TYPE_CHECKING = True
if TYPE_CHECKING:
    from camel.memories.records import MemoryRecord


class MarkdownMemoryToolkit(BaseToolkit):
    def __init__(
        self,
        working_directory: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        r"""Initialize the MarkdownMemoryToolkit.

        Args:
            working_directory (str, optional): The directory path where notes
                will be stored. If not provided, a new unique working
                directory will be created.
            timeout (Optional[float]): The timeout for the toolkit.
        """
        super().__init__(timeout=timeout)
        
        self.session_id = self._generate_session_id()
        self.summary_filename = "summary"
        self.history_filename = "history"

        if working_directory is None:
            working_directory = "MarkdownMemory"

        working_directory = os.path.join(working_directory, self.session_id)
        self.working_directory = working_directory
        
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
    ) -> bool:
        r"""Save the full history of context to a markdown file. 

        Args:
            messages (List[BaseMessage]): The list of messages to save.

        Returns:
            bool: True if the history was saved successfully, False otherwise.
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
    ) -> bool:
        r""" Save a summary of the context in markdown file.

        Args:
            content (dict): The content of the summary.

        Returns:
            bool: True if the summary was saved successfully, False otherwise.
        """
        summary_content = f"#Conversation Summary: {self.session_id}\n\n"

        # Work Completed
        summary_content += f"## Work Completed \n"
        summary_content += f"{content.get('work_completed', 'No description')}\n\n"
        
        # User preferences and knowledge
        summary_content += f"## User Preferences and Knowledge \n"
        summary_content += f"{content.get('user_preferences', 'No description')}\n\n"

        # Next Steps
        summary_content += f"## Next Steps \n"
        summary_content += f"{content.get('next_steps', 'No description')}\n\n"

        return self._create_note(self.summary_filename, summary_content)

    def _create_note(
        self,
        filename: str,
        content: str,
    ) -> bool:
        r""" Create a note in the working directory using NoteTakingToolkit.
        
        Args:
            filename (str): The name of the note.
            content (str): The content of the note.

        Returns:
            bool: True if the note was created successfully, False otherwise.
        """
        try:
            self._note_taking_toolkit.create_note(filename, content)
            return True
        except Exception as e:
            print(f"Error creating note: {e}")
            return False
    
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
            print(f"Error loading summary: {e}")
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
            print(f"Error loading history: {e}")
            return ""

    def save_conversation_memory(
        self,
        summary_notes: str,
        reason: str,
    ) -> bool:
        r"""Saves the full history of the conversation and the summary of the
        work done so far, the information about the user preference, and the 
        plan for the next steps, in markdown files. The history can later be
        searched through and the summary can be read by the user. 

        This function must be used when the memory is cluttered with too many
        unrelated conversations or information that might be irrelevant to 
        the core task and goal of the agent. 

        Args:


        """
    

if __name__ == "__main__":
    from camel.memories.records import MemoryRecord
    from camel.messages.base import BaseMessage

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
    markdown_memory_toolkit = MarkdownMemoryToolkit()
    markdown_memory_toolkit._save_history(messages)