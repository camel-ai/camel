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
from camel.openai_api.openai_file_management import OpenAIFileManagement
from openai.types.beta import Assistant, AssistantDeleted, assistant_create_params
from typing import Any, Dict, List, Optional
from camel.types.enums import ModelType

class OpenAIManager(OpenAIFileManagement):
# A wrapper class for the overall openAI API, including file, assistant, and thread management
    def create_assistant(self, name: str, model: ModelType, file_ids: Optional[List[str]], instructions: Optional[str], tools: List[assistant_create_params.Tool], description: Optional[str]) -> Assistant:
        """
        Create an assistant with a model and instructions.

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

        Raises:
            Exception: If creating the assistant fails.
        """
        try:
            return self.client.beta.assistants.create(
                name=name, description=description, file_ids=file_ids, instructions=instructions, model=model.value, tools=tools)
        except Exception as e:
            self.logger.error(f"Failed to create assistant: {e}")
            raise
