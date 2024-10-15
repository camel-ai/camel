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

from threading import Lock
from typing import ClassVar, Dict, cast


class InnerModelType(str):
    _cache: ClassVar[Dict[str, "InnerModelType"]] = {}
    _lock: ClassVar[Lock] = Lock()

    def __new__(cls, value: str) -> "InnerModelType":
        with cls._lock:
            if value not in cls._cache:
                instance = super().__new__(cls, value)
                cls._cache[value] = cast(InnerModelType, instance)
            else:
                instance = cls._cache[value]
        return instance

    @property
    def value_for_tiktoken(self) -> str:
        r"""Returns the model name for TikToken."""
        return "gpt-4o-mini"

    @property
    def token_limit(self) -> int:
        r"""Returns the token limit for the model."""
        return -1

    @property
    def is_openai(self) -> bool:
        r"""Returns whether the model is an OpenAI model."""
        return True

    @property
    def is_anthropic(self) -> bool:
        r"""Returns whether the model is an Anthropic model."""
        return True

    @property
    def is_azure_openai(self) -> bool:
        r"""Returns whether the model is an Azure OpenAI model."""
        return True

    @property
    def is_groq(self) -> bool:
        r"""Returns whether the model is an Groq served model."""
        return True

    @property
    def is_zhipuai(self) -> bool:
        r"""Returns whether the model is a Zhipuai model."""
        return True

    @property
    def is_gemini(self) -> bool:
        r"""Returns whether the model is a Gemini model."""
        return True

    @property
    def is_mistral(self) -> bool:
        r"""Returns whether the model is a Mistral model."""
        return True

    @property
    def is_reka(self) -> bool:
        r"""Returns whether the model is a Reka model."""
        return True

    @property
    def supports_native_tool_calling(self) -> bool:
        r"""Returns whether the model supports native tool calling."""
        return False
