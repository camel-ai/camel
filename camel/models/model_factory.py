# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
import json
from typing import Dict, Optional, Type, Union

import yaml

from camel.models.aiml_model import AIMLModel
from camel.models.anthropic_model import AnthropicModel
from camel.models.azure_openai_model import AzureOpenAIModel
from camel.models.base_model import BaseModelBackend
from camel.models.cohere_model import CohereModel
from camel.models.deepseek_model import DeepSeekModel
from camel.models.gemini_model import GeminiModel
from camel.models.groq_model import GroqModel
from camel.models.internlm_model import InternLMModel
from camel.models.litellm_model import LiteLLMModel
from camel.models.mistral_model import MistralModel
from camel.models.modelscope_model import ModelScopeModel
from camel.models.moonshot_model import MoonshotModel
from camel.models.nvidia_model import NvidiaModel
from camel.models.ollama_model import OllamaModel
from camel.models.openai_compatible_model import OpenAICompatibleModel
from camel.models.openai_model import OpenAIModel
from camel.models.openrouter_model import OpenRouterModel
from camel.models.qwen_model import QwenModel
from camel.models.reka_model import RekaModel
from camel.models.samba_model import SambaModel
from camel.models.sglang_model import SGLangModel
from camel.models.siliconflow_model import SiliconFlowModel
from camel.models.stub_model import StubModel
from camel.models.togetherai_model import TogetherAIModel
from camel.models.vllm_model import VLLMModel
from camel.models.volcano_model import VolcanoModel
from camel.models.yi_model import YiModel
from camel.models.zhipuai_model import ZhipuAIModel
from camel.types import ModelPlatformType, ModelType, UnifiedModelType
from camel.utils import BaseTokenCounter


class ModelFactory:
    r"""Factory of backend models.

    Raises:
        ValueError: in case the provided model type is unknown.
    """

    @staticmethod
    def create(
        model_platform: ModelPlatformType,
        model_type: Union[ModelType, str],
        model_config_dict: Optional[Dict] = None,
        token_counter: Optional[BaseTokenCounter] = None,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> BaseModelBackend:
        r"""Creates an instance of `BaseModelBackend` of the specified type.

        Args:
            model_platform (ModelPlatformType): Platform from which the model
                originates.
            model_type (Union[ModelType, str]): Model for which a
                backend is created. Can be a `str` for open source platforms.
            model_config_dict (Optional[Dict]): A dictionary that will be fed
                into the backend constructor. (default: :obj:`None`)
            token_counter (Optional[BaseTokenCounter], optional): Token
                counter to use for the model. If not provided,
                :obj:`OpenAITokenCounter(ModelType.GPT_4O_MINI)`
                will be used if the model platform didn't provide official
                token counter. (default: :obj:`None`)
            api_key (Optional[str], optional): The API key for authenticating
                with the model service. (default: :obj:`None`)
            url (Optional[str], optional): The url to the model service.
                (default: :obj:`None`)
            timeout (Optional[float], optional): The timeout value in seconds
                for API calls. (default: :obj:`None`)

        Returns:
            BaseModelBackend: The initialized backend.

        Raises:
            ValueError: If there is no backend for the model.
        """
        model_class: Optional[Type[BaseModelBackend]] = None
        model_type = UnifiedModelType(model_type)

        if model_platform.is_ollama:
            model_class = OllamaModel
        elif model_platform.is_vllm:
            model_class = VLLMModel
        elif model_platform.is_sglang:
            model_class = SGLangModel
        elif model_platform.is_openai_compatible_model:
            model_class = OpenAICompatibleModel
        elif model_platform.is_samba:
            model_class = SambaModel
        elif model_platform.is_together:
            model_class = TogetherAIModel
        elif model_platform.is_litellm:
            model_class = LiteLLMModel
        elif model_platform.is_nvidia:
            model_class = NvidiaModel
        elif model_platform.is_siliconflow:
            model_class = SiliconFlowModel
        elif model_platform.is_aiml:
            model_class = AIMLModel
        elif model_platform.is_volcano:
            model_class = VolcanoModel

        elif model_platform.is_openai and model_type.is_openai:
            model_class = OpenAIModel
        elif model_platform.is_azure and model_type.is_azure_openai:
            model_class = AzureOpenAIModel
        elif model_platform.is_anthropic and model_type.is_anthropic:
            model_class = AnthropicModel
        elif model_platform.is_groq and model_type.is_groq:
            model_class = GroqModel
        elif model_platform.is_openrouter and model_type.is_openrouter:
            model_class = OpenRouterModel
        elif model_platform.is_zhipuai and model_type.is_zhipuai:
            model_class = ZhipuAIModel
        elif model_platform.is_gemini and model_type.is_gemini:
            model_class = GeminiModel
        elif model_platform.is_mistral and model_type.is_mistral:
            model_class = MistralModel
        elif model_platform.is_reka and model_type.is_reka:
            model_class = RekaModel
        elif model_platform.is_cohere and model_type.is_cohere:
            model_class = CohereModel
        elif model_platform.is_yi and model_type.is_yi:
            model_class = YiModel
        elif model_platform.is_qwen and model_type.is_qwen:
            model_class = QwenModel
        elif model_platform.is_deepseek:
            model_class = DeepSeekModel
        elif model_platform.is_internlm and model_type.is_internlm:
            model_class = InternLMModel
        elif model_platform.is_moonshot and model_type.is_moonshot:
            model_class = MoonshotModel
        elif model_platform.is_modelscope:
            model_class = ModelScopeModel
        elif model_type == ModelType.STUB:
            model_class = StubModel

        if model_class is None:
            raise ValueError(
                f"Unknown pair of model platform `{model_platform}` "
                f"and model type `{model_type}`."
            )

        return model_class(
            model_type=model_type,
            model_config_dict=model_config_dict,
            api_key=api_key,
            url=url,
            token_counter=token_counter,
            timeout=timeout,
        )

    @classmethod
    def __parse_model_platform(
        cls, model_platform_str: str
    ) -> ModelPlatformType:
        r"""Parses a string and returns the corresponding ModelPlatformType
        enum.

        Args:
            model_platform_str (str): The platform name as a string. Can be in
                the form "ModelPlatformType.<NAME>" or simply "<NAME>".

        Returns:
            ModelPlatformType: The matching enum value.

        Raises:
            ValueError: If the platform name is not a valid member of
                ModelPlatformType.
        """

        try:
            if model_platform_str.startswith("ModelPlatformType."):
                platform_name = model_platform_str.split('.')[-1]
            else:
                platform_name = model_platform_str.upper()

            if platform_name not in ModelPlatformType.__members__:
                raise ValueError(
                    f"Invalid model platform: {platform_name}. "
                    f"Valid options: "
                    f"{', '.join(ModelPlatformType.__members__.keys())}"
                )

            return ModelPlatformType[platform_name]

        except KeyError:
            raise KeyError(f"Invalid model platform: {model_platform_str}")

    @classmethod
    def __load_yaml(cls, filepath: str) -> Dict:
        r"""Loads and parses a YAML file into a dictionary.

        Args:
            filepath (str): Path to the YAML configuration file.

        Returns:
            Dict: The parsed YAML content as a dictionary.
        """
        with open(filepath, 'r') as file:
            config = yaml.safe_load(file)

        return config

    @classmethod
    def __load_json(cls, filepath: str) -> Dict:
        r"""Loads and parses a JSON file into a dictionary.

        Args:
            filepath (str): Path to the JSON configuration file.

        Returns:
            Dict: The parsed JSON content as a dictionary.
        """
        with open(filepath, 'r') as file:
            config = json.load(file)

        return config

    @classmethod
    def create_from_yaml(cls, filepath: str) -> BaseModelBackend:
        r"""Creates and returns a model base backend instance
        from a YAML configuration file.

        Args:
            filepath (str): Path to the YAML file containing model
                configuration.

        Returns:
            BaseModelBackend: An instance of the model backend based on the
                configuration.
        """

        config = cls.__load_yaml(filepath)
        config["model_platform"] = cls.__parse_model_platform(
            config["model_platform"]
        )

        model = ModelFactory.create(**config)

        return model

    @classmethod
    def create_from_json(cls, filepath: str) -> BaseModelBackend:
        r"""Creates and returns a base model backend instance
        from a JSON configuration file.

        Args:
            filepath (str): Path to the JSON file containing model
                configuration.

        Returns:
            BaseModelBackend: An instance of the model backend based on the
                configuration.
        """

        config = cls.__load_json(filepath)
        config["model_platform"] = cls.__parse_model_platform(
            config["model_platform"]
        )

        model = ModelFactory.create(**config)

        return model
