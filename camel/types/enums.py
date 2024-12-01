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

from camel.types.unified_model_type import UnifiedModelType


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
    O1_PREVIEW = "o1-preview"
    O1_MINI = "o1-mini"

    GLM_4 = "glm-4"
    GLM_4V = 'glm-4v'
    GLM_3_TURBO = "glm-3-turbo"

    GROQ_LLAMA_3_1_8B = "llama-3.1-8b-instant"
    GROQ_LLAMA_3_1_70B = "llama-3.1-70b-versatile"
    GROQ_LLAMA_3_1_405B = "llama-3.1-405b-reasoning"
    GROQ_LLAMA_3_8B = "llama3-8b-8192"
    GROQ_LLAMA_3_70B = "llama3-70b-8192"
    GROQ_MIXTRAL_8_7B = "mixtral-8x7b-32768"
    GROQ_GEMMA_7B_IT = "gemma-7b-it"
    GROQ_GEMMA_2_9B_IT = "gemma2-9b-it"

    STUB = "stub"

    # Legacy anthropic models
    # NOTE: anthropic legacy models only Claude 2.1 has system prompt support
    CLAUDE_2_1 = "claude-2.1"
    CLAUDE_2_0 = "claude-2.0"
    CLAUDE_INSTANT_1_2 = "claude-instant-1.2"

    # Claude3 models
    CLAUDE_3_OPUS = "claude-3-opus-20240229"
    CLAUDE_3_SONNET = "claude-3-sonnet-20240229"
    CLAUDE_3_HAIKU = "claude-3-haiku-20240307"
    CLAUDE_3_5_SONNET = "claude-3-5-sonnet-20240620"

    # Nvidia models
    NVIDIA_NEMOTRON_340B = "nvidia/nemotron-4-340b-instruct"
    NVIDIA_NEMOTRON_340B_REWARD = "nvidia/nemotron-4-340b-reward"
    NVIDIA_YI_LARGE = "01-ai/yi-large"
    NVIDIA_MISTRAL_LARGE = "mistralai/mistral-large"
    NVIDIA_LLAMA3_70B = "meta/llama3-70b"
    NVIDIA_MIXTRAL_8X7B = "mistralai/mixtral-8x7b-instruct"
    NVIDIA_LLAMA31_8B_INSTRUCT = "meta/llama-3.1-8b-instruct"
    NVIDIA_LLAMA31_70B_INSTRUCT = "meta/llama-3.1-70b-instruct"
    NVIDIA_LLAMA31_405B_INSTRUCT = "meta/llama-3.1-405b-instruct"
    NVIDIA_LLAMA32_1B_INSTRUCT = "meta/llama-3.2-1b-instruct"
    NVIDIA_LLAMA32_3B_INSTRUCT = "meta/llama-3.2-3b-instruct"

    # Gemini models
    GEMINI_1_5_FLASH = "gemini-1.5-flash"
    GEMINI_1_5_PRO = "gemini-1.5-pro"
    GEMINI_EXP_1114 = "gemini-exp-1114"

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
    QWEN_LONG = "qwen-long"
    QWEN_VL_MAX = "qwen-vl-max"
    QWEN_VL_PLUS = "qwen-vl-plus"
    QWEN_MATH_PLUS = "qwen-math-plus"
    QWEN_MATH_TURBO = "qwen-math-turbo"
    QWEN_CODER_TURBO = "qwen-coder-turbo"
    QWEN_2_5_CODER_32B = "qwen2.5-coder-32b-instruct"
    QWEN_2_5_72B = "qwen2.5-72b-instruct"
    QWEN_2_5_32B = "qwen2.5-32b-instruct"
    QWEN_2_5_14B = "qwen2.5-14b-instruct"
    QWEN_QWQ_32B = "qwq-32b-preview"

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

    def __str__(self):
        return self.value

    def __new__(cls, value) -> "ModelType":
        return cast("ModelType", UnifiedModelType.__new__(cls, value))

    @property
    def value_for_tiktoken(self) -> str:
        if self.is_openai:
            return self.value
        return "gpt-4o-mini"

    @property
    def support_native_tool_calling(self) -> bool:
        return any([self.is_openai, self.is_gemini, self.is_mistral])

    @property
    def is_openai(self) -> bool:
        r"""Returns whether this type of models is an OpenAI-released model."""
        return self in {
            ModelType.GPT_3_5_TURBO,
            ModelType.GPT_4,
            ModelType.GPT_4_TURBO,
            ModelType.GPT_4O,
            ModelType.GPT_4O_MINI,
            ModelType.O1_PREVIEW,
            ModelType.O1_MINI,
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
        }

    @property
    def is_zhipuai(self) -> bool:
        r"""Returns whether this type of models is an ZhipuAI model."""
        return self in {
            ModelType.GLM_3_TURBO,
            ModelType.GLM_4,
            ModelType.GLM_4V,
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
        }

    @property
    def is_groq(self) -> bool:
        r"""Returns whether this type of models is served by Groq."""
        return self in {
            ModelType.GROQ_LLAMA_3_1_8B,
            ModelType.GROQ_LLAMA_3_1_70B,
            ModelType.GROQ_LLAMA_3_1_405B,
            ModelType.GROQ_LLAMA_3_8B,
            ModelType.GROQ_LLAMA_3_70B,
            ModelType.GROQ_MIXTRAL_8_7B,
            ModelType.GROQ_GEMMA_7B_IT,
            ModelType.GROQ_GEMMA_2_9B_IT,
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
        }

    @property
    def is_nvidia(self) -> bool:
        r"""Returns whether this type of models is a NVIDIA model."""
        return self in {
            ModelType.NVIDIA_NEMOTRON_340B,
            ModelType.NVIDIA_NEMOTRON_340B_REWARD,
            ModelType.NVIDIA_YI_LARGE,
            ModelType.NVIDIA_MISTRAL_LARGE,
            ModelType.NVIDIA_LLAMA3_70B,
            ModelType.NVIDIA_MIXTRAL_8X7B,
            ModelType.NVIDIA_LLAMA31_8B_INSTRUCT,
            ModelType.NVIDIA_LLAMA31_70B_INSTRUCT,
            ModelType.NVIDIA_LLAMA31_405B_INSTRUCT,
            ModelType.NVIDIA_LLAMA32_1B_INSTRUCT,
            ModelType.NVIDIA_LLAMA32_3B_INSTRUCT,
        }

    @property
    def is_gemini(self) -> bool:
        r"""Returns whether this type of models is Gemini model.

        Returns:
            bool: Whether this type of models is gemini.
        """
        return self in {
            ModelType.GEMINI_1_5_FLASH,
            ModelType.GEMINI_1_5_PRO,
            ModelType.GEMINI_EXP_1114,
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
            ModelType.QWEN_2_5_72B,
            ModelType.QWEN_2_5_32B,
            ModelType.QWEN_2_5_14B,
            ModelType.QWEN_QWQ_32B,
        }

    @property
    def is_deepseek(self) -> bool:
        return self in {
            ModelType.DEEPSEEK_CHAT,
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
            ModelType.NVIDIA_NEMOTRON_340B,
            ModelType.NVIDIA_NEMOTRON_340B_REWARD,
        }:
            return 4_096
        elif self in {
            ModelType.GPT_4,
            ModelType.GROQ_LLAMA_3_8B,
            ModelType.GROQ_LLAMA_3_70B,
            ModelType.GROQ_GEMMA_7B_IT,
            ModelType.GROQ_GEMMA_2_9B_IT,
            ModelType.GLM_3_TURBO,
            ModelType.GLM_4,
            ModelType.QWEN_VL_PLUS,
            ModelType.NVIDIA_LLAMA3_70B,
        }:
            return 8_192
        elif self in {
            ModelType.GPT_3_5_TURBO,
            ModelType.YI_LIGHTNING,
            ModelType.YI_MEDIUM,
            ModelType.YI_LARGE_TURBO,
            ModelType.YI_VISION,
            ModelType.YI_SPARK,
            ModelType.YI_LARGE_RAG,
        }:
            return 16_384
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
        }:
            return 32_768
        elif self in {
            ModelType.MISTRAL_MIXTRAL_8x22B,
            ModelType.DEEPSEEK_CHAT,
        }:
            return 64_000
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
            ModelType.MISTRAL_LARGE,
            ModelType.MISTRAL_NEMO,
            ModelType.MISTRAL_PIXTRAL_12B,
            ModelType.MISTRAL_8B,
            ModelType.MISTRAL_3B,
            ModelType.QWEN_2_5_CODER_32B,
            ModelType.QWEN_2_5_72B,
            ModelType.QWEN_2_5_32B,
            ModelType.QWEN_2_5_14B,
            ModelType.COHERE_COMMAND_R,
            ModelType.COHERE_COMMAND_R_PLUS,
            ModelType.COHERE_COMMAND_NIGHTLY,
            ModelType.NVIDIA_LLAMA31_8B_INSTRUCT,
            ModelType.NVIDIA_LLAMA31_70B_INSTRUCT,
            ModelType.NVIDIA_LLAMA31_405B_INSTRUCT,
            ModelType.NVIDIA_LLAMA32_1B_INSTRUCT,
            ModelType.NVIDIA_LLAMA32_3B_INSTRUCT,
        }:
            return 128_000
        elif self in {
            ModelType.GROQ_LLAMA_3_1_8B,
            ModelType.GROQ_LLAMA_3_1_70B,
            ModelType.GROQ_LLAMA_3_1_405B,
            ModelType.QWEN_PLUS,
            ModelType.QWEN_TURBO,
            ModelType.QWEN_CODER_TURBO,
        }:
            return 131_072
        elif self in {
            ModelType.CLAUDE_2_1,
            ModelType.CLAUDE_3_OPUS,
            ModelType.CLAUDE_3_SONNET,
            ModelType.CLAUDE_3_HAIKU,
            ModelType.CLAUDE_3_5_SONNET,
            ModelType.YI_MEDIUM_200K,
        }:
            return 200_000
        elif self in {
            ModelType.MISTRAL_CODESTRAL_MAMBA,
        }:
            return 256_000
        elif self in {
            ModelType.GEMINI_1_5_FLASH,
            ModelType.GEMINI_1_5_PRO,
            ModelType.GEMINI_EXP_1114,  # Not given in docs, assuming the same
        }:
            return 1_048_576
        elif self in {
            ModelType.QWEN_LONG,
        }:
            return 10_000_000
        else:
            raise ValueError("Unknown model type")


class EmbeddingModelType(Enum):
    TEXT_EMBEDDING_ADA_2 = "text-embedding-ada-002"
    TEXT_EMBEDDING_3_SMALL = "text-embedding-3-small"
    TEXT_EMBEDDING_3_LARGE = "text-embedding-3-large"

    MISTRAL_EMBED = "mistral-embed"

    @property
    def is_openai(self) -> bool:
        r"""Returns whether this type of models is an OpenAI-released model."""
        return self in {
            EmbeddingModelType.TEXT_EMBEDDING_ADA_2,
            EmbeddingModelType.TEXT_EMBEDDING_3_SMALL,
            EmbeddingModelType.TEXT_EMBEDDING_3_LARGE,
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
    def output_dim(self) -> int:
        if self is EmbeddingModelType.TEXT_EMBEDDING_ADA_2:
            return 1536
        elif self is EmbeddingModelType.TEXT_EMBEDDING_3_SMALL:
            return 1536
        elif self is EmbeddingModelType.TEXT_EMBEDDING_3_LARGE:
            return 3072
        elif self is EmbeddingModelType.MISTRAL_EMBED:
            return 1024
        else:
            raise ValueError(f"Unknown model type {self}.")


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
    AZURE = "azure"
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    OLLAMA = "ollama"
    LITELLM = "litellm"
    ZHIPU = "zhipuai"
    GEMINI = "gemini"
    VLLM = "vllm"
    MISTRAL = "mistral"
    REKA = "reka"
    TOGETHER = "together"
    OPENAI_COMPATIBLE_MODEL = "openai-compatible-model"
    SAMBA = "samba-nova"
    COHERE = "cohere"
    YI = "lingyiwanwu"
    QWEN = "tongyi-qianwen"
    NVIDIA = "nvidia"
    DEEPSEEK = "deepseek"

    @property
    def is_openai(self) -> bool:
        r"""Returns whether this platform is openai."""
        return self is ModelPlatformType.OPENAI

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
    def is_ollama(self) -> bool:
        r"""Returns whether this platform is ollama."""
        return self is ModelPlatformType.OLLAMA

    @property
    def is_vllm(self) -> bool:
        r"""Returns whether this platform is vllm."""
        return self is ModelPlatformType.VLLM

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
