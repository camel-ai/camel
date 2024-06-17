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
from camel.models import BaseModelBackend
from camel.messages import ContentsType
from camel.types import ModelType, GenerateContentResponse
from camel.configs import Gemini_API_PARAMS
from typing import Any, Dict, List, Optional, Union
import google.generativeai as genai
from camel.utils import (
    BaseTokenCounter,
    GeminiTokenCounter,
    model_api_key_required,
)

class GeminiModel(BaseModelBackend):
    r"""Gemini API in a unified BaseModelBackend interface."""
    def __init__(
        self, 
        model_type: ModelType, 
        model_config_dict: Optional[Dict[str, Any]] = {},
        api_key: Optional[str] = None,
    ) -> None:
        r"""Constructor for Gemini backend.

        Args:
            model_type (ModelType): Model for which a backend is created,
                Gemini-1.5-flash or Gemini-1.5-pro.
            model_config_dict (Dict[str, Any]): A dictionary that will
                be fed into generate_content().
            api_key (Optional[str]): The API key for authenticating with the
                gemini service. (default: :obj:`None`)
        """
        super().__init__(model_type, model_config_dict, api_key)
        self._api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        genai.configure(api_key = self._api_key)
        if model_type.value not in ['gemini-1.5-flash', 'gemini-1.5-pro']:
            raise ValueError("model_type can only be set to gemini-1.5-flash or gemini-1.5-pro")
        self._client = genai.GenerativeModel(model_type.value)
        self._token_counter: Optional[BaseTokenCounter] = None


    @property
    def token_counter(self) -> BaseTokenCounter:
        if not self._token_counter:
            self._token_counter = GeminiTokenCounter(self._client)
        return self._token_counter
    
    @model_api_key_required
    def run(
        self,
        contents : ContentsType
    ) -> GenerateContentResponse:
        r"""Runs inference of Gemini model.
        This method can handle multimodal input

        Args:
            contents: Message list or Message with the chat history
            in Gemini API format.
            example: contents = [{'role':'user', 'parts': ['hello']}]
            

        Returns: 
            response(GenerateContentResponse)

        If it is not in streaming mode, you can directly output the response.text.

        If it is in streaming mode, you can iterate over the response chunks as they become available.
        """
        response = self._client.generate_content(
            contents = contents,
            **self.model_config_dict,
        )
        return response
    
    def check_model_config(self):
        r"""Check whether the model configuration contains any
        unexpected arguments to Gemini API.

        Raises:
            ValueError: If the model configuration dictionary contains any
                unexpected arguments to OpenAI API.
        """
        if self.model_config_dict != None:
            for param in self.model_config_dict:
                if param not in Gemini_API_PARAMS:
                        raise ValueError(
                        f"Unexpected argument `{param}` is "
                        "input into Gemini model backend."
                    )
    
    @property
    def stream(self) -> bool:
        r"""Returns whether the model is in stream mode,
            which sends partial results each time.
        Returns:
            bool: Whether the model is in stream mode.
        """
        return self.model_config_dict.get('stream', False)