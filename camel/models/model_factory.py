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
import os
from typing import Any, ClassVar, Dict, Optional, Type, Union

from camel.models.aihubmix_model import AihubMixModel
from camel.models.aiml_model import AIMLModel
from camel.models.amd_model import AMDModel
from camel.models.anthropic_model import AnthropicModel
from camel.models.aws_bedrock_model import AWSBedrockModel
from camel.models.azure_openai_model import AzureOpenAIModel
from camel.models.base_model import BaseModelBackend
from camel.models.cohere_model import CohereModel
from camel.models.cometapi_model import CometAPIModel
from camel.models.crynux_model import CrynuxModel
from camel.models.deepseek_model import DeepSeekModel
from camel.models.gemini_model import GeminiModel
from camel.models.groq_model import GroqModel
from camel.models.internlm_model import InternLMModel
from camel.models.litellm_model import LiteLLMModel
from camel.models.lmstudio_model import LMStudioModel
from camel.models.minimax_model import MinimaxModel
from camel.models.mistral_model import MistralModel
from camel.models.modelscope_model import ModelScopeModel
from camel.models.moonshot_model import MoonshotModel
from camel.models.nebius_model import NebiusModel
from camel.models.netmind_model import NetmindModel
from camel.models.novita_model import NovitaModel
from camel.models.nvidia_model import NvidiaModel
from camel.models.ollama_model import OllamaModel
from camel.models.openai_compatible_model import OpenAICompatibleModel
from camel.models.openai_model import OpenAIModel
from camel.models.openrouter_model import OpenRouterModel
from camel.models.ppio_model import PPIOModel
from camel.models.qianfan_model import QianfanModel
from camel.models.qwen_model import QwenModel
from camel.models.reka_model import RekaModel
from camel.models.samba_model import SambaModel
from camel.models.sglang_model import SGLangModel
from camel.models.siliconflow_model import SiliconFlowModel
from camel.models.stub_model import StubModel
from camel.models.togetherai_model import TogetherAIModel
from camel.models.vllm_model import VLLMModel
from camel.models.volcano_model import VolcanoModel
from camel.models.watsonx_model import WatsonXModel
from camel.models.yi_model import YiModel
from camel.models.zhipuai_model import ZhipuAIModel
from camel.types import ModelPlatformType, ModelType, UnifiedModelType
from camel.utils import BaseTokenCounter, configure_langfuse


class ModelFactory:
    r"""Factory of backend models.

    Raises:
        ValueError: in case the provided model type is unknown.
    """

    _MODEL_PLATFORM_TO_CLASS_MAP: ClassVar[
        Dict[ModelPlatformType, Type[BaseModelBackend]]
    ] = {
        ModelPlatformType.OLLAMA: OllamaModel,
        ModelPlatformType.VLLM: VLLMModel,
        ModelPlatformType.SGLANG: SGLangModel,
        ModelPlatformType.OPENAI_COMPATIBLE_MODEL: OpenAICompatibleModel,
        ModelPlatformType.SAMBA: SambaModel,
        ModelPlatformType.TOGETHER: TogetherAIModel,
        ModelPlatformType.LITELLM: LiteLLMModel,
        ModelPlatformType.AWS_BEDROCK: AWSBedrockModel,
        ModelPlatformType.NVIDIA: NvidiaModel,
        ModelPlatformType.SILICONFLOW: SiliconFlowModel,
        ModelPlatformType.AMD: AMDModel,
        ModelPlatformType.AIML: AIMLModel,
        ModelPlatformType.VOLCANO: VolcanoModel,
        ModelPlatformType.NETMIND: NetmindModel,
        ModelPlatformType.OPENAI: OpenAIModel,
        ModelPlatformType.AZURE: AzureOpenAIModel,
        ModelPlatformType.ANTHROPIC: AnthropicModel,
        ModelPlatformType.GROQ: GroqModel,
        ModelPlatformType.COMETAPI: CometAPIModel,
        ModelPlatformType.NEBIUS: NebiusModel,
        ModelPlatformType.LMSTUDIO: LMStudioModel,
        ModelPlatformType.MINIMAX: MinimaxModel,
        ModelPlatformType.OPENROUTER: OpenRouterModel,
        ModelPlatformType.ZHIPU: ZhipuAIModel,
        ModelPlatformType.GEMINI: GeminiModel,
        ModelPlatformType.MISTRAL: MistralModel,
        ModelPlatformType.REKA: RekaModel,
        ModelPlatformType.COHERE: CohereModel,
        ModelPlatformType.YI: YiModel,
        ModelPlatformType.QWEN: QwenModel,
        ModelPlatformType.DEEPSEEK: DeepSeekModel,
        ModelPlatformType.PPIO: PPIOModel,
        ModelPlatformType.INTERNLM: InternLMModel,
        ModelPlatformType.MOONSHOT: MoonshotModel,
        ModelPlatformType.MODELSCOPE: ModelScopeModel,
        ModelPlatformType.NOVITA: NovitaModel,
        ModelPlatformType.WATSONX: WatsonXModel,
        ModelPlatformType.QIANFAN: QianfanModel,
        ModelPlatformType.CRYNUX: CrynuxModel,
        ModelPlatformType.AIHUBMIX: AihubMixModel,
    }

    @staticmethod
    def create(
        model_platform: Union[ModelPlatformType, str],
        model_type: Union[ModelType, str, UnifiedModelType],
        model_config_dict: Optional[Dict] = None,
        token_counter: Optional[BaseTokenCounter] = None,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: int = 3,
        client: Optional[Any] = None,
        async_client: Optional[Any] = None,
        **kwargs,
    ) -> BaseModelBackend:
        r"""Creates an instance of `BaseModelBackend` of the specified type.

        Args:
            model_platform (Union[ModelPlatformType, str]): Platform from
                which the model originates. Can be a string or
                ModelPlatformType enum.
            model_type (Union[ModelType, str, UnifiedModelType]): Model for
                which a backend is created. Can be a string, ModelType enum, or
                UnifiedModelType.
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
            max_retries (int, optional): Maximum number of retries
                for API calls. (default: :obj:`3`)
            client (Optional[Any], optional): A custom synchronous client
                instance. Supported by models that use OpenAI-compatible APIs
                . The client should implement the appropriate client interface
                for the platform. (default: :obj:`None`)
            async_client (Optional[Any], optional): A custom asynchronous
                client instance. Supported by models that use OpenAI-compatible
                APIs. The client should implement the appropriate async client
                interface for the platform. (default: :obj:`None`)
            **kwargs: Additional model-specific parameters that will be passed
                to the model constructor. For example, Azure OpenAI models may
                require `api_version`, `azure_deployment_name`,
                `azure_ad_token_provider`, and `azure_ad_token`.

        Returns:
            BaseModelBackend: The initialized backend.

        Raises:
            ValueError: If there is no backend for the model.
        """

        # Auto-configure Langfuse only if explicitly enabled
        env_enabled_str = os.environ.get("LANGFUSE_ENABLED")
        if env_enabled_str and env_enabled_str.lower() == "true":
            configure_langfuse()

        # Convert string to ModelPlatformType enum if needed
        if isinstance(model_platform, str):
            try:
                model_platform = ModelPlatformType(model_platform)
            except ValueError:
                raise ValueError(f"Unknown model platform: {model_platform}")

        # Convert string to ModelType enum or UnifiedModelType if needed
        if isinstance(model_type, str):
            try:
                model_type = ModelType(model_type)
            except ValueError:
                # If not in ModelType, create a UnifiedModelType
                model_type = UnifiedModelType(model_type)

        model_class: Optional[Type[BaseModelBackend]] = None
        model_type = UnifiedModelType(model_type)

        model_class = ModelFactory._MODEL_PLATFORM_TO_CLASS_MAP.get(
            model_platform
        )

        if model_type == ModelType.STUB:
            model_class = StubModel

        if model_class is None:
            raise ValueError(f"Unknown model platform `{model_platform}`")

        # Pass client and async_client via kwargs if provided
        if client is not None:
            kwargs['client'] = client
        if async_client is not None:
            kwargs['async_client'] = async_client

        return model_class(
            model_type=model_type,
            model_config_dict=model_config_dict,
            api_key=api_key,
            url=url,
            token_counter=token_counter,
            timeout=timeout,
            max_retries=max_retries,
            **kwargs,
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
        import yaml

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
