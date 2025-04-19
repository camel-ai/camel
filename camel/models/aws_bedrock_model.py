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

from openai import AsyncStream
from pydantic import BaseModel

from camel.configs import BEDROCK_API_PARAMS, BedrockConfig
from camel.messages import OpenAIMessage
from camel.models.openai_compatible_model import OpenAICompatibleModel
from camel.types import (
    ChatCompletion,
    ChatCompletionChunk,
    ModelType,
)
from camel.utils import BaseTokenCounter, api_keys_required


class AWSBedrockModel(OpenAICompatibleModel):
    r"""AWS Bedrock API in a unified OpenAICompatibleModel interface.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created.
        model_config_dict (Dict[str, Any], optional): A dictionary
            that will be fed into:obj:`openai.ChatCompletion.create()`.
            If:obj:`None`, :obj:`BedrockConfig().as_dict()` will be used.
            (default: :obj:`None`)
        api_key (str, optional): The API key for authenticating with
            the AWS Bedrock service. (default: :obj:`None`)
        url (str, optional): The url to the AWS Bedrock service.
        token_counter (BaseTokenCounter, optional): Token counter to
            use for the model. If not provided, :obj:`OpenAITokenCounter(
            ModelType.GPT_4O_MINI)` will be used.
            (default: :obj:`None`)
        timeout (Optional[float], optional): The timeout value in seconds for
            API calls. If not provided, will fall back to the MODEL_TIMEOUT
            environment variable or default to 180 seconds.
            (default: :obj:`None`)
    References:
        https://docs.aws.amazon.com/bedrock/latest/APIReference/welcome.html
    """

    @api_keys_required(
        [
            ("url", "BEDROCK_API_BASE_URL"),
            ("api_key", "BEDROCK_API_KEY"),
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
    ) -> None:
        if model_config_dict is None:
            model_config_dict = BedrockConfig().as_dict()
        api_key = api_key or os.environ.get("BEDROCK_API_KEY")
        url = url or os.environ.get(
            "BEDROCK_API_BASE_URL",
        )
        timeout = timeout or float(os.environ.get("MODEL_TIMEOUT", 180))
        super().__init__(
            model_type=model_type,
            model_config_dict=model_config_dict,
            api_key=api_key,
            url=url,
            token_counter=token_counter,
            timeout=timeout,
        )

    async def _arun(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]:
        raise NotImplementedError(
            "AWS Bedrock does not support async inference."
        )

    def check_model_config(self):
        r"""Check whether the input model configuration contains unexpected
        arguments.

        Raises:
            ValueError: If the model configuration dictionary contains any
                unexpected argument for this model class.
        """
        for param in self.model_config_dict:
            if param not in BEDROCK_API_PARAMS:
                raise ValueError(
                    f"Invalid parameter '{param}' in model_config_dict. "
                    f"Valid parameters are: {BEDROCK_API_PARAMS}"
                )
