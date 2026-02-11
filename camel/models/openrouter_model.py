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
import os
from typing import Any, Dict, List, Optional, Union

from camel.configs import OpenRouterConfig
from camel.models.openai_compatible_model import OpenAICompatibleModel
from camel.types import ModelType
from camel.utils import (
    BaseTokenCounter,
    api_keys_required,
)


class OpenRouterModel(OpenAICompatibleModel):
    r"""LLM API served by OpenRouter in a unified OpenAICompatibleModel
    interface.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created.
        model_config_dict (Optional[Dict[str, Any]], optional): A dictionary
            that will be fed into:obj:`openai.ChatCompletion.create()`.
            If:obj:`None`, :obj:`GroqConfig().as_dict()` will be used.
            (default: :obj:`None`)
        api_key (Optional[str], optional): The API key for authenticating
            with the OpenRouter service. (default: :obj:`None`).
        url (Optional[str], optional): The url to the OpenRouter service.
            (default: :obj:`None`)
        token_counter (Optional[BaseTokenCounter], optional): Token counter to
            use for the model. If not provided, :obj:`OpenAITokenCounter(
            ModelType.GPT_4O_MINI)` will be used.
            (default: :obj:`None`)
        timeout (Optional[float], optional): The timeout value in seconds for
            API calls. If not provided, will fall back to the MODEL_TIMEOUT
            environment variable or default to 180 seconds.
            (default: :obj:`None`)
        max_retries (int, optional): Maximum number of retries for API calls.
            (default: :obj:`3`)
        **kwargs (Any): Additional arguments to pass to the client
            initialization.
    """

    @api_keys_required([("api_key", "OPENROUTER_API_KEY")])
    def __init__(
        self,
        model_type: Union[ModelType, str],
        model_config_dict: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        token_counter: Optional[BaseTokenCounter] = None,
        timeout: Optional[float] = None,
        max_retries: int = 3,
        **kwargs: Any,
    ) -> None:
        if model_config_dict is None:
            model_config_dict = OpenRouterConfig().as_dict()
        api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        url = url or os.environ.get(
            "OPENROUTER_API_BASE_URL", "https://openrouter.ai/api/v1"
        )
        timeout = timeout or float(os.environ.get("MODEL_TIMEOUT", 180))
        super().__init__(
            model_type=model_type,
            model_config_dict=model_config_dict,
            api_key=api_key,
            url=url,
            token_counter=token_counter,
            timeout=timeout,
            max_retries=max_retries,
            **kwargs,
        )
    def _prepare_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not self.model_config_dict.get("enable_prompt_caching"):
            return messages

        implicit_caching_prefixes = (
            "openai/",
            "deepseek/",
            "google/gemini-2.5-pro",
            "google/gemini-2.5-flash",
            "x-ai/",
            "moonshotai/"

        )

        model_name = str(self.model_type).lower()

        needs_explicit_caching = not any(
            model_name.startswith(p) for p in implicit_caching_prefixes
        )

        # 4. Apply transformation only if needed
        if needs_explicit_caching and messages:
            if messages[0].get("role") == "system":
                sys_msg = messages[0]
                content = sys_msg.get("content")

                ttl = self.model_config_dict.get("cache_ttl", "5m")
                cache_obj = {"type": "ephemeral"}

                if model_name.startswith("anthropic/") and ttl == "1h":
                    cache_obj["ttl"] = "1h"

                if isinstance(content, str):
                    sys_msg["content"] = [
                        {
                            "type": "text",
                            "text": content,
                            "cache_control": cache_obj,
                        }
                    ]
                elif isinstance(content, list) and content:
                    content[-1]["cache_control"] = cache_obj

        return messages
