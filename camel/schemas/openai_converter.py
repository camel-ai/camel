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
from typing import Any, Dict, Optional, Type

from openai import OpenAI
from pydantic import BaseModel

from camel.types import ModelType
from camel.utils import (
    api_keys_required,
)

from .base import BaseConverter
from .prompts import DEFAULT_CONVERTER_PROMPTS


class OpenAISchemaConverter(BaseConverter):
    r"""OpenAISchemaConverter is a class that
    converts a string or a function into a BaseModel schema.

    Args:
        model_type (ModelType, optional): The model type to be used.
            (default: ModelType.GPT_4O_MINI)
        model_config_dict (Optional[Dict[str, Any]], optional): A dictionary
            that will be fed into:obj:`openai.ChatCompletion.create()`. If
            :obj:`None`, :obj:`ChatGPTConfig().as_dict()` will be used.
            (default: :obj:`None`)
        api_key (Optional[str], optional): The API key for authenticating
            with the OpenAI service. (default: :obj:`None`)
        output_schema (Optional[Type[BaseModel]], optional): The expected
            format of the response. (default: :obj:`None`)
        prompt (Optional[str], optional): The prompt to be used.
            (default: :obj:`None`)

    """

    def __init__(
        self,
        model_type: ModelType = ModelType.GPT_4O_MINI,
        model_config_dict: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        output_schema: Optional[Type[BaseModel]] = None,
        prompt: Optional[str] = None,
    ):
        self.model_type = model_type
        self.prompt = prompt or DEFAULT_CONVERTER_PROMPTS
        self.model_config_dict = model_config_dict or {}
        api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._client = OpenAI(
            timeout=60,
            max_retries=3,
            api_key=api_key,
        )
        BaseConverter.__init__(self, output_schema)
        if output_schema is not None:
            self.model_config_dict["response_format"] = output_schema

    @api_keys_required("OPENAI_API_KEY")
    def convert(
        self, content: str, output_schema: Optional[Type[BaseModel]] = None
    ) -> BaseModel:
        """
        Formats the input content into the expected BaseModel

        Args:
            content (str): The content to be formatted.
            output_schema (Optional[Type[BaseModel]], optional):
                The expected format of the response. Defaults to None.

        Returns:
            Optional[BaseModel]: The formatted response.
        """
        if output_schema is not None:
            self.model_config_dict["response_format"] = output_schema

        response = self._client.beta.chat.completions.parse(
            messages=[
                {'role': 'system', 'content': self.prompt},
                {'role': 'user', 'content': content},
            ],
            model=self.model_type,
            **self.model_config_dict,
        )

        message = response.choices[0].message  # type: ignore[union-attr]
        return message.parsed  # type: ignore[return-value]
