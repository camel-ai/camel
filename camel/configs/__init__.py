# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
from .aihubmix_config import AIHUBMIX_API_PARAMS, AihubMixConfig
from .aiml_config import AIML_API_PARAMS, AIMLConfig
from .amd_config import AMD_API_PARAMS, AMDConfig
from .anthropic_config import ANTHROPIC_API_PARAMS, AnthropicConfig
from .atlascloud_config import ATLASCLOUD_API_PARAMS, AtlasCloudConfig
from .base_config import BaseConfig
from .bedrock_config import BEDROCK_API_PARAMS, BedrockConfig
from .cerebras_config import CEREBRAS_API_PARAMS, CerebrasConfig
from .cohere_config import COHERE_API_PARAMS, CohereConfig
from .cometapi_config import COMETAPI_API_PARAMS, CometAPIConfig
from .crynux_config import CRYNUX_API_PARAMS, CrynuxConfig
from .deepseek_config import DEEPSEEK_API_PARAMS, DeepSeekConfig
from .function_gemma_config import (
    FUNCTION_GEMMA_API_PARAMS,
    FunctionGemmaConfig,
)
from .gemini_config import Gemini_API_PARAMS, GeminiConfig
from .groq_config import GROQ_API_PARAMS, GroqConfig
from .internlm_config import INTERNLM_API_PARAMS, InternLMConfig
from .litellm_config import LITELLM_API_PARAMS, LiteLLMConfig
from .lmstudio_config import LMSTUDIO_API_PARAMS, LMStudioConfig
from .minimax_config import MINIMAX_API_PARAMS, MinimaxConfig
from .mistral_config import MISTRAL_API_PARAMS, MistralConfig
from .modelscope_config import MODELSCOPE_API_PARAMS, ModelScopeConfig
from .moonshot_config import MOONSHOT_API_PARAMS, MoonshotConfig
from .nebius_config import NEBIUS_API_PARAMS, NebiusConfig
from .netmind_config import NETMIND_API_PARAMS, NetmindConfig
from .novita_config import NOVITA_API_PARAMS, NovitaConfig
from .nvidia_config import NVIDIA_API_PARAMS, NvidiaConfig
from .ollama_config import OLLAMA_API_PARAMS, OllamaConfig
from .openai_config import OPENAI_API_PARAMS, ChatGPTConfig
from .openrouter_config import OPENROUTER_API_PARAMS, OpenRouterConfig
from .ppio_config import PPIO_API_PARAMS, PPIOConfig
from .qianfan_config import QIANFAN_API_PARAMS, QianfanConfig
from .qwen_config import QWEN_API_PARAMS, QwenConfig
from .reka_config import REKA_API_PARAMS, RekaConfig
from .samba_config import (
    SAMBA_CLOUD_API_PARAMS,
    SAMBA_VERSE_API_PARAMS,
    SambaCloudAPIConfig,
    SambaVerseAPIConfig,
)
from .sglang_config import SGLANG_API_PARAMS, SGLangConfig
from .siliconflow_config import SILICONFLOW_API_PARAMS, SiliconFlowConfig
from .togetherai_config import TOGETHERAI_API_PARAMS, TogetherAIConfig
from .vllm_config import VLLM_API_PARAMS, VLLMConfig
from .watsonx_config import WATSONX_API_PARAMS, WatsonXConfig
from .yi_config import YI_API_PARAMS, YiConfig
from .zhipuai_config import ZHIPUAI_API_PARAMS, ZhipuAIConfig

__all__ = [
    'AIHUBMIX_API_PARAMS',
    'AIML_API_PARAMS',
    'AMD_API_PARAMS',
    'ANTHROPIC_API_PARAMS',
    'ATLASCLOUD_API_PARAMS',
    'BEDROCK_API_PARAMS',
    'CEREBRAS_API_PARAMS',
    'COHERE_API_PARAMS',
    'COMETAPI_API_PARAMS',
    'CRYNUX_API_PARAMS',
    'DEEPSEEK_API_PARAMS',
    'FUNCTION_GEMMA_API_PARAMS',
    'GROQ_API_PARAMS',
    'INTERNLM_API_PARAMS',
    'LITELLM_API_PARAMS',
    'LMSTUDIO_API_PARAMS',
    'MINIMAX_API_PARAMS',
    'MISTRAL_API_PARAMS',
    'MODELSCOPE_API_PARAMS',
    "MOONSHOT_API_PARAMS",
    'NEBIUS_API_PARAMS',
    'NETMIND_API_PARAMS',
    'NOVITA_API_PARAMS',
    'NVIDIA_API_PARAMS',
    'OLLAMA_API_PARAMS',
    'OPENAI_API_PARAMS',
    'OPENROUTER_API_PARAMS',
    'PPIO_API_PARAMS',
    'QIANFAN_API_PARAMS',
    'QWEN_API_PARAMS',
    'REKA_API_PARAMS',
    'SAMBA_CLOUD_API_PARAMS',
    'SAMBA_VERSE_API_PARAMS',
    'SGLANG_API_PARAMS',
    'SILICONFLOW_API_PARAMS',
    'TOGETHERAI_API_PARAMS',
    'VLLM_API_PARAMS',
    'WATSONX_API_PARAMS',
    'YI_API_PARAMS',
    'ZHIPUAI_API_PARAMS',
    'AIMLConfig',
    'AMDConfig',
    'AihubMixConfig',
    'AnthropicConfig',
    'AtlasCloudConfig',
    'BaseConfig',
    'BedrockConfig',
    'CerebrasConfig',
    'ChatGPTConfig',
    'CohereConfig',
    'CometAPIConfig',
    'CrynuxConfig',
    'DeepSeekConfig',
    'FunctionGemmaConfig',
    'GeminiConfig',
    'Gemini_API_PARAMS',
    'GroqConfig',
    'InternLMConfig',
    'LMStudioConfig',
    'LiteLLMConfig',
    'MinimaxConfig',
    'MistralConfig',
    'ModelScopeConfig',
    'MoonshotConfig',
    'NebiusConfig',
    'NetmindConfig',
    'NovitaConfig',
    'NvidiaConfig',
    'OllamaConfig',
    'OpenRouterConfig',
    'PPIOConfig',
    'QianfanConfig',
    'QwenConfig',
    'RekaConfig',
    'SGLangConfig',
    'SambaCloudAPIConfig',
    'SambaVerseAPIConfig',
    'SiliconFlowConfig',
    'TogetherAIConfig',
    'VLLMConfig',
    'WatsonXConfig',
    'YiConfig',
    'ZhipuAIConfig',
]
