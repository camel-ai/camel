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

from camel.configs import DeepSeekConfig
from camel.logger import get_logger
from camel.models.openai_compatible_model import OpenAICompatibleModel
from camel.types import (
    ModelType,
    StructuredOutputMode,
)
from camel.utils import (
    BaseTokenCounter,
    api_keys_required,
)

logger = get_logger(__name__)

REASONSER_UNSUPPORTED_PARAMS = [
    "temperature",
    "top_p",
    "presence_penalty",
    "frequency_penalty",
    "logprobs",
    "top_logprobs",
    "tools",
]


class DeepSeekModel(OpenAICompatibleModel):
    r"""DeepSeek API in a unified OpenAICompatibleModel interface.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created.
        model_config_dict (Optional[Dict[str, Any]], optional): A dictionary
            that will be fed into:obj:`openai.ChatCompletion.create()`. If
            :obj:`None`, :obj:`DeepSeekConfig().as_dict()` will be used.
            (default: :obj:`None`)
        api_key (Optional[str], optional): The API key for authenticating with
            the DeepSeek service. (default: :obj:`None`)
        url (Optional[str], optional): The url to the DeepSeek service.
            (default: :obj:`https://api.deepseek.com`)
        token_counter (Optional[BaseTokenCounter], optional): Token counter to
            use for the model. If not provided, :obj:`OpenAITokenCounter`
            will be used. (default: :obj:`None`)
        timeout (Optional[float], optional): The timeout value in seconds for
            API calls. If not provided, will fall back to the MODEL_TIMEOUT
            environment variable or default to 180 seconds.
            (default: :obj:`None`)
        max_retries (int, optional): Maximum number of retries for API calls.
            (default: :obj:`3`)
        **kwargs (Any): Additional arguments to pass to the client
            initialization.

    References:
        https://api-docs.deepseek.com/
    """

    @api_keys_required(
        [
            ("api_key", "DEEPSEEK_API_KEY"),
        ]
    )
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
            model_config_dict = DeepSeekConfig().as_dict()
        api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        url = url or os.environ.get(
            "DEEPSEEK_API_BASE_URL",
            "https://api.deepseek.com",
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

    @property
    def structured_output_mode(self) -> StructuredOutputMode:
        return StructuredOutputMode.JSON_OBJECT

    def _prepare_request_config(
        self,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        r"""Prepare request config with DeepSeek-specific adjustments.

        - For Reasoner models, removes unsupported parameters.
        - Removes ``strict`` from tool function definitions (unsupported
          by DeepSeek).
        """
        request_config = super()._prepare_request_config(tools)

        if self.model_type in [ModelType.DEEPSEEK_REASONER]:
            logger.warning(
                "Warning: You are using an DeepSeek Reasoner model, "
                "which has certain limitations, reference: "
                "`https://api-docs.deepseek.com/guides/reasoning_model"
                "#api-parameters`.",
            )
            for key in REASONSER_UNSUPPORTED_PARAMS:
                request_config.pop(key, None)

        if tools:
            for tool in request_config.get("tools", []):
                tool.get("function", {}).pop("strict", None)

        return request_config
