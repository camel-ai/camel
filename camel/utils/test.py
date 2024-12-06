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
from camel.utils import api_keys_required
from typing import List
import os

# @api_keys_required({'api_key': 'AZURE_OPENAI_API_KEY', 'api_version': 'AZURE_API_VERSION'})
# def __init__(
#     self,
#     model_type: Union[ModelType, str],
#     model_config_dict: Optional[Dict[str, Any]] = None,
#     api_key: Optional[str] = None,
#     url: Optional[str] = None,
#     token_counter: Optional[BaseTokenCounter] = None,
#     api_version: Optional[str] = None,
#     azure_deployment_name: Optional[str] = None,
# ) -> None:
#     if model_config_dict is None:
#         model_config_dict = ChatGPTConfig().as_dict()
#     api_key = api_key or os.environ.get("AZURE_OPENAI_API_KEY")
#     url = url or os.environ.get("AZURE_OPENAI_BASE_URL")

class ExampleClass:
    @api_keys_required(
        [
            ("key_1", 'API_KEY_1'),
            ("api_key_2", 'API_KEY_2'),
        ]
    )
    def __init__(self, messages: List[str], key_1: str = None, api_key_2: str = None):
        self._key1 = key_1 or os.environ.get("API_KEY_1")
        self._key2 = api_key_2 or os.environ.get("API_KEY_2")
        self.messages = messages

    @api_keys_required(
        [
            (None, "API_KEY_3"),
        ]
    )
    def run(self):
        print("API keys validated!")


# Example with API_KEY_1 provided in arguments
obj = ExampleClass(messages=["xx"])
