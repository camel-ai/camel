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
from typing import Any, Dict, List, Optional, cast

from camel.configs import ANTHROPIC_API_PARAMS_WITH_FUNCTIONS
from camel.messages import OpenAIMessage
from camel.models import BaseModelBackend
from camel.typing import ModelType
from camel.utils import BaseTokenCounter
from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT
from openai.openai_object import OpenAIObject
from anthropic.types import Completion
from camel.utils.token_counting import messages_to_prompt
from colorama import Fore

class AnthropicModel(BaseModelBackend):
    r"""Anthropic API in a unified BaseModelBackend interface."""

    def __init__(self, model_type: ModelType,
                 model_config_dict: Dict[str, Any]) -> None:
        
        super().__init__(model_type, model_config_dict)

        self.client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self._token_counter: Optional[BaseTokenCounter] = None

    def _convert_openai_messages_to_anthropic_prompt(self, messages: List[OpenAIMessage]):
        return messages_to_prompt(messages, self.model_type)
    
    def _convert_response_format_from_anthropic_to_openai(self, response: Completion):
        obj = OpenAIObject.construct_from(dict(
            id=response.log_id,
            object="chat.completion",
            created=0,
            model=response.model,
            choices=[dict(index=0,
                          message={
                              "role": "assistant",
                              "content": response.completion
                          },
                          finish_reason=response.stop_reason
                    )],
            usage={
                "completion_tokens": self.count_tokens_from_anthropic_prompt(response.completion),
            }
        ))
        return obj
    
    @property
    def token_counter(self) -> BaseTokenCounter:
        if not self._token_counter:
            self._token_counter = self.client.get_tokenizer()
        return self._token_counter

    def count_tokens_from_messages(self, messages: List[OpenAIMessage]):
        prompt = self._convert_openai_messages_to_anthropic_prompt(messages)
        return self.count_tokens_from_anthropic_prompt(prompt)
    
    def count_tokens_from_anthropic_prompt(self, prompt):
        return self.client.count_tokens(prompt)

    def run(
        self,
        messages: List[Dict],
    ) -> Dict[str, Any]:
        """
        convert openai format messages to anthropic format prompt
        e.g.
        messages = [{'role': 'system', 'content': 'Hello'},
                    {'role': 'user', 'content': 'world!'}]
        ===> prompt = f"{HUMAN_PROMPT} how does a court case get to the Supreme Court? {AI_PROMPT}""
        """

        prompt = self._convert_openai_messages_to_anthropic_prompt(messages)
        prompt_tokens = self.count_tokens_from_anthropic_prompt(prompt)
        response = self.client.completions.create(model = self.model_type.value,
                                                  prompt = f"{HUMAN_PROMPT} {prompt} {AI_PROMPT}",
                                                  **self.model_config_dict)
        
        # format response to openai object
        response = self._convert_response_format_from_anthropic_to_openai(response)
        response["usage"]["prompt_tokens"] = prompt_tokens
        response["usage"]["total_tokens"] = prompt_tokens + response["usage"]["completion_tokens"]

        return response

    def check_model_config(self):
        r"""Check whether the model configuration is valid for anthropic
        model backends.

        Raises:
            ValueError: If the model configuration dictionary contains any
                unexpected arguments to OpenAI API, or it does not contain
                :obj:`model_path` or :obj:`server_url`.
        """
        for param in self.model_config_dict:
            if param not in ANTHROPIC_API_PARAMS_WITH_FUNCTIONS:
                raise ValueError(f"Unexpected argument `{param}` is "
                                 "input into Anthropic model backend.")

    @property
    def stream(self) -> bool:
        r"""Returns whether the model is in stream mode,
            which sends partial results each time.
        Returns:
            bool: Whether the model is in stream mode.
        """
        return self.model_config_dict.get("stream", False)