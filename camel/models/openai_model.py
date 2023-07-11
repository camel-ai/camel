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
from types import GeneratorType
from typing import Any, Dict, List

from camel.messages import OpenAIMessage
from camel.models import BaseModelBackend
from camel.typing import ModelType


class OpenAIModel(BaseModelBackend):
    r"""OpenAI API in a unified BaseModelBackend interface."""

    def __init__(self, model_type: ModelType,
                 model_config_dict: Dict[str, Any]) -> None:
        r"""Constructor for OpenAI backend.

        Args:
            model_type (ModelType): Model for which a backend is created,
                one of GPT_* series.
            model_config_dict (Dict[str, Any]): A dictionary that will
                be fed into openai.ChatCompletion.create().
        """
        super().__init__(model_type, model_config_dict)

    def run(
        self,
        messages: List[Dict],
    ) -> Dict[str, Any]:
        r"""Run inference of OpenAI chat completion.

        Args:
            messages (List[Dict]): Message list with the chat history
                in OpenAI API format.

        Returns:
            Dict[str, Any]: Response in the OpenAI API format.
        """
        import openai
        messages_openai: List[OpenAIMessage] = messages
        response = openai.ChatCompletion.create(messages=messages_openai,
                                                model=self.model_type.value,
                                                **self.model_config_dict)
        if not self.stream:
            if not isinstance(response, Dict):
                raise RuntimeError("Unexpected batch return from OpenAI API")
        else:
            if not isinstance(response, GeneratorType):
                raise RuntimeError("Unexpected stream return from OpenAI API")
        return response

    @property
    def stream(self) -> bool:
        r"""Returns whether the model is in stream mode,
            which sends partial results each time.
        Returns:
            bool: Whether the model is in stream mode.
        """
        return self.model_config_dict.get('stream', False)
