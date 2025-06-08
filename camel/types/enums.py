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
import os
from enum import Enum, EnumMeta
from typing import cast

from camel.logger import get_logger
from camel.types.unified_model_type import UnifiedModelType

logger = get_logger(__name__)


class RoleType(Enum):
    ASSISTANT = "assistant"
    USER = "user"
    CRITIC = "critic"
    EMBODIMENT = "embodiment"
    DEFAULT = "default"


class ModelType(UnifiedModelType, Enum):
    DEFAULT = os.getenv("DEFAULT_MODEL_TYPE", "gpt-4o-mini")

    GPT_3_5_TURBO = "gpt-3.5-turbo"
    GPT_4 = "gpt-4"
    GPT_4_TURBO = "gpt-4-turbo"
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_4_5_PREVIEW = "gpt-4.5-preview"
    O1 = "o1"
    O1_PREVIEW = "o1-preview"
    O1_MINI = "o1-mini"
    O3_MINI = "o3-mini"
    GPT_4_1 = "gpt-4.1-2025-04-14"
    GPT_4_1_MINI = "gpt-4.1-mini-2025-04-14"
    GPT_4_1_NANO = "gpt-4.1-nano-2025-04-14"
    O4_MINI = "o4-mini"
    O3 = "o3"

    AWS_CLAUDE_3_7_SONNET = "anthropic.claude-3-7-sonnet-20250219-v1:0"
    AWS_CLAUDE_3_5_SONNET = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    AWS_CLAUDE_3_HAIKU = "anthropic.claude-3-haiku-20240307-v1:0"
    AWS_CLAUDE_3_SONNET = "anthropic.claude-3-sonnet-20240229-v1:0"
    AWS_DEEPSEEK_R1 = "us.deepseek.r1-v1:0"
    AWS_LLAMA_3_3_70B_INSTRUCT = "us.meta.llama3-3-70b-instruct-v1:0"
    AWS_LLAMA_3_2_90B_INSTRUCT = "us.meta.llama3-2-90b-instruct-v1:0"
    AWS_LLAMA_3_2_11B_INSTRUCT = "us.meta.llama3-2-11b-instruct-v1:0"
    AWS_CLAUDE_SONNET_4 = "anthropic.claude-sonnet-4-20250514-v1:0"
    AWS_CLAUDE_OPUS_4 = "anthropic.claude-opus-4-20250514-v1:0"

    GLM_4 = "glm-4"
    GLM_4V = "glm-4v"
    GLM_4V_FLASH = "glm-4v-flash"
    GLM_4V_PLUS_0111 = "glm-4v-plus-0111"
    GLM_4_PLUS = "glm-4-plus"
    GLM_4_AIR = "glm-4-air"
    GLM_4_AIR_0111 = "glm-4-air-0111"
    GLM_4_AIRX = "glm-4-airx"
    GLM_4_LONG = "glm-4-long"
    GLM_4_FLASHX = "glm-4-flashx"
    GLM_4_FLASH = "glm-4-flash"
    GLM_ZERO_PREVIEW = "glm-zero-preview"
    GLM_3_TURBO = "glm-3-turbo"

    # Groq platform models
    GROQ_LLAMA_3_1_8B = "llama-3.1-8b-instant"
    GROQ_LLAMA_3_3_70B = "llama-3.3-70b-versatile"
    GROQ_LLAMA_3_3_70B_PREVIEW = "llama-3.3-70b-specdec"
    GROQ_LLAMA_3_8B = "llama3-8b-8192"
    GROQ_LLAMA_3_70B = "llama3-70b-8192"
    GROQ_MIXTRAL_8_7B = "mixtral-8x7b-32768"
    GROQ_GEMMA_2_9B_IT = "gemma2-9b-it"

    # OpenRouter models
    OPENROUTER_LLAMA_3_1_405B = "meta-llama/llama-3.1-405b-instruct"
    OPENROUTER_LLAMA_3_1_70B = "meta-llama/llama-3.1-70b-instruct"
    OPENROUTER_LLAMA_4_MAVERICK = "meta-llama/llama-4-maverick"
    OPENROUTER_LLAMA_4_MAVERICK_FREE = "meta-llama/llama-4-maverick:free"
    OPENROUTER_LLAMA_4_SCOUT = "meta-llama/llama-4-scout"
    OPENROUTER_LLAMA_4_SCOUT_FREE = "meta-llama/llama-4-scout:free"
    OPENROUTER_OLYMPICODER_7B = "open-r1/olympiccoder-7b:free"

    # LMStudio models
    LMSTUDIO_GEMMA_3_1B = "gemma-3-1b"
    LMSTUDIO_GEMMA_3_4B = "gemma-3-4b"
    LMSTUDIO_GEMMA_3_12B = "gemma-3-12b"
    LMSTUDIO_GEMMA_3_27B = "gemma-3-27b"

    # TogetherAI platform models support tool calling
    TOGETHER_LLAMA_3_1_8B = "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"
    TOGETHER_LLAMA_3_1_70B = "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"
    TOGETHER_LLAMA_3_1_405B = "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo"
    TOGETHER_LLAMA_3_3_70B = "meta-llama/Llama-3.3-70B-Instruct-Turbo"
    TOGETHER_MIXTRAL_8_7B = "mistralai/Mixtral-8x7B-Instruct-v0.1"
    TOGETHER_MISTRAL_7B = "mistralai/Mistral-7B-Instruct-v0.1"
    TOGETHER_LLAMA_4_MAVERICK = (
        "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8"
    )
    TOGETHER_LLAMA_4_SCOUT = "meta-llama/Llama-4-Scout-17B-16E-Instruct"

    # PPIO platform models support tool calling
    PPIO_DEEPSEEK_PROVER_V2_671B = "deepseek/deepseek-prover-v2-671b"
    PPIO_DEEPSEEK_R1_TURBO = "deepseek/deepseek-r1-turbo"
    PPIO_DEEPSEEK_V3_TURBO = "deepseek/deepseek-v3-turbo"
    PPIO_DEEPSEEK_R1_COMMUNITY = "deepseek/deepseek-r1/community"
    PPIO_DEEPSEEK_V3_COMMUNITY = "deepseek/deepseek-v3/community"
    PPIO_DEEPSEEK_R1 = "deepseek/deepseek-r1"
    PPIO_DEEPSEEK_V3 = "deepseek/deepseek-v3"
    PPIO_QWEN_2_5_72B = "qwen/qwen-2.5-72b-instruct"
    PPIO_BAICHUAN_2_13B_CHAT = "baichuan/baichuan2-13b-chat"
    PPIO_LLAMA_3_3_70B = "meta-llama/llama-3.3-70b-instruct"
    PPIO_LLAMA_3_1_70B = "meta-llama/llama-3.1-70b-instruct"
    PPIO_YI_1_5_34B_CHAT = "01-ai/yi-1.5-34b-chat"

    # SambaNova Cloud platform models support tool calling
    SAMBA_LLAMA_3_1_8B = "Meta-Llama-3.1-8B-Instruct"
    SAMBA_LLAMA_3_1_70B = "Meta-Llama-3.1-70B-Instruct"
    SAMBA_LLAMA_3_1_405B = "Meta-Llama-3.1-405B-Instruct"

    # SGLang models support tool calling
    SGLANG_LLAMA_3_1_8B = "meta-llama/Meta-Llama-3.1-8B-Instruct"
    SGLANG_LLAMA_3_1_70B = "meta-llama/Meta-Llama-3.1-70B-Instruct"
    SGLANG_LLAMA_3_1_405B = "meta-llama/Meta-Llama-3.1-405B-Instruct"
    SGLANG_LLAMA_3_2_1B = "meta-llama/Llama-3.2-1B-Instruct"
    SGLANG_MIXTRAL_NEMO = "mistralai/Mistral-Nemo-Instruct-2407"
    SGLANG_MISTRAL_7B = "mistralai/Mistral-7B-Instruct-v0.3"
    SGLANG_QWEN_2_5_7B = "Qwen/Qwen2.5-7B-Instruct"
    SGLANG_QWEN_2_5_32B = "Qwen/Qwen2.5-32B-Instruct"
    SGLANG_QWEN_2_5_72B = "Qwen/Qwen2.5-72B-Instruct"

    STUB = "stub"

    # Legacy anthropic models
    # NOTE: anthropic legacy models only Claude 2.1 has system prompt support
    CLAUDE_2_1 = "claude-2.1"
    CLAUDE_2_0 = "claude-2.0"
    CLAUDE_INSTANT_1_2 = "claude-instant-1.2"

    # Claude models
    CLAUDE_3_OPUS = "claude-3-opus-latest"
    CLAUDE_3_SONNET = "claude-3-sonnet-20240229"
    CLAUDE_3_HAIKU = "claude-3-haiku-20240307"
    CLAUDE_3_5_SONNET = "claude-3-5-sonnet-latest"
    CLAUDE_3_5_HAIKU = "claude-3-5-haiku-latest"
    CLAUDE_3_7_SONNET = "claude-3-7-sonnet-latest"
    CLAUDE_SONNET_4 = "claude-sonnet-4-20250514"
    CLAUDE_OPUS_4 = "claude-opus-4-20250514"

    # Netmind models
    NETMIND_LLAMA_4_MAVERICK_17B_128E_INSTRUCT = (
        "meta-llama/Llama-4-Maverick-17B-128E-Instruct"
    )
    NETMIND_LLAMA_4_SCOUT_17B_16E_INSTRUCT = (
        "meta-llama/Llama-4-Scout-17B-16E-Instruct"
    )
    NETMIND_DEEPSEEK_R1 = "deepseek-ai/DeepSeek-R1"
    NETMIND_DEEPSEEK_V3 = "deepseek-ai/DeepSeek-V3-0324"
    NETMIND_DOUBAO_1_5_PRO = "doubao/Doubao-1.5-pro"
    NETMIND_QWQ_32B = "Qwen/QwQ-32B"

    # Nvidia models
    NVIDIA_NEMOTRON_340B_INSTRUCT = "nvidia/nemotron-4-340b-instruct"
    NVIDIA_NEMOTRON_340B_REWARD = "nvidia/nemotron-4-340b-reward"
    NVIDIA_YI_LARGE = "01-ai/yi-large"
    NVIDIA_MISTRAL_LARGE = "mistralai/mistral-large"
    NVIDIA_MIXTRAL_8X7B = "mistralai/mixtral-8x7b-instruct"
    NVIDIA_LLAMA3_70B = "meta/llama3-70b"
    NVIDIA_LLAMA3_1_8B_INSTRUCT = "meta/llama-3.1-8b-instruct"
    NVIDIA_LLAMA3_1_70B_INSTRUCT = "meta/llama-3.1-70b-instruct"
    NVIDIA_LLAMA3_1_405B_INSTRUCT = "meta/llama-3.1-405b-instruct"
    NVIDIA_LLAMA3_2_1B_INSTRUCT = "meta/llama-3.2-1b-instruct"
    NVIDIA_LLAMA3_2_3B_INSTRUCT = "meta/llama-3.2-3b-instruct"
    NVIDIA_LLAMA3_3_70B_INSTRUCT = "meta/llama-3.3-70b-instruct"

    # Gemini models
    GEMINI_2_5_FLASH_PREVIEW = "gemini-2.5-flash-preview-04-17"
    GEMINI_2_5_PRO_PREVIEW = "gemini-2.5-pro-preview-05-06"
    GEMINI_2_0_FLASH = "gemini-2.0-flash"
    GEMINI_2_0_FLASH_EXP = "gemini-2.0-flash-exp"
    GEMINI_2_0_FLASH_THINKING = "gemini-2.0-flash-thinking-exp"
    GEMINI_2_0_PRO_EXP = "gemini-2.0-pro-exp-02-05"
    GEMINI_2_0_FLASH_LITE = "gemini-2.0-flash-lite"
    GEMINI_2_0_FLASH_LITE_PREVIEW = "gemini-2.0-flash-lite-preview-02-05"
    GEMINI_1_5_FLASH = "gemini-1.5-flash"
    GEMINI_1_5_PRO = "gemini-1.5-pro"

    # Mistral AI models
    MISTRAL_3B = "ministral-3b-latest"
    MISTRAL_7B = "open-mistral-7b"
    MISTRAL_8B = "ministral-8b-latest"
    MISTRAL_CODESTRAL = "codestral-latest"
    MISTRAL_CODESTRAL_MAMBA = "open-codestral-mamba"
    MISTRAL_LARGE = "mistral-large-latest"
    MISTRAL_MIXTRAL_8x7B = "open-mixtral-8x7b"
    MISTRAL_MIXTRAL_8x22B = "open-mixtral-8x22b"
    MISTRAL_NEMO = "open-mistral-nemo"
    MISTRAL_PIXTRAL_12B = "pixtral-12b-2409"
    MISTRAL_MEDIUM_3 = "mistral-medium-latest"

    # Reka models
    REKA_CORE = "reka-core"
    REKA_FLASH = "reka-flash"
    REKA_EDGE = "reka-edge"

    # Cohere models
    COHERE_COMMAND_R_PLUS = "command-r-plus"
    COHERE_COMMAND_R = "command-r"
    COHERE_COMMAND_LIGHT = "command-light"
    COHERE_COMMAND = "command"
    COHERE_COMMAND_NIGHTLY = "command-nightly"

    # Qwen models (Aliyun)
    QWEN_MAX = "qwen-max"
    QWEN_PLUS = "qwen-plus"
    QWEN_TURBO = "qwen-turbo"
    QWEN_PLUS_LATEST = "qwen-plus-latest"
    QWEN_PLUS_2025_04_28 = "qwen-plus-2025-04-28"
    QWEN_TURBO_LATEST = "qwen-turbo-latest"
    QWEN_TURBO_2025_04_28 = "qwen-turbo-2025-04-28"
    QWEN_LONG = "qwen-long"
    QWEN_VL_MAX = "qwen-vl-max"
    QWEN_VL_PLUS = "qwen-vl-plus"
    QWEN_MATH_PLUS = "qwen-math-plus"
    QWEN_MATH_TURBO = "qwen-math-turbo"
    QWEN_CODER_TURBO = "qwen-coder-turbo"
    QWEN_2_5_CODER_32B = "qwen2.5-coder-32b-instruct"
    QWEN_2_5_VL_72B = "qwen2.5-vl-72b-instruct"
    QWEN_2_5_72B = "qwen2.5-72b-instruct"
    QWEN_2_5_32B = "qwen2.5-32b-instruct"
    QWEN_2_5_14B = "qwen2.5-14b-instruct"
    QWEN_QWQ_32B = "qwq-32b-preview"
    QWEN_QVQ_72B = "qvq-72b-preview"
    QWEN_QWQ_PLUS = "qwq-plus"

    # Yi models (01-ai)
    YI_LIGHTNING = "yi-lightning"
    YI_LARGE = "yi-large"
    YI_MEDIUM = "yi-medium"
    YI_LARGE_TURBO = "yi-large-turbo"
    YI_VISION = "yi-vision"
    YI_MEDIUM_200K = "yi-medium-200k"
    YI_SPARK = "yi-spark"
    YI_LARGE_RAG = "yi-large-rag"
    YI_LARGE_FC = "yi-large-fc"

    # DeepSeek models
    DEEPSEEK_CHAT = "deepseek-chat"
    DEEPSEEK_REASONER = "deepseek-reasoner"
    # InternLM models
    INTERNLM3_LATEST = "internlm3-latest"
    INTERNLM3_8B_INSTRUCT = "internlm3-8b-instruct"
    INTERNLM2_5_LATEST = "internlm2.5-latest"
    INTERNLM2_PRO_CHAT = "internlm2-pro-chat"

    # Moonshot models
    MOONSHOT_V1_8K = "moonshot-v1-8k"
    MOONSHOT_V1_32K = "moonshot-v1-32k"
    MOONSHOT_V1_128K = "moonshot-v1-128k"

    # SiliconFlow models support tool calling
    SILICONFLOW_DEEPSEEK_V2_5 = "deepseek-ai/DeepSeek-V2.5"
    SILICONFLOW_DEEPSEEK_V3 = "deepseek-ai/DeepSeek-V3"
    SILICONFLOW_INTERN_LM2_5_20B_CHAT = "internlm/internlm2_5-20b-chat"
    SILICONFLOW_INTERN_LM2_5_7B_CHAT = "internlm/internlm2_5-7b-chat"
    SILICONFLOW_PRO_INTERN_LM2_5_7B_CHAT = "Pro/internlm/internlm2_5-7b-chat"
    SILICONFLOW_QWEN2_5_72B_INSTRUCT = "Qwen/Qwen2.5-72B-Instruct"
    SILICONFLOW_QWEN2_5_32B_INSTRUCT = "Qwen/Qwen2.5-32B-Instruct"
    SILICONFLOW_QWEN2_5_14B_INSTRUCT = "Qwen/Qwen2.5-14B-Instruct"
    SILICONFLOW_QWEN2_5_7B_INSTRUCT = "Qwen/Qwen2.5-7B-Instruct"
    SILICONFLOW_PRO_QWEN2_5_7B_INSTRUCT = "Pro/Qwen/Qwen2.5-7B-Instruct"
    SILICONFLOW_THUDM_GLM_4_9B_CHAT = "THUDM/glm-4-9b-chat"
    SILICONFLOW_PRO_THUDM_GLM_4_9B_CHAT = "Pro/THUDM/glm-4-9b-chat"

    # AIML models support tool calling
    AIML_MIXTRAL_8X7B = "mistralai/Mixtral-8x7B-Instruct-v0.1"
    AIML_MISTRAL_7B_INSTRUCT = "mistralai/Mistral-7B-Instruct-v0.1"

    # Novita platform models support tool calling
    NOVITA_LLAMA_4_MAVERICK_17B = (
        "meta-llama/llama-4-maverick-17b-128e-instruct-fp8"
    )
    NOVITA_LLAMA_4_SCOUT_17B = "meta-llama/llama-4-scout-17b-16e-instruct"
    NOVITA_DEEPSEEK_V3_0324 = "deepseek/deepseek-v3-0324"
    NOVITA_QWEN_2_5_V1_72B = "qwen/qwen2.5-vl-72b-instruct"
    NOVITA_DEEPSEEK_V3_TURBO = "deepseek/deepseek-v3-turbo"
    NOVITA_DEEPSEEK_R1_TURBO = "deepseek/deepseek-r1-turbo"
    NOVITA_GEMMA_3_27B_IT = "google/gemma-3-27b-it"
    NOVITA_QWEN_32B = "qwen/qwq-32b"
    NOVITA_L3_8B_STHENO_V3_2 = "Sao10K/L3-8B-Stheno-v3.2"
    NOVITA_MYTHOMAX_L2_13B = "gryphe/mythomax-l2-13b"
    NOVITA_DEEPSEEK_R1_DISTILL_LLAMA_8B = (
        "deepseek/deepseek-r1-distill-llama-8b"
    )
    NOVITA_DEEPSEEK_V3 = "deepseek/deepseek_v3"
    NOVITA_LLAMA_3_1_8B = "meta-llama/llama-3.1-8b-instruct"
    NOVITA_DEEPSEEK_R1_DISTILL_QWEN_14B = (
        "deepseek/deepseek-r1-distill-qwen-14b"
    )
    NOVITA_LLAMA_3_3_70B = "meta-llama/llama-3.3-70b-instruct"
    NOVITA_QWEN_2_5_72B = "qwen/qwen-2.5-72b-instruct"
    NOVITA_MISTRAL_NEMO = "mistralai/mistral-nemo"
    NOVITA_DEEPSEEK_R1_DISTILL_QWEN_32B = (
        "deepseek/deepseek-r1-distill-qwen-32b"
    )
    NOVITA_LLAMA_3_8B = "meta-llama/llama-3-8b-instruct"
    NOVITA_WIZARDLM_2_8X22B = "microsoft/wizardlm-2-8x22b"
    NOVITA_DEEPSEEK_R1_DISTILL_LLAMA_70B = (
        "deepseek/deepseek-r1-distill-llama-70b"
    )
    NOVITA_LLAMA_3_1_70B = "meta-llama/llama-3.1-70b-instruct"
    NOVITA_GEMMA_2_9B_IT = "google/gemma-2-9b-it"
    NOVITA_MISTRAL_7B = "mistralai/mistral-7b-instruct"
    NOVITA_LLAMA_3_70B = "meta-llama/llama-3-70b-instruct"
    NOVITA_DEEPSEEK_R1 = "deepseek/deepseek-r1"
    NOVITA_HERMES_2_PRO_LLAMA_3_8B = "nousresearch/hermes-2-pro-llama-3-8b"
    NOVITA_L3_70B_EURYALE_V2_1 = "sao10k/l3-70b-euryale-v2.1"
    NOVITA_DOLPHIN_MIXTRAL_8X22B = (
        "cognitivecomputations/dolphin-mixtral-8x22b"
    )
    NOVITA_AIROBOROS_L2_70B = "jondurbin/airoboros-l2-70b"
    NOVITA_MIDNIGHT_ROSE_70B = "sophosympatheia/midnight-rose-70b"
    NOVITA_L3_8B_LUNARIS = "sao10k/l3-8b-lunaris"
    NOVITA_GLM_4_9B_0414 = "thudm/glm-4-9b-0414"
    NOVITA_GLM_Z1_9B_0414 = "thudm/glm-z1-9b-0414"
    NOVITA_GLM_Z1_32B_0414 = "thudm/glm-z1-32b-0414"
    NOVITA_GLM_4_32B_0414 = "thudm/glm-4-32b-0414"
    NOVITA_GLM_Z1_RUMINATION_32B_0414 = "thudm/glm-z1-rumination-32b-0414"
    NOVITA_QWEN_2_5_7B = "qwen/qwen2.5-7b-instruct"
    NOVITA_LLAMA_3_2_1B = "meta-llama/llama-3.2-1b-instruct"
    NOVITA_LLAMA_3_2_11B_VISION = "meta-llama/llama-3.2-11b-vision-instruct"
    NOVITA_LLAMA_3_2_3B = "meta-llama/llama-3.2-3b-instruct"
    NOVITA_LLAMA_3_1_8B_BF16 = "meta-llama/llama-3.1-8b-instruct-bf16"
    NOVITA_L31_70B_EURYALE_V2_2 = "sao10k/l31-70b-euryale-v2.2"

    # ModelScope models support tool calling
    MODELSCOPE_QWEN_2_5_7B_INSTRUCT = "Qwen/Qwen2.5-7B-Instruct"
    MODELSCOPE_QWEN_2_5_14B_INSTRUCT = "Qwen/Qwen2.5-14B-Instruct"
    MODELSCOPE_QWEN_2_5_32B_INSTRUCT = "Qwen/Qwen2.5-32B-Instruct"
    MODELSCOPE_QWEN_2_5_72B_INSTRUCT = "Qwen/Qwen2.5-72B-Instruct"
    MODELSCOPE_QWEN_2_5_CODER_7B_INSTRUCT = "Qwen/Qwen2.5-Coder-7B-Instruct"
    MODELSCOPE_QWEN_2_5_CODER_14B_INSTRUCT = "Qwen/Qwen2.5-Coder-14B-Instruct"
    MODELSCOPE_QWEN_2_5_CODER_32B_INSTRUCT = "Qwen/Qwen2.5-Coder-32B-Instruct"
    MODELSCOPE_QWEN_3_235B_A22B = "Qwen/Qwen3-235B-A22B"
    MODELSCOPE_QWEN_3_32B = "Qwen/Qwen3-32B"
    MODELSCOPE_QWQ_32B = "Qwen/QwQ-32B"
    MODELSCOPE_QWQ_32B_PREVIEW = "Qwen/QwQ-32B-Preview"
    MODELSCOPE_LLAMA_3_1_8B_INSTRUCT = (
        "LLM-Research/Meta-Llama-3.1-8B-Instruct"
    )
    MODELSCOPE_LLAMA_3_1_70B_INSTRUCT = (
        "LLM-Research/Meta-Llama-3.1-70B-Instruct"
    )
    MODELSCOPE_LLAMA_3_1_405B_INSTRUCT = (
        "LLM-Research/Meta-Llama-3.1-405B-Instruct"
    )
    MODELSCOPE_LLAMA_3_3_70B_INSTRUCT = "LLM-Research/Llama-3.3-70B-Instruct"
    MODELSCOPE_MINISTRAL_8B_INSTRUCT = "mistralai/Ministral-8B-Instruct-2410"
    MODELSCOPE_DEEPSEEK_V3_0324 = "deepseek-ai/DeepSeek-V3-0324"

    # WatsonX models
    WATSONX_GRANITE_3_8B_INSTRUCT = "ibm/granite-3-8b-instruct"
    WATSONX_LLAMA_3_3_70B_INSTRUCT = "meta-llama/llama-3-3-70b-instruct"
    WATSONX_LLAMA_3_2_1B_INSTRUCT = "meta-llama/llama-3-2-1b-instruct"
    WATSONX_LLAMA_3_2_3B_INSTRUCT = "meta-llama/llama-3-2-3b-instruct"
    WATSONX_LLAMA_3_2_11B_VISION_INSTRUCT = (
        "meta-llama/llama-3-2-11b-vision-instruct"
    )
    WATSONX_LLAMA_3_2_90B_VISION_INSTRUCT = (
        "meta-llama/llama-3-2-90b-vision-instruct"
    )
    WATSONX_LLAMA_GUARD_3_11B_VISION_INSTRUCT = (
        "meta-llama/llama-guard-3-11b-vision-instruct"
    )
    WATSONX_MISTRAL_LARGE = "mistralai/mistral-large"

    def __str__(self):
        return self.value

    def __new__(cls, value) -> "ModelType":
        return cast("ModelType", UnifiedModelType.__new__(cls, value))

    @classmethod
    def from_name(cls, name):
        r"""Returns the ModelType enum value from a string."""
        for model_type in cls:
            if model_type.value == name:
                return model_type
        raise ValueError(f"Unknown ModelType name: {name}")

    @property
    def value_for_tiktoken(self) -> str:
        if self.is_openai:
            return self.value
        return "gpt-4o-mini"

    @property
    def support_native_structured_output(self) -> bool:
        return any(
            [
                self.is_openai,
            ]
        )

    @property
    def support_native_tool_calling(self) -> bool:
        return any(
            [
                self.is_openai,
                self.is_gemini,
                self.is_mistral,
                self.is_qwen,
                self.is_deepseek,
                self.is_ppio,
                self.is_cohere,
                self.is_internlm,
                self.is_together,
                self.is_sambanova,
                self.is_groq,
                self.is_openrouter,
                self.is_lmstudio,
                self.is_sglang,
                self.is_moonshot,
                self.is_siliconflow,
                self.is_modelscope,
                self.is_zhipuai,
                self.is_aiml,
                self.is_azure_openai,
                self.is_novita,
            ]
        )

    @property
    def is_openai(self) -> bool:
        r"""Returns whether this type of models is an OpenAI-released model."""
        return self in {
            ModelType.GPT_3_5_TURBO,
            ModelType.GPT_4,
            ModelType.GPT_4_TURBO,
            ModelType.GPT_4O,
            ModelType.GPT_4O_MINI,
            ModelType.O1,
            ModelType.O1_PREVIEW,
            ModelType.O1_MINI,
            ModelType.O3_MINI,
            ModelType.GPT_4_5_PREVIEW,
            ModelType.GPT_4_1,
            ModelType.GPT_4_1_MINI,
            ModelType.GPT_4_1_NANO,
            ModelType.O4_MINI,
            ModelType.O3,
        }

    @property
    def is_aws_bedrock(self) -> bool:
        r"""Returns whether this type of models is an AWS Bedrock model."""
        return self in {
            ModelType.AWS_CLAUDE_3_7_SONNET,
            ModelType.AWS_CLAUDE_3_5_SONNET,
            ModelType.AWS_CLAUDE_3_HAIKU,
            ModelType.AWS_CLAUDE_3_SONNET,
            ModelType.AWS_DEEPSEEK_R1,
            ModelType.AWS_LLAMA_3_3_70B_INSTRUCT,
            ModelType.AWS_LLAMA_3_2_90B_INSTRUCT,
            ModelType.AWS_LLAMA_3_2_11B_INSTRUCT,
            ModelType.AWS_CLAUDE_SONNET_4,
            ModelType.AWS_CLAUDE_OPUS_4,
        }

    @property
    def is_azure_openai(self) -> bool:
        r"""Returns whether this type of models is an OpenAI-released model
        from Azure.
        """
        return self in {
            ModelType.GPT_3_5_TURBO,
            ModelType.GPT_4,
            ModelType.GPT_4_TURBO,
            ModelType.GPT_4O,
            ModelType.GPT_4O_MINI,
            ModelType.O1,
            ModelType.O1_PREVIEW,
            ModelType.O1_MINI,
            ModelType.O3_MINI,
            ModelType.GPT_4_5_PREVIEW,
            ModelType.GPT_4_1,
            ModelType.GPT_4_1_MINI,
            ModelType.GPT_4_1_NANO,
            ModelType.O4_MINI,
            ModelType.O3,
        }

    @property
    def is_zhipuai(self) -> bool:
        r"""Returns whether this type of models is an ZhipuAI model."""
        return self in {
            ModelType.GLM_3_TURBO,
            ModelType.GLM_4,
            ModelType.GLM_4V,
            ModelType.GLM_4V_FLASH,
            ModelType.GLM_4V_PLUS_0111,
            ModelType.GLM_4_PLUS,
            ModelType.GLM_4_AIR,
            ModelType.GLM_4_AIR_0111,
            ModelType.GLM_4_AIRX,
            ModelType.GLM_4_LONG,
            ModelType.GLM_4_FLASHX,
            ModelType.GLM_4_FLASH,
            ModelType.GLM_ZERO_PREVIEW,
        }

    @property
    def is_anthropic(self) -> bool:
        r"""Returns whether this type of models is Anthropic-released model.

        Returns:
            bool: Whether this type of models is anthropic.
        """
        return self in {
            ModelType.CLAUDE_INSTANT_1_2,
            ModelType.CLAUDE_2_0,
            ModelType.CLAUDE_2_1,
            ModelType.CLAUDE_3_OPUS,
            ModelType.CLAUDE_3_SONNET,
            ModelType.CLAUDE_3_HAIKU,
            ModelType.CLAUDE_3_5_SONNET,
            ModelType.CLAUDE_3_5_HAIKU,
            ModelType.CLAUDE_3_7_SONNET,
            ModelType.CLAUDE_SONNET_4,
            ModelType.CLAUDE_OPUS_4,
        }

    @property
    def is_groq(self) -> bool:
        r"""Returns whether this type of models is served by Groq."""
        return self in {
            ModelType.GROQ_LLAMA_3_1_8B,
            ModelType.GROQ_LLAMA_3_3_70B,
            ModelType.GROQ_LLAMA_3_3_70B_PREVIEW,
            ModelType.GROQ_LLAMA_3_8B,
            ModelType.GROQ_LLAMA_3_70B,
            ModelType.GROQ_MIXTRAL_8_7B,
            ModelType.GROQ_GEMMA_2_9B_IT,
        }

    @property
    def is_openrouter(self) -> bool:
        r"""Returns whether this type of models is served by OpenRouter."""
        return self in {
            ModelType.OPENROUTER_LLAMA_3_1_405B,
            ModelType.OPENROUTER_LLAMA_3_1_70B,
            ModelType.OPENROUTER_LLAMA_4_MAVERICK,
            ModelType.OPENROUTER_LLAMA_4_MAVERICK_FREE,
            ModelType.OPENROUTER_LLAMA_4_SCOUT,
            ModelType.OPENROUTER_LLAMA_4_SCOUT_FREE,
            ModelType.OPENROUTER_OLYMPICODER_7B,
        }

    @property
    def is_lmstudio(self) -> bool:
        r"""Returns whether this type of models is served by LMStudio."""
        return self in {
            ModelType.LMSTUDIO_GEMMA_3_1B,
            ModelType.LMSTUDIO_GEMMA_3_4B,
            ModelType.LMSTUDIO_GEMMA_3_12B,
            ModelType.LMSTUDIO_GEMMA_3_27B,
        }

    @property
    def is_together(self) -> bool:
        r"""Returns whether this type of models is served by Together AI."""
        return self in {
            ModelType.TOGETHER_LLAMA_3_1_405B,
            ModelType.TOGETHER_LLAMA_3_1_70B,
            ModelType.TOGETHER_LLAMA_3_3_70B,
            ModelType.TOGETHER_LLAMA_3_3_70B,
            ModelType.TOGETHER_MISTRAL_7B,
            ModelType.TOGETHER_MIXTRAL_8_7B,
        }

    @property
    def is_sambanova(self) -> bool:
        r"""Returns whether this type of model is served by SambaNova AI."""
        return self in {
            ModelType.SAMBA_LLAMA_3_1_8B,
            ModelType.SAMBA_LLAMA_3_1_70B,
            ModelType.SAMBA_LLAMA_3_1_405B,
        }

    @property
    def is_mistral(self) -> bool:
        r"""Returns whether this type of models is served by Mistral."""
        return self in {
            ModelType.MISTRAL_LARGE,
            ModelType.MISTRAL_NEMO,
            ModelType.MISTRAL_CODESTRAL,
            ModelType.MISTRAL_7B,
            ModelType.MISTRAL_MIXTRAL_8x7B,
            ModelType.MISTRAL_MIXTRAL_8x22B,
            ModelType.MISTRAL_CODESTRAL_MAMBA,
            ModelType.MISTRAL_PIXTRAL_12B,
            ModelType.MISTRAL_8B,
            ModelType.MISTRAL_3B,
            ModelType.MISTRAL_MEDIUM_3,
        }

    @property
    def is_nvidia(self) -> bool:
        r"""Returns whether this type of models is a NVIDIA model."""
        return self in {
            ModelType.NVIDIA_NEMOTRON_340B_INSTRUCT,
            ModelType.NVIDIA_NEMOTRON_340B_REWARD,
            ModelType.NVIDIA_YI_LARGE,
            ModelType.NVIDIA_MISTRAL_LARGE,
            ModelType.NVIDIA_LLAMA3_70B,
            ModelType.NVIDIA_MIXTRAL_8X7B,
            ModelType.NVIDIA_LLAMA3_1_8B_INSTRUCT,
            ModelType.NVIDIA_LLAMA3_1_70B_INSTRUCT,
            ModelType.NVIDIA_LLAMA3_1_405B_INSTRUCT,
            ModelType.NVIDIA_LLAMA3_2_1B_INSTRUCT,
            ModelType.NVIDIA_LLAMA3_2_3B_INSTRUCT,
            ModelType.NVIDIA_LLAMA3_3_70B_INSTRUCT,
        }

    @property
    def is_gemini(self) -> bool:
        r"""Returns whether this type of models is Gemini model.

        Returns:
            bool: Whether this type of models is gemini.
        """
        return self in {
            ModelType.GEMINI_2_5_FLASH_PREVIEW,
            ModelType.GEMINI_2_5_PRO_PREVIEW,
            ModelType.GEMINI_2_0_FLASH,
            ModelType.GEMINI_2_0_FLASH_EXP,
            ModelType.GEMINI_2_0_FLASH_THINKING,
            ModelType.GEMINI_2_0_PRO_EXP,
            ModelType.GEMINI_2_0_FLASH_LITE,
            ModelType.GEMINI_2_0_FLASH_LITE_PREVIEW,
            ModelType.GEMINI_1_5_FLASH,
            ModelType.GEMINI_1_5_PRO,
        }

    @property
    def is_reka(self) -> bool:
        r"""Returns whether this type of models is Reka model.

        Returns:
            bool: Whether this type of models is Reka.
        """
        return self in {
            ModelType.REKA_CORE,
            ModelType.REKA_EDGE,
            ModelType.REKA_FLASH,
        }

    @property
    def is_cohere(self) -> bool:
        r"""Returns whether this type of models is a Cohere model.

        Returns:
            bool: Whether this type of models is Cohere.
        """
        return self in {
            ModelType.COHERE_COMMAND_R_PLUS,
            ModelType.COHERE_COMMAND_R,
            ModelType.COHERE_COMMAND_LIGHT,
            ModelType.COHERE_COMMAND,
            ModelType.COHERE_COMMAND_NIGHTLY,
        }

    @property
    def is_yi(self) -> bool:
        r"""Returns whether this type of models is Yi model.

        Returns:
            bool: Whether this type of models is Yi.
        """
        return self in {
            ModelType.YI_LIGHTNING,
            ModelType.YI_LARGE,
            ModelType.YI_MEDIUM,
            ModelType.YI_LARGE_TURBO,
            ModelType.YI_VISION,
            ModelType.YI_MEDIUM_200K,
            ModelType.YI_SPARK,
            ModelType.YI_LARGE_RAG,
            ModelType.YI_LARGE_FC,
        }

    @property
    def is_qwen(self) -> bool:
        return self in {
            ModelType.QWEN_MAX,
            ModelType.QWEN_PLUS,
            ModelType.QWEN_TURBO,
            ModelType.QWEN_LONG,
            ModelType.QWEN_VL_MAX,
            ModelType.QWEN_VL_PLUS,
            ModelType.QWEN_MATH_PLUS,
            ModelType.QWEN_MATH_TURBO,
            ModelType.QWEN_CODER_TURBO,
            ModelType.QWEN_2_5_CODER_32B,
            ModelType.QWEN_2_5_VL_72B,
            ModelType.QWEN_2_5_72B,
            ModelType.QWEN_2_5_32B,
            ModelType.QWEN_2_5_14B,
            ModelType.QWEN_QWQ_32B,
            ModelType.QWEN_QVQ_72B,
            ModelType.QWEN_QWQ_PLUS,
            ModelType.QWEN_PLUS_LATEST,
            ModelType.QWEN_PLUS_2025_04_28,
            ModelType.QWEN_TURBO_LATEST,
            ModelType.QWEN_TURBO_2025_04_28,
        }

    @property
    def is_deepseek(self) -> bool:
        return self in {
            ModelType.DEEPSEEK_CHAT,
            ModelType.DEEPSEEK_REASONER,
        }

    @property
    def is_netmind(self) -> bool:
        return self in {
            ModelType.NETMIND_LLAMA_4_MAVERICK_17B_128E_INSTRUCT,
            ModelType.NETMIND_LLAMA_4_SCOUT_17B_16E_INSTRUCT,
            ModelType.NETMIND_DEEPSEEK_R1,
            ModelType.NETMIND_DEEPSEEK_V3,
            ModelType.NETMIND_DOUBAO_1_5_PRO,
            ModelType.NETMIND_QWQ_32B,
        }

    @property
    def is_ppio(self) -> bool:
        return self in {
            ModelType.PPIO_DEEPSEEK_PROVER_V2_671B,
            ModelType.PPIO_DEEPSEEK_R1_TURBO,
            ModelType.PPIO_DEEPSEEK_V3_TURBO,
            ModelType.PPIO_DEEPSEEK_R1_COMMUNITY,
            ModelType.PPIO_DEEPSEEK_V3_COMMUNITY,
            ModelType.PPIO_DEEPSEEK_R1,
            ModelType.PPIO_DEEPSEEK_V3,
            ModelType.PPIO_QWEN_2_5_72B,
            ModelType.PPIO_BAICHUAN_2_13B_CHAT,
            ModelType.PPIO_LLAMA_3_3_70B,
            ModelType.PPIO_LLAMA_3_1_70B,
            ModelType.PPIO_YI_1_5_34B_CHAT,
        }

    @property
    def is_internlm(self) -> bool:
        return self in {
            ModelType.INTERNLM3_LATEST,
            ModelType.INTERNLM3_8B_INSTRUCT,
            ModelType.INTERNLM2_5_LATEST,
            ModelType.INTERNLM2_PRO_CHAT,
        }

    @property
    def is_modelscope(self) -> bool:
        return self in {
            ModelType.MODELSCOPE_QWEN_2_5_7B_INSTRUCT,
            ModelType.MODELSCOPE_QWEN_2_5_14B_INSTRUCT,
            ModelType.MODELSCOPE_QWEN_2_5_32B_INSTRUCT,
            ModelType.MODELSCOPE_QWEN_2_5_72B_INSTRUCT,
            ModelType.MODELSCOPE_QWEN_2_5_CODER_7B_INSTRUCT,
            ModelType.MODELSCOPE_QWEN_2_5_CODER_14B_INSTRUCT,
            ModelType.MODELSCOPE_QWEN_2_5_CODER_32B_INSTRUCT,
            ModelType.MODELSCOPE_QWEN_3_235B_A22B,
            ModelType.MODELSCOPE_QWEN_3_32B,
            ModelType.MODELSCOPE_QWQ_32B,
            ModelType.MODELSCOPE_QWQ_32B_PREVIEW,
            ModelType.MODELSCOPE_LLAMA_3_1_8B_INSTRUCT,
            ModelType.MODELSCOPE_LLAMA_3_1_70B_INSTRUCT,
            ModelType.MODELSCOPE_LLAMA_3_1_405B_INSTRUCT,
            ModelType.MODELSCOPE_LLAMA_3_3_70B_INSTRUCT,
            ModelType.MODELSCOPE_MINISTRAL_8B_INSTRUCT,
            ModelType.MODELSCOPE_DEEPSEEK_V3_0324,
        }

    @property
    def is_moonshot(self) -> bool:
        return self in {
            ModelType.MOONSHOT_V1_8K,
            ModelType.MOONSHOT_V1_32K,
            ModelType.MOONSHOT_V1_128K,
        }

    @property
    def is_sglang(self) -> bool:
        return self in {
            ModelType.SGLANG_LLAMA_3_1_8B,
            ModelType.SGLANG_LLAMA_3_1_70B,
            ModelType.SGLANG_LLAMA_3_1_405B,
            ModelType.SGLANG_LLAMA_3_2_1B,
            ModelType.SGLANG_MIXTRAL_NEMO,
            ModelType.SGLANG_MISTRAL_7B,
            ModelType.SGLANG_QWEN_2_5_7B,
            ModelType.SGLANG_QWEN_2_5_32B,
            ModelType.SGLANG_QWEN_2_5_72B,
        }

    @property
    def is_siliconflow(self) -> bool:
        return self in {
            ModelType.SILICONFLOW_DEEPSEEK_V2_5,
            ModelType.SILICONFLOW_DEEPSEEK_V3,
            ModelType.SILICONFLOW_INTERN_LM2_5_20B_CHAT,
            ModelType.SILICONFLOW_INTERN_LM2_5_7B_CHAT,
            ModelType.SILICONFLOW_PRO_INTERN_LM2_5_7B_CHAT,
            ModelType.SILICONFLOW_QWEN2_5_72B_INSTRUCT,
            ModelType.SILICONFLOW_QWEN2_5_32B_INSTRUCT,
            ModelType.SILICONFLOW_QWEN2_5_14B_INSTRUCT,
            ModelType.SILICONFLOW_QWEN2_5_7B_INSTRUCT,
            ModelType.SILICONFLOW_PRO_QWEN2_5_7B_INSTRUCT,
            ModelType.SILICONFLOW_THUDM_GLM_4_9B_CHAT,
            ModelType.SILICONFLOW_PRO_THUDM_GLM_4_9B_CHAT,
        }

    @property
    def is_watsonx(self) -> bool:
        return self in {
            ModelType.WATSONX_GRANITE_3_8B_INSTRUCT,
            ModelType.WATSONX_LLAMA_3_3_70B_INSTRUCT,
            ModelType.WATSONX_LLAMA_3_2_1B_INSTRUCT,
            ModelType.WATSONX_LLAMA_3_2_3B_INSTRUCT,
            ModelType.WATSONX_LLAMA_3_2_11B_VISION_INSTRUCT,
            ModelType.WATSONX_LLAMA_3_2_90B_VISION_INSTRUCT,
            ModelType.WATSONX_LLAMA_GUARD_3_11B_VISION_INSTRUCT,
            ModelType.WATSONX_MISTRAL_LARGE,
        }

    @property
    def is_novita(self) -> bool:
        return self in {
            ModelType.NOVITA_LLAMA_4_MAVERICK_17B,
            ModelType.NOVITA_LLAMA_4_SCOUT_17B,
            ModelType.NOVITA_DEEPSEEK_V3_0324,
            ModelType.NOVITA_QWEN_2_5_V1_72B,
            ModelType.NOVITA_DEEPSEEK_V3_TURBO,
            ModelType.NOVITA_DEEPSEEK_R1_TURBO,
            ModelType.NOVITA_GEMMA_3_27B_IT,
            ModelType.NOVITA_QWEN_32B,
            ModelType.NOVITA_L3_8B_STHENO_V3_2,
            ModelType.NOVITA_MYTHOMAX_L2_13B,
            ModelType.NOVITA_DEEPSEEK_R1_DISTILL_LLAMA_8B,
            ModelType.NOVITA_DEEPSEEK_V3,
            ModelType.NOVITA_LLAMA_3_1_8B,
            ModelType.NOVITA_DEEPSEEK_R1_DISTILL_QWEN_14B,
            ModelType.NOVITA_LLAMA_3_3_70B,
            ModelType.NOVITA_QWEN_2_5_72B,
            ModelType.NOVITA_MISTRAL_NEMO,
            ModelType.NOVITA_DEEPSEEK_R1_DISTILL_QWEN_32B,
            ModelType.NOVITA_LLAMA_3_8B,
            ModelType.NOVITA_WIZARDLM_2_8X22B,
            ModelType.NOVITA_DEEPSEEK_R1_DISTILL_LLAMA_70B,
            ModelType.NOVITA_LLAMA_3_1_70B,
            ModelType.NOVITA_GEMMA_2_9B_IT,
            ModelType.NOVITA_MISTRAL_7B,
            ModelType.NOVITA_LLAMA_3_70B,
            ModelType.NOVITA_DEEPSEEK_R1,
            ModelType.NOVITA_HERMES_2_PRO_LLAMA_3_8B,
            ModelType.NOVITA_L3_70B_EURYALE_V2_1,
            ModelType.NOVITA_DOLPHIN_MIXTRAL_8X22B,
            ModelType.NOVITA_AIROBOROS_L2_70B,
            ModelType.NOVITA_MIDNIGHT_ROSE_70B,
            ModelType.NOVITA_L3_8B_LUNARIS,
            ModelType.NOVITA_GLM_4_9B_0414,
            ModelType.NOVITA_GLM_Z1_9B_0414,
            ModelType.NOVITA_GLM_Z1_32B_0414,
            ModelType.NOVITA_GLM_4_32B_0414,
            ModelType.NOVITA_GLM_Z1_RUMINATION_32B_0414,
            ModelType.NOVITA_QWEN_2_5_7B,
            ModelType.NOVITA_LLAMA_3_2_1B,
            ModelType.NOVITA_LLAMA_3_2_11B_VISION,
            ModelType.NOVITA_LLAMA_3_2_3B,
            ModelType.NOVITA_LLAMA_3_1_8B_BF16,
            ModelType.NOVITA_L31_70B_EURYALE_V2_2,
        }

    @property
    def is_aiml(self) -> bool:
        return self in {
            ModelType.AIML_MIXTRAL_8X7B,
            ModelType.AIML_MISTRAL_7B_INSTRUCT,
        }

    @property
    def token_limit(self) -> int:
        r"""Returns the maximum token limit for a given model.

        Returns:
            int: The maximum token limit for the given model.
        """
        if self is ModelType.GLM_4V:
            return 1024
        elif self in {
            ModelType.STUB,
            ModelType.REKA_CORE,
            ModelType.REKA_EDGE,
            ModelType.REKA_FLASH,
            ModelType.QWEN_MATH_PLUS,
            ModelType.QWEN_MATH_TURBO,
            ModelType.COHERE_COMMAND,
            ModelType.COHERE_COMMAND_LIGHT,
            ModelType.NVIDIA_NEMOTRON_340B_INSTRUCT,
            ModelType.NVIDIA_NEMOTRON_340B_REWARD,
            ModelType.NOVITA_MYTHOMAX_L2_13B,
            ModelType.NOVITA_AIROBOROS_L2_70B,
            ModelType.NOVITA_MIDNIGHT_ROSE_70B,
        }:
            return 4_096
        elif self in {
            ModelType.GPT_4,
            ModelType.GROQ_LLAMA_3_8B,
            ModelType.GROQ_LLAMA_3_70B,
            ModelType.GROQ_LLAMA_3_3_70B_PREVIEW,
            ModelType.GROQ_GEMMA_2_9B_IT,
            ModelType.GLM_3_TURBO,
            ModelType.GLM_4,
            ModelType.QWEN_VL_PLUS,
            ModelType.NVIDIA_LLAMA3_70B,
            ModelType.TOGETHER_MISTRAL_7B,
            ModelType.MOONSHOT_V1_8K,
            ModelType.GLM_4V_FLASH,
            ModelType.GLM_4_AIRX,
            ModelType.OPENROUTER_OLYMPICODER_7B,
            ModelType.LMSTUDIO_GEMMA_3_1B,
            ModelType.LMSTUDIO_GEMMA_3_4B,
            ModelType.LMSTUDIO_GEMMA_3_12B,
            ModelType.LMSTUDIO_GEMMA_3_27B,
            ModelType.WATSONX_GRANITE_3_8B_INSTRUCT,
            ModelType.NOVITA_L3_8B_STHENO_V3_2,
            ModelType.NOVITA_LLAMA_3_8B,
            ModelType.NOVITA_GEMMA_2_9B_IT,
            ModelType.NOVITA_LLAMA_3_70B,
            ModelType.NOVITA_HERMES_2_PRO_LLAMA_3_8B,
            ModelType.NOVITA_L3_70B_EURYALE_V2_1,
            ModelType.NOVITA_L3_8B_LUNARIS,
            ModelType.NOVITA_LLAMA_3_1_8B_BF16,
            ModelType.NOVITA_L31_70B_EURYALE_V2_2,
        }:
            return 8_192
        elif self in {
            ModelType.PPIO_BAICHUAN_2_13B_CHAT,
        }:
            return 14_336
        elif self in {
            ModelType.PPIO_DEEPSEEK_PROVER_V2_671B,
            ModelType.NOVITA_DOLPHIN_MIXTRAL_8X22B,
        }:
            return 16_000
        elif self in {
            ModelType.GPT_3_5_TURBO,
            ModelType.YI_LIGHTNING,
            ModelType.YI_MEDIUM,
            ModelType.YI_LARGE_TURBO,
            ModelType.YI_VISION,
            ModelType.YI_SPARK,
            ModelType.YI_LARGE_RAG,
            ModelType.SAMBA_LLAMA_3_1_8B,
            ModelType.SAMBA_LLAMA_3_1_405B,
            ModelType.GLM_4V_PLUS_0111,
            ModelType.GLM_ZERO_PREVIEW,
            ModelType.PPIO_YI_1_5_34B_CHAT,
            ModelType.NOVITA_LLAMA_3_1_8B,
        }:
            return 16_384
        elif self in {
            ModelType.NETMIND_DOUBAO_1_5_PRO,
            ModelType.NOVITA_GEMMA_3_27B_IT,
            ModelType.NOVITA_DEEPSEEK_R1_DISTILL_LLAMA_8B,
            ModelType.NOVITA_QWEN_2_5_72B,
            ModelType.NOVITA_DEEPSEEK_R1_DISTILL_LLAMA_70B,
            ModelType.NOVITA_GLM_4_9B_0414,
            ModelType.NOVITA_GLM_Z1_9B_0414,
            ModelType.NOVITA_GLM_Z1_32B_0414,
            ModelType.NOVITA_GLM_4_32B_0414,
            ModelType.NOVITA_GLM_Z1_RUMINATION_32B_0414,
            ModelType.NOVITA_QWEN_2_5_7B,
        }:
            return 32_000
        elif self in {
            ModelType.MISTRAL_CODESTRAL,
            ModelType.MISTRAL_7B,
            ModelType.MISTRAL_MIXTRAL_8x7B,
            ModelType.GROQ_MIXTRAL_8_7B,
            ModelType.YI_LARGE,
            ModelType.YI_LARGE_FC,
            ModelType.QWEN_MAX,
            ModelType.QWEN_VL_MAX,
            ModelType.NVIDIA_YI_LARGE,
            ModelType.NVIDIA_MISTRAL_LARGE,
            ModelType.NVIDIA_MIXTRAL_8X7B,
            ModelType.QWEN_QWQ_32B,
            ModelType.QWEN_QWQ_PLUS,
            ModelType.QWEN_QVQ_72B,
            ModelType.INTERNLM3_8B_INSTRUCT,
            ModelType.INTERNLM3_LATEST,
            ModelType.INTERNLM2_5_LATEST,
            ModelType.INTERNLM2_PRO_CHAT,
            ModelType.TOGETHER_MIXTRAL_8_7B,
            ModelType.SGLANG_MISTRAL_7B,
            ModelType.MOONSHOT_V1_32K,
            ModelType.AIML_MIXTRAL_8X7B,
            ModelType.AIML_MISTRAL_7B_INSTRUCT,
            ModelType.PPIO_QWEN_2_5_72B,
            ModelType.PPIO_LLAMA_3_1_70B,
            ModelType.MODELSCOPE_QWEN_2_5_7B_INSTRUCT,
            ModelType.MODELSCOPE_QWEN_2_5_14B_INSTRUCT,
            ModelType.MODELSCOPE_QWEN_2_5_32B_INSTRUCT,
            ModelType.MODELSCOPE_QWEN_2_5_72B_INSTRUCT,
            ModelType.MODELSCOPE_QWEN_2_5_CODER_7B_INSTRUCT,
            ModelType.MODELSCOPE_QWEN_2_5_CODER_14B_INSTRUCT,
            ModelType.MODELSCOPE_QWEN_2_5_CODER_32B_INSTRUCT,
            ModelType.MODELSCOPE_QWEN_3_235B_A22B,
            ModelType.MODELSCOPE_QWEN_3_32B,
            ModelType.MODELSCOPE_QWQ_32B,
            ModelType.MODELSCOPE_QWQ_32B_PREVIEW,
            ModelType.MODELSCOPE_LLAMA_3_1_8B_INSTRUCT,
            ModelType.MODELSCOPE_LLAMA_3_1_70B_INSTRUCT,
            ModelType.MODELSCOPE_LLAMA_3_1_405B_INSTRUCT,
            ModelType.MODELSCOPE_LLAMA_3_3_70B_INSTRUCT,
            ModelType.MODELSCOPE_MINISTRAL_8B_INSTRUCT,
            ModelType.MODELSCOPE_DEEPSEEK_V3_0324,
            ModelType.OPENROUTER_LLAMA_3_1_405B,
            ModelType.WATSONX_MISTRAL_LARGE,
            ModelType.NOVITA_QWEN_32B,
            ModelType.NOVITA_LLAMA_3_1_70B,
            ModelType.NOVITA_MISTRAL_7B,
            ModelType.NOVITA_LLAMA_3_2_11B_VISION,
            ModelType.NOVITA_LLAMA_3_2_3B,
        }:
            return 32_768
        elif self in {
            ModelType.MISTRAL_MIXTRAL_8x22B,
            ModelType.DEEPSEEK_CHAT,
            ModelType.DEEPSEEK_REASONER,
            ModelType.PPIO_DEEPSEEK_R1_TURBO,
            ModelType.PPIO_DEEPSEEK_V3_TURBO,
            ModelType.PPIO_DEEPSEEK_R1_COMMUNITY,
            ModelType.PPIO_DEEPSEEK_V3_COMMUNITY,
            ModelType.PPIO_DEEPSEEK_R1,
            ModelType.PPIO_DEEPSEEK_V3,
            ModelType.AWS_DEEPSEEK_R1,
            ModelType.NETMIND_QWQ_32B,
            ModelType.NOVITA_DEEPSEEK_V3_TURBO,
            ModelType.NOVITA_DEEPSEEK_R1_TURBO,
            ModelType.NOVITA_DEEPSEEK_V3,
            ModelType.NOVITA_DEEPSEEK_R1_DISTILL_QWEN_14B,
            ModelType.NOVITA_DEEPSEEK_R1_DISTILL_QWEN_32B,
            ModelType.NOVITA_DEEPSEEK_R1,
        }:
            return 64_000
        elif self in {
            ModelType.NOVITA_WIZARDLM_2_8X22B,
        }:
            return 65_535
        elif self in {
            ModelType.NOVITA_QWEN_2_5_V1_72B,
        }:
            return 96_000
        elif self in {
            ModelType.CLAUDE_2_0,
            ModelType.CLAUDE_INSTANT_1_2,
        }:
            return 100_000
        elif self in {
            ModelType.GPT_4O,
            ModelType.GPT_4O_MINI,
            ModelType.GPT_4_TURBO,
            ModelType.O1_PREVIEW,
            ModelType.O1_MINI,
            ModelType.GPT_4_5_PREVIEW,
            ModelType.MISTRAL_LARGE,
            ModelType.MISTRAL_NEMO,
            ModelType.MISTRAL_PIXTRAL_12B,
            ModelType.MISTRAL_8B,
            ModelType.MISTRAL_3B,
            ModelType.QWEN_2_5_CODER_32B,
            ModelType.QWEN_2_5_VL_72B,
            ModelType.QWEN_2_5_72B,
            ModelType.QWEN_2_5_32B,
            ModelType.QWEN_2_5_14B,
            ModelType.COHERE_COMMAND_R,
            ModelType.COHERE_COMMAND_R_PLUS,
            ModelType.COHERE_COMMAND_NIGHTLY,
            ModelType.NVIDIA_LLAMA3_1_8B_INSTRUCT,
            ModelType.NVIDIA_LLAMA3_1_70B_INSTRUCT,
            ModelType.NVIDIA_LLAMA3_1_405B_INSTRUCT,
            ModelType.NVIDIA_LLAMA3_2_1B_INSTRUCT,
            ModelType.NVIDIA_LLAMA3_2_3B_INSTRUCT,
            ModelType.NVIDIA_LLAMA3_3_70B_INSTRUCT,
            ModelType.GROQ_LLAMA_3_3_70B,
            ModelType.SAMBA_LLAMA_3_1_70B,
            ModelType.SGLANG_LLAMA_3_1_8B,
            ModelType.SGLANG_LLAMA_3_1_70B,
            ModelType.SGLANG_LLAMA_3_1_405B,
            ModelType.SGLANG_LLAMA_3_2_1B,
            ModelType.SGLANG_MIXTRAL_NEMO,
            ModelType.MOONSHOT_V1_128K,
            ModelType.GLM_4_PLUS,
            ModelType.GLM_4_AIR,
            ModelType.GLM_4_AIR_0111,
            ModelType.GLM_4_FLASHX,
            ModelType.GLM_4_FLASH,
            ModelType.AWS_LLAMA_3_3_70B_INSTRUCT,
            ModelType.AWS_LLAMA_3_2_90B_INSTRUCT,
            ModelType.AWS_LLAMA_3_2_11B_INSTRUCT,
            ModelType.NETMIND_DEEPSEEK_R1,
            ModelType.NETMIND_DEEPSEEK_V3,
            ModelType.NOVITA_DEEPSEEK_V3_0324,
            ModelType.MISTRAL_MEDIUM_3,
        }:
            return 128_000
        elif self in {
            ModelType.NOVITA_LLAMA_3_2_1B,
        }:
            return 131_000
        elif self in {
            ModelType.GROQ_LLAMA_3_1_8B,
            ModelType.QWEN_PLUS,
            ModelType.QWEN_TURBO,
            ModelType.QWEN_CODER_TURBO,
            ModelType.QWEN_PLUS_LATEST,
            ModelType.QWEN_PLUS_2025_04_28,
            ModelType.QWEN_TURBO_LATEST,
            ModelType.QWEN_TURBO_2025_04_28,
            ModelType.TOGETHER_LLAMA_3_1_8B,
            ModelType.TOGETHER_LLAMA_3_1_70B,
            ModelType.TOGETHER_LLAMA_3_1_405B,
            ModelType.TOGETHER_LLAMA_3_3_70B,
            ModelType.SGLANG_QWEN_2_5_7B,
            ModelType.SGLANG_QWEN_2_5_32B,
            ModelType.SGLANG_QWEN_2_5_72B,
            ModelType.OPENROUTER_LLAMA_3_1_70B,
            ModelType.PPIO_LLAMA_3_3_70B,
            ModelType.OPENROUTER_LLAMA_4_SCOUT,
            ModelType.WATSONX_LLAMA_3_3_70B_INSTRUCT,
            ModelType.WATSONX_LLAMA_3_2_1B_INSTRUCT,
            ModelType.WATSONX_LLAMA_3_2_3B_INSTRUCT,
            ModelType.WATSONX_LLAMA_3_2_11B_VISION_INSTRUCT,
            ModelType.WATSONX_LLAMA_3_2_90B_VISION_INSTRUCT,
            ModelType.WATSONX_LLAMA_GUARD_3_11B_VISION_INSTRUCT,
            ModelType.NOVITA_LLAMA_4_SCOUT_17B,
            ModelType.NOVITA_LLAMA_3_3_70B,
            ModelType.NOVITA_MISTRAL_NEMO,
        }:
            return 131_072
        elif self in {
            ModelType.O1,
            ModelType.O3_MINI,
            ModelType.CLAUDE_2_1,
            ModelType.CLAUDE_3_OPUS,
            ModelType.CLAUDE_3_SONNET,
            ModelType.CLAUDE_3_HAIKU,
            ModelType.CLAUDE_3_5_SONNET,
            ModelType.CLAUDE_3_5_HAIKU,
            ModelType.CLAUDE_3_7_SONNET,
            ModelType.CLAUDE_SONNET_4,
            ModelType.CLAUDE_OPUS_4,
            ModelType.YI_MEDIUM_200K,
            ModelType.AWS_CLAUDE_3_5_SONNET,
            ModelType.AWS_CLAUDE_3_HAIKU,
            ModelType.AWS_CLAUDE_3_SONNET,
            ModelType.AWS_CLAUDE_3_7_SONNET,
            ModelType.AWS_CLAUDE_SONNET_4,
            ModelType.AWS_CLAUDE_OPUS_4,
            ModelType.O4_MINI,
            ModelType.O3,
        }:
            return 200_000
        elif self in {
            ModelType.MISTRAL_CODESTRAL_MAMBA,
            ModelType.OPENROUTER_LLAMA_4_MAVERICK_FREE,
        }:
            return 256_000

        elif self in {
            ModelType.NETMIND_LLAMA_4_SCOUT_17B_16E_INSTRUCT,
        }:
            return 320_000
        elif self in {
            ModelType.OPENROUTER_LLAMA_4_SCOUT_FREE,
            ModelType.NETMIND_LLAMA_4_MAVERICK_17B_128E_INSTRUCT,
        }:
            return 512_000
        elif self in {
            ModelType.GEMINI_2_5_FLASH_PREVIEW,
            ModelType.GEMINI_2_5_PRO_PREVIEW,
            ModelType.GEMINI_2_0_FLASH,
            ModelType.GEMINI_2_0_FLASH_EXP,
            ModelType.GEMINI_2_0_FLASH_THINKING,
            ModelType.GEMINI_2_0_FLASH_LITE,
            ModelType.GEMINI_2_0_FLASH_LITE_PREVIEW,
            ModelType.GEMINI_1_5_FLASH,
            ModelType.GEMINI_1_5_PRO,
            ModelType.GEMINI_2_0_PRO_EXP,  # Not given in doc, assume the same
            ModelType.GLM_4_LONG,
            ModelType.TOGETHER_LLAMA_4_MAVERICK,
            ModelType.OPENROUTER_LLAMA_4_MAVERICK,
            ModelType.GPT_4_1,
            ModelType.GPT_4_1_MINI,
            ModelType.GPT_4_1_NANO,
            ModelType.NOVITA_LLAMA_4_MAVERICK_17B,
        }:
            return 1_048_576
        elif self in {
            ModelType.QWEN_LONG,
            ModelType.TOGETHER_LLAMA_4_SCOUT,
        }:
            return 10_000_000
        else:
            logger.warning(
                f"Unknown model type {self}, set maximum token limit "
                f"to 999_999_999"
            )
            return 999_999_999


class EmbeddingModelType(Enum):
    TEXT_EMBEDDING_ADA_2 = "text-embedding-ada-002"
    TEXT_EMBEDDING_3_SMALL = "text-embedding-3-small"
    TEXT_EMBEDDING_3_LARGE = "text-embedding-3-large"

    JINA_EMBEDDINGS_V3 = "jina-embeddings-v3"
    JINA_CLIP_V2 = "jina-clip-v2"
    JINA_COLBERT_V2 = "jina-colbert-v2"
    JINA_EMBEDDINGS_V2_BASE_CODE = "jina-embeddings-v2-base-code"

    MISTRAL_EMBED = "mistral-embed"

    GEMINI_EMBEDDING_EXP = "gemini-embedding-exp-03-07"

    @property
    def is_openai(self) -> bool:
        r"""Returns whether this type of models is an OpenAI-released model."""
        return self in {
            EmbeddingModelType.TEXT_EMBEDDING_ADA_2,
            EmbeddingModelType.TEXT_EMBEDDING_3_SMALL,
            EmbeddingModelType.TEXT_EMBEDDING_3_LARGE,
        }

    @property
    def is_jina(self) -> bool:
        r"""Returns whether this type of models is an Jina model."""
        return self in {
            EmbeddingModelType.JINA_EMBEDDINGS_V3,
            EmbeddingModelType.JINA_CLIP_V2,
            EmbeddingModelType.JINA_COLBERT_V2,
            EmbeddingModelType.JINA_EMBEDDINGS_V2_BASE_CODE,
        }

    @property
    def is_mistral(self) -> bool:
        r"""Returns whether this type of models is an Mistral-released
        model.
        """
        return self in {
            EmbeddingModelType.MISTRAL_EMBED,
        }

    @property
    def is_gemini(self) -> bool:
        r"""Returns whether this type of models is an Gemini-released model."""
        return self in {
            EmbeddingModelType.GEMINI_EMBEDDING_EXP,
        }

    @property
    def output_dim(self) -> int:
        if self in {
            EmbeddingModelType.JINA_COLBERT_V2,
        }:
            return 128
        elif self in {
            EmbeddingModelType.JINA_EMBEDDINGS_V2_BASE_CODE,
        }:
            return 768
        elif self in {
            EmbeddingModelType.JINA_EMBEDDINGS_V3,
            EmbeddingModelType.JINA_CLIP_V2,
        }:
            return 1024
        elif self is EmbeddingModelType.TEXT_EMBEDDING_ADA_2:
            return 1536
        elif self is EmbeddingModelType.TEXT_EMBEDDING_3_SMALL:
            return 1536
        elif self is EmbeddingModelType.TEXT_EMBEDDING_3_LARGE:
            return 3072
        elif self is EmbeddingModelType.MISTRAL_EMBED:
            return 1024
        elif self is EmbeddingModelType.GEMINI_EMBEDDING_EXP:
            return 3072
        else:
            raise ValueError(f"Unknown model type {self}.")


class GeminiEmbeddingTaskType(str, Enum):
    r"""Task types for Gemini embedding models.

    For more information, please refer to:
    https://ai.google.dev/gemini-api/docs/embeddings#task-types
    """

    SEMANTIC_SIMILARITY = "SEMANTIC_SIMILARITY"
    CLASSIFICATION = "CLASSIFICATION"
    CLUSTERING = "CLUSTERING"
    RETRIEVAL_DOCUMENT = "RETRIEVAL_DOCUMENT"
    RETRIEVAL_QUERY = "RETRIEVAL_QUERY"
    QUESTION_ANSWERING = "QUESTION_ANSWERING"
    FACT_VERIFICATION = "FACT_VERIFICATION"
    CODE_RETRIEVAL_QUERY = "CODE_RETRIEVAL_QUERY"


class TaskType(Enum):
    AI_SOCIETY = "ai_society"
    CODE = "code"
    MISALIGNMENT = "misalignment"
    TRANSLATION = "translation"
    EVALUATION = "evaluation"
    SOLUTION_EXTRACTION = "solution_extraction"
    ROLE_DESCRIPTION = "role_description"
    GENERATE_TEXT_EMBEDDING_DATA = "generate_text_embedding_data"
    OBJECT_RECOGNITION = "object_recognition"
    IMAGE_CRAFT = "image_craft"
    MULTI_CONDITION_IMAGE_CRAFT = "multi_condition_image_craft"
    DEFAULT = "default"
    VIDEO_DESCRIPTION = "video_description"


class VectorDistance(Enum):
    r"""Distance metrics used in a vector database."""

    DOT = "dot"
    r"""Dot product. https://en.wikipedia.org/wiki/Dot_product"""

    COSINE = "cosine"
    r"""Cosine similarity. https://en.wikipedia.org/wiki/Cosine_similarity"""

    EUCLIDEAN = "euclidean"
    r"""Euclidean distance. https://en.wikipedia.org/wiki/Euclidean_distance"""


class OpenAIBackendRole(Enum):
    ASSISTANT = "assistant"
    SYSTEM = "system"
    DEVELOPER = "developer"
    USER = "user"
    FUNCTION = "function"
    TOOL = "tool"


class TerminationMode(Enum):
    ANY = "any"
    ALL = "all"


class OpenAIImageTypeMeta(EnumMeta):
    def __contains__(cls, image_type: object) -> bool:
        try:
            cls(image_type)
        except ValueError:
            return False
        return True


class OpenAIImageType(Enum, metaclass=OpenAIImageTypeMeta):
    r"""Image types supported by OpenAI vision model."""

    # https://platform.openai.com/docs/guides/vision
    PNG = "png"
    JPEG = "jpeg"
    JPG = "jpg"
    WEBP = "webp"
    GIF = "gif"


class OpenAIVisionDetailType(Enum):
    AUTO = "auto"
    LOW = "low"
    HIGH = "high"


class StorageType(Enum):
    MILVUS = "milvus"
    QDRANT = "qdrant"
    TIDB = "tidb"


class OpenAPIName(Enum):
    COURSERA = "coursera"
    KLARNA = "klarna"
    SPEAK = "speak"
    NASA_APOD = "nasa_apod"
    BIZTOC = "biztoc"
    CREATE_QR_CODE = "create_qr_code"
    OUTSCHOOL = "outschool"
    WEB_SCRAPER = "web_scraper"


class ModelPlatformType(Enum):
    DEFAULT = os.getenv("DEFAULT_MODEL_PLATFORM_TYPE", "openai")

    OPENAI = "openai"
    AWS_BEDROCK = "aws-bedrock"
    AZURE = "azure"
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"
    LITELLM = "litellm"
    LMSTUDIO = "lmstudio"
    ZHIPU = "zhipuai"
    GEMINI = "gemini"
    VLLM = "vllm"
    MISTRAL = "mistral"
    REKA = "reka"
    TOGETHER = "together"
    STUB = "stub"
    OPENAI_COMPATIBLE_MODEL = "openai-compatible-model"
    SAMBA = "samba-nova"
    COHERE = "cohere"
    YI = "lingyiwanwu"
    QWEN = "tongyi-qianwen"
    NVIDIA = "nvidia"
    DEEPSEEK = "deepseek"
    PPIO = "ppio"
    SGLANG = "sglang"
    INTERNLM = "internlm"
    MOONSHOT = "moonshot"
    MODELSCOPE = "modelscope"
    SILICONFLOW = "siliconflow"
    AIML = "aiml"
    VOLCANO = "volcano"
    NETMIND = "netmind"
    NOVITA = "novita"
    WATSONX = "watsonx"

    @classmethod
    def from_name(cls, name):
        r"""Returns the ModelPlatformType enum value from a string."""
        for model_platfrom_type in cls:
            if model_platfrom_type.value == name:
                return model_platfrom_type
        raise ValueError(f"Unknown ModelPlatformType name: {name}")

    @property
    def is_openai(self) -> bool:
        r"""Returns whether this platform is openai."""
        return self is ModelPlatformType.OPENAI

    @property
    def is_aws_bedrock(self) -> bool:
        r"""Returns whether this platform is aws-bedrock."""
        return self is ModelPlatformType.AWS_BEDROCK

    @property
    def is_azure(self) -> bool:
        r"""Returns whether this platform is azure."""
        return self is ModelPlatformType.AZURE

    @property
    def is_anthropic(self) -> bool:
        r"""Returns whether this platform is anthropic."""
        return self is ModelPlatformType.ANTHROPIC

    @property
    def is_groq(self) -> bool:
        r"""Returns whether this platform is groq."""
        return self is ModelPlatformType.GROQ

    @property
    def is_openrouter(self) -> bool:
        r"""Returns whether this platform is openrouter."""
        return self is ModelPlatformType.OPENROUTER

    @property
    def is_lmstudio(self) -> bool:
        r"""Returns whether this platform is lmstudio."""
        return self is ModelPlatformType.LMSTUDIO

    @property
    def is_ollama(self) -> bool:
        r"""Returns whether this platform is ollama."""
        return self is ModelPlatformType.OLLAMA

    @property
    def is_vllm(self) -> bool:
        r"""Returns whether this platform is vllm."""
        return self is ModelPlatformType.VLLM

    @property
    def is_sglang(self) -> bool:
        r"""Returns whether this platform is sglang."""
        return self is ModelPlatformType.SGLANG

    @property
    def is_together(self) -> bool:
        r"""Returns whether this platform is together."""
        return self is ModelPlatformType.TOGETHER

    @property
    def is_litellm(self) -> bool:
        r"""Returns whether this platform is litellm."""
        return self is ModelPlatformType.LITELLM

    @property
    def is_zhipuai(self) -> bool:
        r"""Returns whether this platform is zhipu."""
        return self is ModelPlatformType.ZHIPU

    @property
    def is_mistral(self) -> bool:
        r"""Returns whether this platform is mistral."""
        return self is ModelPlatformType.MISTRAL

    @property
    def is_openai_compatible_model(self) -> bool:
        r"""Returns whether this is a platform supporting openai
        compatibility"""
        return self is ModelPlatformType.OPENAI_COMPATIBLE_MODEL

    @property
    def is_gemini(self) -> bool:
        r"""Returns whether this platform is Gemini."""
        return self is ModelPlatformType.GEMINI

    @property
    def is_reka(self) -> bool:
        r"""Returns whether this platform is Reka."""
        return self is ModelPlatformType.REKA

    @property
    def is_samba(self) -> bool:
        r"""Returns whether this platform is Samba Nova."""
        return self is ModelPlatformType.SAMBA

    @property
    def is_cohere(self) -> bool:
        r"""Returns whether this platform is Cohere."""
        return self is ModelPlatformType.COHERE

    @property
    def is_yi(self) -> bool:
        r"""Returns whether this platform is Yi."""
        return self is ModelPlatformType.YI

    @property
    def is_qwen(self) -> bool:
        r"""Returns whether this platform is Qwen."""
        return self is ModelPlatformType.QWEN

    @property
    def is_nvidia(self) -> bool:
        r"""Returns whether this platform is Nvidia."""
        return self is ModelPlatformType.NVIDIA

    @property
    def is_deepseek(self) -> bool:
        r"""Returns whether this platform is DeepSeek."""
        return self is ModelPlatformType.DEEPSEEK

    @property
    def is_netmind(self) -> bool:
        r"""Returns whether this platform is Netmind."""
        return self is ModelPlatformType.NETMIND

    @property
    def is_ppio(self) -> bool:
        r"""Returns whether this platform is PPIO."""
        return self is ModelPlatformType.PPIO

    @property
    def is_internlm(self) -> bool:
        r"""Returns whether this platform is InternLM."""
        return self is ModelPlatformType.INTERNLM

    @property
    def is_moonshot(self) -> bool:
        r"""Returns whether this platform is Moonshot model."""
        return self is ModelPlatformType.MOONSHOT

    @property
    def is_modelscope(self) -> bool:
        r"""Returns whether this platform is ModelScope model."""
        return self is ModelPlatformType.MODELSCOPE

    @property
    def is_siliconflow(self) -> bool:
        r"""Returns whether this platform is SiliconFlow."""
        return self is ModelPlatformType.SILICONFLOW

    @property
    def is_aiml(self) -> bool:
        r"""Returns whether this platform is AIML."""
        return self is ModelPlatformType.AIML

    @property
    def is_volcano(self) -> bool:
        r"""Returns whether this platform is volcano."""
        return self is ModelPlatformType.VOLCANO

    @property
    def is_novita(self) -> bool:
        r"""Returns whether this platform is Novita."""
        return self is ModelPlatformType.NOVITA

    @property
    def is_watsonx(self) -> bool:
        r"""Returns whether this platform is WatsonX."""
        return self is ModelPlatformType.WATSONX


class AudioModelType(Enum):
    TTS_1 = "tts-1"
    TTS_1_HD = "tts-1-hd"

    @property
    def is_openai(self) -> bool:
        r"""Returns whether this type of audio models is an OpenAI-released
        model."""
        return self in {
            AudioModelType.TTS_1,
            AudioModelType.TTS_1_HD,
        }


class VoiceType(Enum):
    ALLOY = "alloy"
    ECHO = "echo"
    FABLE = "fable"
    ONYX = "onyx"
    NOVA = "nova"
    SHIMMER = "shimmer"

    @property
    def is_openai(self) -> bool:
        r"""Returns whether this type of voice is an OpenAI-released voice."""
        return self in {
            VoiceType.ALLOY,
            VoiceType.ECHO,
            VoiceType.FABLE,
            VoiceType.ONYX,
            VoiceType.NOVA,
            VoiceType.SHIMMER,
        }


class JinaReturnFormat(Enum):
    DEFAULT = None
    MARKDOWN = "markdown"
    HTML = "html"
    TEXT = "text"


class HuggingFaceRepoType(str, Enum):
    DATASET = "dataset"
    MODEL = "model"
    SPACE = "space"
