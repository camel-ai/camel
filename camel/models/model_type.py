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

from typing import Union

from camel.types import PredefinedModelType


class Modeltype:
    def __init__(self, value: Union[str, PredefinedModelType]) -> None:
        if isinstance(value, PredefinedModelType):
            self.type = value
            self.value = value.value
        elif isinstance(value, str):
            try:
                self.type = PredefinedModelType(value)
            except ValueError:
                self.type = PredefinedModelType.OPEN_SOURCE
            self.value = value
        else:
            raise ValueError(f"Invalid type for _ModelType: {value}")

    def __str__(self):
        return self.value

    def __repr__(self):
        return f"ModelType({self.value})"

    """
    The following properties are duplicated from the PredefinedModelType class.
    This is used to support the autocompletion in IDEs.
    """

    @property
    def value_for_tiktoken(self) -> str:
        r"""Returns the model name for TikToken."""
        return self.type.value_for_tiktoken

    @property
    def is_open_source(self) -> bool:
        r"""Returns whether this type of models is open-source."""
        return self.type.is_open_source

    @property
    def is_openai(self) -> bool:
        r"""Returns whether this type of models is OpenAI-released model."""
        return self.type.is_openai

    @property
    def is_azure_openai(self) -> bool:
        r"""Returns whether this type of models is an OpenAI-released model
        from Azure.
        """
        return self.type.is_azure_openai

    @property
    def is_zhipuai(self) -> bool:
        r"""Returns whether this type of models is Zhipuai-released model."""
        return self.type.is_zhipuai

    @property
    def is_anthropic(self) -> bool:
        r"""Returns whether this type of models is Anthropic-released model."""
        return self.type.is_anthropic

    @property
    def is_groq(self) -> bool:
        r"""Returns whether this type of models is served by Groq."""
        return self.type.is_groq

    @property
    def is_mistral(self) -> bool:
        r"""Returns whether this type of models is served by Mistral."""
        return self.type.is_mistral

    @property
    def is_nvidia(self) -> bool:
        r"""Returns whether this type of models is Nvidia-released model."""
        return self.type.is_nvidia

    @property
    def is_gemini(self) -> bool:
        r"""Returns whether this type of models is Gemini model."""
        return self.type.is_gemini

    @property
    def is_reka(self) -> bool:
        r"""Returns whether this type of models is Reka model."""
        return self.type.is_reka

    @property
    def token_limit(self) -> int:
        r"""Returns the maximum token limit for a given model."""
        return self.type.token_limit

    def validate_model_name(self, model_name: str) -> bool:
        r"""Checks whether the model type and the model name matches.

        Args:
            model_name (str): The name of the model, e.g. "vicuna-7b-v1.5".

        Returns:
            bool: Whether the model type matches the model name.
        """
        return self.type.validate_model_name(model_name)

    """
    The following method will delegate the attribute access to the 
    PredefinedModelType class if the attribute is not found in the _ModelType 
    class.
    """

    def __getattr__(self, attr):
        return getattr(self.type, attr)
