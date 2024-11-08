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
from camel.types import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionFunctionMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)
from .axolotl.sharegpt.functions.function_call_formatter import (
    FunctionCallFormatter,
)
from .axolotl.sharegpt.functions.hermes.hermes_function_formatter import (
    HermesFunctionFormatter,
)
from .axolotl.sharegpt.sharegpt_conversation import (
    ShareGPTConversation,
)
from .axolotl.sharegpt.sharegpt_message import (
    ShareGPTMessage,
)

OpenAISystemMessage = ChatCompletionSystemMessageParam
OpenAIAssistantMessage = ChatCompletionAssistantMessageParam
OpenAIUserMessage = ChatCompletionUserMessageParam
OpenAIFunctionMessage = ChatCompletionFunctionMessageParam
OpenAIMessage = ChatCompletionMessageParam


from .base import BaseMessage  # noqa: E402
from .func_message import FunctionCallingMessage  # noqa: E402

__all__ = [
    'OpenAISystemMessage',
    'OpenAIAssistantMessage',
    'OpenAIUserMessage',
    'OpenAIFunctionMessage',
    'OpenAIMessage',
    'FunctionCallFormatter',
    'HermesFunctionFormatter',
    'ShareGPTConversation',
    'ShareGPTMessage',
    'BaseMessage',
    'FunctionCallingMessage',
]
