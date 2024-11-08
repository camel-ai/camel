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
from typing import Any, Callable, Dict, Optional, Type, cast

from openai import OpenAI
from pydantic import BaseModel

from camel.types import ModelType
from camel.types.enums import ModelPlatformType
from camel.utils import (
    api_keys_required,
)
from camel.utils import get_format
from camel.models import ModelFactory

from .base import BaseConverter

DEFAULT_CONVERTER_PROMPTS = """
    Extract key entities and attributes from the provided text,
        and convert them into a structured JSON format.
"""


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
        prompt: Optional[str] = DEFAULT_CONVERTER_PROMPTS,
    ):
        self.model_type = model_type
        self.prompt = prompt
        self.model_config_dict = model_config_dict or {}
        api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._client = ModelFactory.create(
            ModelPlatformType.OPENAI,
            model_type,
            api_key=api_key,
        )
        super().__init__()

    @api_keys_required("OPENAI_API_KEY")
    def convert(
        self,
        content: str,
        output_schema: Type[BaseModel] | str | Callable,
    ) -> BaseModel:
        r"""Formats the input content into the expected BaseModel

        Args:
            content (str): The content to be formatted.
            output_schema (Optional[Type[BaseModel]], optional):
                The expected format of the response. Defaults to None.
            prompt (Optional[str], optional): The prompt to be used.

        Returns:
            BaseModel: The formatted response.
        """
        if not isinstance(output_schema, type):
            output_schema = get_format(output_schema)
        elif not issubclass(output_schema, BaseModel):
            raise ValueError(
                f"Expected a BaseModel, got {type(output_schema)}"
            )

        self.model_config_dict["response_format"] = output_schema
        response = self._client.beta.chat.completions.parse(
            messages=[
                {'role': 'system', 'content': self.prompt},
                {'role': 'user', 'content': content},
            ],
            model=self.model_type,
            **self.model_config_dict,
        )

        message = response.choices[0].message

        if not isinstance(message.parsed, BaseModel):
            raise ValueError(
                f"Expected a BaseModel, got {type(message.parsed)}"
            )

        return message.parsed
