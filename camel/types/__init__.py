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
from .enums import (
    AudioModelType,
    EmbeddingModelType,
    GeminiEmbeddingTaskType,
    HuggingFaceRepoType,
    ModelPlatformType,
    ModelType,
    OpenAIBackendRole,
    OpenAIImageType,
    OpenAIVisionDetailType,
    OpenAPIName,
    RoleType,
    StorageType,
    TaskType,
    TerminationMode,
    VectorDistance,
    VoiceType,
)
from .mcp_registries import (
    ACIRegistryConfig,
    BaseMCPRegistryConfig,
    MCPRegistryType,
    SmitheryRegistryConfig,
)
from .openai_types import (
    NOT_GIVEN,
    ChatCompletion,
    ChatCompletionAssistantMessageParam,
    ChatCompletionChunk,
    ChatCompletionMessage,
    ChatCompletionMessageParam,
    ChatCompletionMessageToolCall,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionUserMessageParam,
    Choice,
    CompletionUsage,
    NotGiven,
    ParsedChatCompletion,
)
from .unified_model_type import UnifiedModelType

__all__ = [
    'ACIRegistryConfig',
    'AudioModelType',
    'BaseMCPRegistryConfig',
    'ChatCompletion',
    'ChatCompletionAssistantMessageParam',
    'ChatCompletionChunk',
    'ChatCompletionMessage',
    'ChatCompletionMessageParam',
    'ChatCompletionMessageToolCall',
    'ChatCompletionSystemMessageParam',
    'ChatCompletionToolMessageParam',
    'ChatCompletionUserMessageParam',
    'Choice',
    'CompletionUsage',
    'EmbeddingModelType',
    'GeminiEmbeddingTaskType',
    'HuggingFaceRepoType',
    'MCPRegistryType',
    'ModelPlatformType',
    'ModelType',
    'NOT_GIVEN',
    'NotGiven',
    'OpenAIBackendRole',
    'OpenAIImageType',
    'OpenAIVisionDetailType',
    'OpenAPIName',
    'ParsedChatCompletion',
    'RoleType',
    'SmitheryRegistryConfig',
    'StorageType',
    'TaskType',
    'TerminationMode',
    'UnifiedModelType',
    'VectorDistance',
    'VoiceType',
]
