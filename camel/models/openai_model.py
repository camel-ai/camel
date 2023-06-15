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
from typing import Any, Dict, List

from camel.messages import OpenAIMessage
from camel.typing import ModelType

from .base_model import BaseModel


class OpenAIModel(BaseModel):
    r"""OpenAI API in a unified BaseModel interface."""

    def __init__(self, model_type: ModelType,
                 model_config_dict: Dict[str, Any]) -> None:
        r"""Constructor for OpenAI backend.

        Args:
            model_type (ModelType): Model for which a backend is created,
                one of GPT_* series.
            model_config_dict (Dict[str, Any]): a dictionary that will
                be fed into openai.ChatCompletion.create().
        """
        super().__init__()
        self.model_type = model_type
        self.model_config_dict = model_config_dict

    def run(self, messages: List[OpenAIMessage]) -> Dict[str, Any]:
        r"""Run inference of OpenAI chat completion.

        Args:
            messages (List[Dict]): message list with the chat history
                in OpenAI API format.

        Returns:
            Dict[str, Any]: Response in the OpenAI API format.
        """
        import openai
        response = openai.ChatCompletion.create(messages=messages,
                                                model=self.model_type.value,
                                                **self.model_config_dict)
        if not isinstance(response, Dict):
            raise RuntimeError("Unexpected return from OpenAI API")
        return response
