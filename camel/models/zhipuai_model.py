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
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel

from camel.configs import ZhipuAIConfig
from camel.logger import get_logger
from camel.messages import OpenAIMessage
from camel.models._utils import try_modify_message_with_format
from camel.models.openai_compatible_model import OpenAICompatibleModel
from camel.types import (
    ChatCompletion,
    ModelType,
)
from camel.utils import (
    BaseTokenCounter,
    api_keys_required,
)

logger = get_logger(__name__)


class ZhipuAIModel(OpenAICompatibleModel):
    r"""ZhipuAI API in a unified OpenAICompatibleModel interface.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created, one of GLM_* series.
        model_config_dict (Optional[Dict[str, Any]], optional): A dictionary
            that will be fed into:obj:`openai.ChatCompletion.create()`. If
            :obj:`None`, :obj:`ZhipuAIConfig().as_dict()` will be used.
            (default: :obj:`None`)
        api_key (Optional[str], optional): The API key for authenticating with
            the ZhipuAI service. (default: :obj:`None`)
        url (Optional[str], optional): The url to the ZhipuAI service.
            (default: :obj:`https://open.bigmodel.cn/api/paas/v4/`)
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

    @api_keys_required(
        [
            ("api_key", 'ZHIPUAI_API_KEY'),
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
            model_config_dict = ZhipuAIConfig().as_dict()
        api_key = api_key or os.environ.get("ZHIPUAI_API_KEY")
        url = url or os.environ.get(
            "ZHIPUAI_API_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/"
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

    def _request_parse(
        self,
        messages: List[OpenAIMessage],
        response_format: Type[BaseModel],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatCompletion:
        import copy

        request_config = copy.deepcopy(self.model_config_dict)
        request_config.pop("stream", None)
        if tools is not None:
            request_config["tools"] = tools

        try_modify_message_with_format(messages[-1], response_format)
        request_config["response_format"] = {"type": "json_object"}
        try:
            return self._client.beta.chat.completions.parse(
                messages=messages,
                model=self.model_type,
                **request_config,
            )
        except Exception as e:
            logger.error(f"Fallback attempt also failed: {e}")
            raise

    async def _arequest_parse(
        self,
        messages: List[OpenAIMessage],
        response_format: Type[BaseModel],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatCompletion:
        import copy

        request_config = copy.deepcopy(self.model_config_dict)
        request_config.pop("stream", None)
        if tools is not None:
            request_config["tools"] = tools
        try_modify_message_with_format(messages[-1], response_format)
        request_config["response_format"] = {"type": "json_object"}
        try:
            return await self._async_client.beta.chat.completions.parse(
                messages=messages,
                model=self.model_type,
                **request_config,
            )
        except Exception as e:
            logger.error(f"Fallback attempt also failed: {e}")
            raise
