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

from typing import Any, Dict, Optional

from pydantic import BaseModel

from camel.models import OpenAIModel
from camel.types import ModelType
from camel.utils import (
    api_keys_required,
)

from .base import BaseStructedModel


class OpenAIStructure(BaseStructedModel):
    def __init__(
        self,
        model_type: ModelType = ModelType.GPT_4O_MINI,
        model_config_dict: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        target: Optional[BaseModel] = None,
        prompt: Optional[str] = None,
    ):
        """
        Initializes the StructuredOpenAIModel class
            with the specified parameters.

        Args:
            model_type (ModelType): The model type to use.
            model_config_dict (Optional[Dict[str, Any]]):
                The model config dict.
            api_key (Optional[str]): The API key to use.
            target (Optional[BaseModel]): The target format.
            prompt (Optional[str]): The prompt to use.
        """
        if model_config_dict is None:
            model_config_dict = {}
        self.model = OpenAIModel(model_type, model_config_dict, api_key)
        BaseStructedModel.__init__(self, target, prompt)

        if target is not None:
            self.model.model_config_dict["response_format"] = target

        self.model._client.chat.completions.create = (  # type: ignore[method-assign]
            self.model._client.beta.chat.completions.parse  # type: ignore[assignment]
        )

    @api_keys_required("OPENAI_API_KEY")
    def structure(
        self, content: str, target: Optional[BaseModel] = None
    ) -> BaseModel:
        """
        Formats the input content into the expected BaseModel

        Args:
            content (str): The content to be formatted.
            target (Optional[BaseModel]):
                The expected format of the response.

        Returns:
            Optional[BaseModel]: The formatted response.
        """
        if target is not None:
            self.model.model_config_dict["response_format"] = target

        completion = self.model.run(
            messages=[
                {'role': 'system', 'content': self.prompt},
                {'role': 'user', 'content': content},
            ]
        )
        message = completion.choices[0].message  # type: ignore[union-attr]
        return message.parsed  # type: ignore[union-attr]
