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
from typing import List, Optional

from openai.types.beta import Assistant, AssistantDeleted, assistant_create_params
from openai.types.beta.assistants import AssistantFile, FileDeleteResponse, file_list_params, file_create_params
from openai.pagination import SyncCursorPage

from camel.openai_api.openai_file_management import OpenAIFileManagement
from camel.types.enums import ModelType

class OpenAIManager(OpenAIFileManagement):
# A wrapper class for the overall openAI API, including file, assistant, and thread management

    def create_assistant(self, name: str, model: str, file_ids: Optional[List[str]], instructions: Optional[str], tools: List[assistant_create_params.Tool], description: Optional[str]) -> Assistant:
        """
        Args:
            name: The name of the assistant. The maximum length is 256 characters.

            model: ID of the model to use. You can use the
              [List models](https://platform.openai.com/docs/api-reference/models/list) API to
              see all of your available models, or see our
              [Model overview](https://platform.openai.com/docs/models/overview) for
              descriptions of them.

            file_ids: A list of [file](https://platform.openai.com/docs/api-reference/files) IDs
              attached to this assistant. There can be a maximum of 20 files attached to the
              assistant. Files are ordered by their creation date in ascending order.

            instructions: The system instructions that the assistant uses. The maximum length is 32768
              characters.
              
            tools: A list of tool enabled on the assistant. There can be a maximum of 128 tools per
              assistant. Tools can be of types `code_interpreter`, `retrieval`, or `function`.

            description: The description of the assistant. The maximum length is 512 characters.

        Returns:
            The assistant object.
            """
        try:
            return self.client.beta.assistants.create(
                name=name, description=description, file_ids=file_ids, instructions=instructions, model=model.value, tools=tools)
        except Exception as e:
            self.logger.error(f"Failed to create assistant: {e}")
            raise

    def update_assistant(self, name: str, assistant_id: str, description: Optional[str], instructions: Optional[str], file_ids: Optional[List[str]], tools: Optional[List[assistant_create_params.Tool]]) -> Assistant:
        """
        Args: See create_assistant above for details
        Returns:
            The assistant object.
        """
        try:
            return self.client.beta.assistants.update(assistant_id=assistant_id, name=name, description=description, instructions=instructions, file_ids=file_ids, tools=tools)
        except Exception as e:
            self.logger.error(f"Failed to update assistant: {e}")
            raise

    def list_assistants(self) -> SyncCursorPage[Assistant]:
        """
        Returns:
            A list of assistant objects.
        """
        try:
            return self.client.beta.assistants.list()
        except Exception as e:
            self.logger.error(f"Failed to list assistants: {e}")
            raise

    def retrieve_assitant(self, assistant_id: str) -> Assistant:
        """
        Args:
            assistant_id: The ID of the assistant to retrieve
        Returns:
            The assistant object.
        """
        try:
            return self.client.beta.assistants.retrieve(assistant_id=assistant_id)
        except Exception as e:
            self.logger.error(f"Failed to retrieve assistant: {e}")
            raise

    def delete_assistant(self, assistant_id: str) -> AssistantDeleted:
        """
        Args:
            assistant_id: The ID of the assistant to delete
        Returns:
            The assistant object.
        """
        try:
            return self.client.beta.assistants.delete(assistant_id=assistant_id)
        except Exception as e:
            self.logger.error(f"Failed to delete assistant: {e}")
            raise

############################################################################################################
# Assistant File Management
############################################################################################################

    def create_assistant_file(self, file_id: str, assistant_id: str) -> AssistantFile:
        """
        Args:
            file: The ID of the file to attach to the assistant
            assistant_id: The ID of the assistant to attach the file to
        Returns:
            The assistant object.
        """
        try:
            return self.client.beta.assistants.files.create(assistant_id=assistant_id, file_id=file_id)
        except Exception as e:
            self.logger.error(f"Failed to create assistant file: {e}")
            raise

    def retrieve_assistant_file(self, file_id: str, assistant_id: str) -> AssistantFile:
        """
        Args:
            file_id: The ID of the file to retrieve
            assistant_id: The ID of the assistant to retrieve the file from
        Returns:
            The assistant file object.
        """
        try:
            return self.client.beta.assistants.files.retrieve(assistant_id=assistant_id, file_id=file_id)
        except Exception as e:
            self.logger.error(f"Failed to retrieve assistant file: {e}")
            raise
    
    def list_assistant_files(self, assistant_id: str) -> SyncCursorPage[AssistantFile]:
        """
        Args:
            assistant_id: The ID of the assistant to list files from
        Returns:
            A list of files attached to the assistant
        """
        try:
            return self.client.beta.assistants.files.list(assistant_id=assistant_id)
        except Exception as e:
            self.logger.error(f"Failed to list assistant files: {e}")
            raise

    def delete_assistant_file(self, file_id: str, assistant_id: str) -> FileDeleteResponse:
        """
        Args:
            file_id: The ID of the file to delete
            assistant_id: The ID of the assistant to delete the file from
        Returns:
            The assistant file object.
        """
        try:
            return self.client.beta.assistants.files.delete(assistant_id=assistant_id, file_id=file_id)
        except Exception as e:
            self.logger.error(f"Failed to delete assistant file: {e}")
            raise
