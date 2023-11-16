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

import logging
from typing import Any, Dict, Optional

class Assistant:

    def __init__(self, assistant_id: str) -> None:
        """
        Initialize the AssistantFile with an assistant ID and
        an optional OpenAI client.

        Args:
            assistant_id: The ID of the assistant.
            client: An instance of the OpenAI client. Optional.

        Example:
            assistant_file = AssistantFile(assistant_id='my-assistant-id')
        """
        self.assistant_id = assistant_id
        self.logger = logging.getLogger(__name__)

    def create_file(self, file_id: str) -> Dict[str, Any]:
        """
        Create an assistant file.

        Args:
            file_id: The ID of the file to attach to the assistant.

        Returns:
            The assistant file object.

        Raises:
            Exception: If creating the assistant file fails.

        Example:
            assistant_file_obj = assistant_file.create_file('file-id')
        """
        try:
            return self.client.beta.assistants.files.create(
                assistant_id=self.assistant_id, file_id=file_id)
        except Exception as e:
            self.logger.error(f"Failed to create file: {e}")
            raise

    def list_files(self, limit: int = 20, order: str = 'desc',
                   after: Optional[str] = None,
                   before: Optional[str] = None) -> Dict[str, Any]:
        """
        List assistant files with various filtering and sorting options.

        Args:
            limit: The number of objects to be returned. Default is 20.
            order: Sort order ('asc' or 'desc'). Default is 'desc'.
            after: Pagination cursor for the next page. Optional.
            before: Pagination cursor for the previous page. Optional.

        Returns:
            A list of assistant file objects.

        Raises:
            Exception: If listing the assistant files fails.

        Example:
            files = assistant_file.list_files(limit=10, order='asc')
        """
        try:
            return self.client.beta.assistants.files.list(
                assistant_id=self.assistant_id, limit=limit, order=order,
                after=after, before=before)
        except Exception as e:
            self.logger.error(f"Failed to list files: {e}")
            raise