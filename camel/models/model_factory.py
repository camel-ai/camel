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
from typing import Any, Dict, Optional, Union

from camel.models.anthropic_model import AnthropicModel
from camel.models.base_model import BaseModelBackend
from camel.models.gemini_model import GeminiModel
from camel.models.litellm_model import LiteLLMModel
from camel.models.ollama_model import OllamaModel
from camel.models.open_source_model import OpenSourceModel
from camel.models.openai_model import OpenAIModel
from camel.models.stub_model import StubModel
from camel.models.zhipuai_model import ZhipuAIModel
from camel.types import ModelPlatformType, ModelType


class ModelFactory:
    r"""Factory of backend models.

    Raises:
        ValueError: in case the provided model type is unknown.
    """

    @staticmethod
    def create(
        model_platform: ModelPlatformType,
        model_type: Union[ModelType, str],
        model_config_dict: Dict,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
    ) -> BaseModelBackend:
        r"""Creates an instance of `BaseModelBackend` of the specified type.

        Args:
            model_platform (ModelPlatformType): Platform from which the model
                originates.
            model_type (Union[ModelType, str]): Model for which a backend is
                created can be a `str` for open source platforms.
            model_config_dict (Dict): A dictionary that will be fed into
                the backend constructor.
            api_key (Optional[str]): The API key for authenticating with the
                model service.
            url (Optional[str]): The url to the model service.

        Raises:
            ValueError: If there is not backend for the model.

        Returns:
            BaseModelBackend: The initialized backend.
        """
        model_class: Any
        if isinstance(model_type, ModelType):
            if model_platform.is_open_source and model_type.is_open_source:
                model_class = OpenSourceModel
                return model_class(model_type, model_config_dict, url)
            if model_platform.is_openai and model_type.is_openai:
                model_class = OpenAIModel
            elif model_platform.is_anthropic and model_type.is_anthropic:
                model_class = AnthropicModel
            elif model_platform.is_zhipuai and model_type.is_zhipuai:
                model_class = ZhipuAIModel
            elif model_platform.is_gemini and model_type.is_gemini:
                model_class = GeminiModel
            elif model_type == ModelType.STUB:
                model_class = StubModel
            else:
                raise ValueError(
                    f"Unknown pair of model platform `{model_platform}` "
                    f"and model type `{model_type}`."
                )
        elif isinstance(model_type, str):
            if model_platform.is_ollama:
                model_class = OllamaModel
                return model_class(model_type, model_config_dict, url)
            elif model_platform.is_litellm:
                model_class = LiteLLMModel
            else:
                raise ValueError(
                    f"Unknown pair of model platform `{model_platform}` "
                    f"and model type `{model_type}`."
                )
        else:
            raise ValueError(f"Invalid model type `{model_type}` provided.")
        return model_class(model_type, model_config_dict, api_key, url)
