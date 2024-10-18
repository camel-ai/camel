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
    BaseTokenCounter,
    api_keys_required,
)

from .base import BaseStructedModel


class OpenAIStructure(OpenAIModel, BaseStructedModel):
    def __init__(
        self,
        model_type: ModelType,
        model_config_dict: Dict[str, Any],
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        token_counter: Optional[BaseTokenCounter] = None,
        output_format: Optional[BaseModel] = None,
        prompt: Optional[str] = None,
    ):
        """
        Initializes the StructuredOpenAIModel class
            with the specified parameters.

        Args:
            model_type (ModelType):
                Type of the model to be used.
            model_config_dict (Dict[str, Any]):
                Dictionary containing model configuration parameters.
            api_key (Optional[str]):
                API key for authenticating the requests. Defaults to None.
            url (Optional[str]):
                URL endpoint for the model API. Defaults to None.
            token_counter (Optional[BaseTokenCounter]):
                Counter for tracking token usage. Defaults to None.
            output_format (Optional[BaseModel]):
                Expected format of the response. Defaults to None.
            prompt (Optional[str]):
                Prompt to be used for the model. Defaults to None.
        """
        OpenAIModel.__init__(
            self, model_type, model_config_dict, api_key, url, token_counter
        )
        BaseStructedModel.__init__(self, output_format, prompt)

        if output_format is not None:
            self.model_config_dict["response_format"] = output_format

        self._client.chat.completions.create = (  # type: ignore[method-assign]
            self._client.beta.chat.completions.parse  # type: ignore[assignment]
        )

    @api_keys_required("OPENAI_API_KEY")
    def structure(
        self, content: str, output_format: Optional[BaseModel] = None
    ) -> BaseModel:
        """
        Formats the input content into the expected BaseModel

        Args:
            content (str): The content to be formatted.
            output_format (Optional[BaseModel]):
                The expected format of the response.

        Returns:
            Optional[BaseModel]: The formatted response.
        """
        if output_format is not None:
            self.model_config_dict["response_format"] = output_format

        completion = self.run(
            messages=[
                {'role': 'system', 'content': self.prompt},
                {'role': 'user', 'content': content},
            ]
        )
        message = completion.choices[0].message  # type: ignore[union-attr]
        return message.parsed  # type: ignore[union-attr]
