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
from .anthropic_config import ANTHROPIC_API_PARAMS, AnthropicConfig
from .base_config import BaseConfig
from .gemini_config import (
    Gemini_API_PARAMS,
    GeminiConfig,
)
from .litellm_config import LITELLM_API_PARAMS, LiteLLMConfig
from .ollama_config import OLLAMA_API_PARAMS, OllamaConfig
from .openai_config import (
    OPENAI_API_PARAMS,
    ChatGPTConfig,
    OpenSourceConfig,
)
from .zhipuai_config import ZHIPUAI_API_PARAMS, ZhipuAIConfig

__all__ = [
    'BaseConfig',
    'ChatGPTConfig',
    'OPENAI_API_PARAMS',
    'AnthropicConfig',
    'ANTHROPIC_API_PARAMS',
    'OpenSourceConfig',
    'LiteLLMConfig',
    'LITELLM_API_PARAMS',
    'OllamaConfig',
    'OLLAMA_API_PARAMS',
    'ZhipuAIConfig',
    'ZHIPUAI_API_PARAMS',
    'GeminiConfig',
    'Gemini_API_PARAMS',
]
