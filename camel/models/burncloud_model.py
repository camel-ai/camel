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
from typing import Any, Dict, Optional, Union

from camel.configs import BurnCloudConfig
from camel.models.openai_compatible_model import OpenAICompatibleModel
from camel.types import ModelType
from camel.utils import BaseTokenCounter, api_keys_required


class BurnCloudModel(OpenAICompatibleModel):
    r"""OpenAI-compatible backend for the BurnCloud API gateway.

    Args:
        model_type (Union[ModelType, str]): Target model identifier supported
            by BurnCloud, e.g., ``gpt-4o`` or ``deepseek-reasoner``.
        model_config_dict (Optional[Dict[str, Any]], optional): Request payload
            overrides. Defaults to :obj:`BurnCloudConfig().as_dict()`.
        api_key (Optional[str], optional): BurnCloud API key. If omitted,
            :obj:`BURNCLOUD_API_KEY` from the environment will be used.
        url (Optional[str], optional): Endpoint base URL. Defaults to
            ``https://ai.burncloud.com/v1`` or ``BURNCLOUD_API_BASE_URL`` when
            provided.
        token_counter (Optional[BaseTokenCounter], optional): Token counter to
            associate with the model. Falls back to :obj:`OpenAITokenCounter`
            inside :class:`OpenAICompatibleModel` if not provided.
        timeout (Optional[float], optional): Timeout in seconds for API calls.
            Defaults to ``MODEL_TIMEOUT`` env var or ``180`` seconds.
        max_retries (int, optional): Maximum retry attempts for failed calls.
            Defaults to ``3``.
        **kwargs (Any): Extra keyword arguments forwarded to the underlying
            OpenAI-compatible client.
    """

    @api_keys_required([('api_key', 'BURNCLOUD_API_KEY')])
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
            model_config_dict = BurnCloudConfig().as_dict()
        api_key = api_key or os.environ.get('BURNCLOUD_API_KEY')
        url = url or os.environ.get(
            'BURNCLOUD_API_BASE_URL', 'https://ai.burncloud.com/v1'
        )
        timeout = timeout or float(os.environ.get('MODEL_TIMEOUT', 180))

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
