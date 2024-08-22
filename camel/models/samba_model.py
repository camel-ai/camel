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
import os
from typing import Any, Dict, List, Optional

from camel.configs import SAMBA_API_PARAMS
from camel.messages import OpenAIMessage
from camel.types import ChatCompletion, ModelType
from camel.utils import (
    BaseTokenCounter,
    OpenAITokenCounter,
    api_keys_required,
)


class SambaModel:
    r"""SambaNova service interface."""

    def __init__(
        self,
        model_type: ModelType,
        model_config_dict: Dict[str, Any],
        api_key: Optional[str] = None,
        token_counter: Optional[BaseTokenCounter] = None,
    ) -> None:
        r"""Constructor for SambaNova backend.

        Args:
            model_type (ModelType): Model for which a backend is created.
                Currently only support `"llama3-405b"`
            api_key (Optional[str]): The API key for authenticating with the
                SambaNova service. (default: :obj:`None`)
            token_counter (Optional[BaseTokenCounter]): Token counter to use
                for the model. If not provided, `OpenAITokenCounter(ModelType.
                GPT_3_5_TURBO)` will be used.
        """
        self.model_type = model_type
        self._api_key = api_key or os.environ.get("SAMBA_API_KEY")
        self._token_counter = token_counter
        self.model_config_dict = model_config_dict
        self.check_model_config()

    @property
    def token_counter(self) -> BaseTokenCounter:
        r"""Initialize the token counter for the model backend.

        Returns:
            BaseTokenCounter: The token counter following the model's
                tokenization style.
        """
        if not self._token_counter:
            self._token_counter = OpenAITokenCounter(ModelType.GPT_3_5_TURBO)
        return self._token_counter

    def check_model_config(self):
        r"""Check whether the model configuration contains any
        unexpected arguments to SambaNova API.

        Raises:
            ValueError: If the model configuration dictionary contains any
                unexpected arguments to SambaNova API.
        """
        for param in self.model_config_dict:
            if param not in SAMBA_API_PARAMS:
                raise ValueError(
                    f"Unexpected argument `{param}` is "
                    "input into SambaNova model backend."
                )

    @api_keys_required("SAMBA_API_KEY")
    def run(self, messages: List[OpenAIMessage]):
        import json

        import requests

        url = "https://mzulfm3ekjd5j3hv.snova.ai/v1/chat/completions"

        headers = {
            "Authorization": f"Basic {self._api_key}",
            "Content-Type": "application/json",
        }

        data = [
            {
                "messages": messages,
                "max_tokens": self.token_limit,
                "stop": ["<|eot_id|>"],
                "model": self.model_type.value,
                "stream": True,
            }
        ]

        response = requests.post(
            url, headers=headers, data=json.dumps(data), stream=True
        )

        # Check for successful response
        if response.status_code != 200:
            return {
                "error": "Request failed",
                "status_code": response.status_code,
                "response_text": response.text,
            }

        result = []
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8').strip()
                # Remove "data: " prefix if it exists
                if line_str.startswith('data: '):
                    line_str = line_str[6:]
                # Handle special end-of-stream marker
                if line_str == '[DONE]':
                    break
                try:
                    # Decode each line as JSON
                    json_data = json.loads(line_str)
                    result.append(json_data)
                except json.JSONDecodeError:
                    # Handle lines that are not valid JSON
                    result.append(
                        {"error": "Failed to decode line", "line": line_str}
                    )

        return self._to_openai_response(result)

    def _to_openai_response(
        self, response: List[Dict[str, Any]]
    ) -> ChatCompletion:
        # Step 1: Combine the content from each chunk
        full_content = ""
        for chunk in response:
            for value in chunk.values():
                for choice in value['choices']:
                    delta_content = choice['delta'].get('content', '')
                    full_content += delta_content

        # Step 2: Create the ChatCompletion object
        # Extract relevant information from the first chunk (assuming uniform
        # chunks)
        first_chunk = response[0]['0']

        choices = [
            {
                'index': 0,  # Assuming a single choice
                'message': {
                    'role': 'assistant',
                    'content': full_content.strip(),
                },
                'finish_reason': response[-1]['0']['choices'][0][
                    'finish_reason'
                ]
                or None,
            }
        ]

        obj = ChatCompletion.construct(
            id=first_chunk['id'],
            choices=choices,
            created=first_chunk['created'],
            model=first_chunk['model'],
            object="chat.completion",
            usage=None,
        )

        return obj

    @property
    def token_limit(self) -> int:
        r"""Returns the maximum token limit for a given model.

        Returns:
            int: The maximum token limit for the given model.
        """
        return (
            self.model_config_dict.get("max_tokens")
            or self.model_type.token_limit
        )

    @property
    def stream(self) -> bool:
        r"""Returns whether the model is in stream mode, which sends partial
        results each time.

        Returns:
            bool: Whether the model is in stream mode.
        """
        return True
