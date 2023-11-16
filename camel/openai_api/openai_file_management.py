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

from camel.openai_api.base_openai_api_client import BaseOpenAIAPIClient
from typing import Any, Dict, List, Optional

class OpenAIFileManagement(BaseOpenAIAPIClient):
    # A wrapper class for the OpenAI file management API.
    
    def list_files(self,
                   purpose: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List files with an optional filter by purpose.

        Args:
            purpose: The purpose of the files to list. Optional.

        Returns:
            A list of file information dictionaries.

        Raises:
            Exception: If the file listing fails.

        Example:
            files = manager.list_files(purpose='fine-tune')
        """
        try:
            return self.client.files.list(purpose=purpose)
        except Exception as e:
            self.logger.error(f"Failed to list files: {e}")
            raise

    def upload_file(self, file_path: str, purpose: str) -> Dict[str, Any]:
        """
        Upload a file for a specific purpose.

        Args:
            file_path: The path to the file to upload.
            purpose: The purpose of the file.

        Returns:
            The uploaded file information.

        Raises:
            Exception: If the file upload fails.

        Example:
            uploaded_file_info = manager.upload_file('/path/to/file.txt',
            'fine-tune')
        """
        try:
            with open(file_path, "rb") as file:
                return self.client.files.create(file=file, purpose=purpose)
        except Exception as e:
            self.logger.error(f"Failed to upload file: {e}")
            raise

    def delete_file(self, file_id: str) -> Dict[str, Any]:
        """
        Delete a file by its ID.

        Args:
            file_id: The ID of the file to delete.

        Returns:
            Deletion status.

        Raises:
            Exception: If the file deletion fails.

        Example:
            deletion_status = manager.delete_file('file-id')
        """
        try:
            return self.client.files.delete(file_id)
        except Exception as e:
            self.logger.error(f"Failed to delete file: {e}")
            raise

    def retrieve_file(self, file_id: str) -> Dict[str, Any]:
        """
        Retrieve information about a specific file by its ID.

        Args:
            file_id: The ID of the file to retrieve.

        Returns:
            The file information.

        Raises:
            Exception: If the file retrieval fails.

        Example:
            file_info = manager.retrieve_file('file-id')
        """
        try:
            return self.client.files.retrieve(file_id)
        except Exception as e:
            self.logger.error(f"Failed to retrieve file: {e}")
            raise

    def retrieve_file_content(self, file_id: str) -> Any:
        """
        Retrieve the content of a specific file by its ID.

        Args:
            file_id: The ID of the file whose content is to be retrieved.

        Returns:
            The file content.

        Raises:
            Exception: If the file content retrieval fails.

        Example:
            file_content = manager.retrieve_file_content('file-id')
        """
        try:
            return self.client.files.content(file_id)
        except Exception as e:
            self.logger.error(f"Failed to retrieve file content: {e}")
            raise