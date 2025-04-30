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

from camel.configs import WATSONX_API_PARAMS, WatsonXConfig
from camel.logger import get_logger
from camel.messages import OpenAIMessage
from camel.models import BaseModelBackend
from camel.models._utils import try_modify_message_with_format
from camel.types import ChatCompletion, ModelType
from camel.utils import (
    BaseTokenCounter,
    OpenAITokenCounter,
    api_keys_required,
)

logger = get_logger(__name__)


class WatsonXModel(BaseModelBackend):
    r"""WatsonX API in a unified BaseModelBackend interface.

    Args:
        model_type (Union[ModelType, str]): Model type for which a backend is
            created, one of WatsonX series.
        model_config_dict (Optional[Dict[str, Any]], optional): A dictionary
            that will be fed into :obj:`ModelInference.chat()`.
            If :obj:`None`, :obj:`WatsonXConfig().as_dict()` will be used.
            (default: :obj:`None`)
        api_key (Optional[str], optional): The API key for authenticating with
            the WatsonX service. (default: :obj:`None`)
        url (Optional[str], optional): The url to the WatsonX service.
            (default: :obj:`None`)
        project_id (Optional[str], optional): The project ID authenticating
            with the WatsonX service. (default: :obj:`None`)
        token_counter (Optional[BaseTokenCounter], optional): Token counter to
            use for the model. If not provided, :obj:`OpenAITokenCounter(
            ModelType.GPT_4O_MINI)` will be used.
            (default: :obj:`None`)
        timeout (Optional[float], optional): The timeout value in seconds for
            API calls. If not provided, will fall back to the MODEL_TIMEOUT
            environment variable or default to 180 seconds.
            (default: :obj:`None`)
    """

    @api_keys_required(
        [
            ("api_key", 'WATSONX_API_KEY'),
            ("project_id", 'WATSONX_PROJECT_ID'),
        ]
    )
    def __init__(
        self,
        model_type: Union[ModelType, str],
        model_config_dict: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        project_id: Optional[str] = None,
        token_counter: Optional[BaseTokenCounter] = None,
        timeout: Optional[float] = None,
    ):
        from ibm_watsonx_ai import APIClient, Credentials
        from ibm_watsonx_ai.foundation_models import ModelInference

        if model_config_dict is None:
            model_config_dict = WatsonXConfig().as_dict()

        api_key = api_key or os.environ.get("WATSONX_API_KEY")
        url = url or os.environ.get(
            "WATSONX_URL", "https://jp-tok.ml.cloud.ibm.com"
        )
        project_id = project_id or os.environ.get("WATSONX_PROJECT_ID")

        timeout = timeout or float(os.environ.get("MODEL_TIMEOUT", 180))
        super().__init__(
            model_type, model_config_dict, api_key, url, token_counter, timeout
        )

        self._project_id = project_id
        credentials = Credentials(api_key=self._api_key, url=self._url)
        client = APIClient(credentials, project_id=self._project_id)

        self._model = ModelInference(
            model_id=self.model_type,
            api_client=client,
            params=model_config_dict,
        )

    def _to_openai_response(self, response: Dict[str, Any]) -> ChatCompletion:
        r"""Convert WatsonX response to OpenAI format."""
        if not response:
            raise ValueError("Empty response from WatsonX API")

        # Extract usage information
        usage = response.get("usage", {})

        # Create OpenAI-compatible response
        obj = ChatCompletion.construct(
            id=response.get("id", ""),
            choices=response.get("choices", []),
            created=response.get("created"),
            model=self.model_type,
            object="chat.completion",
            usage=usage,
        )
        return obj

    @property
    def token_counter(self) -> BaseTokenCounter:
        r"""Initialize the token counter for the model backend.

        Returns:
            BaseTokenCounter: The token counter following the model's
                tokenization style.
        """
        if not self._token_counter:
            self._token_counter = OpenAITokenCounter(
                model=ModelType.GPT_4O_MINI
            )
        return self._token_counter

    def _prepare_request(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        import copy

        request_config = copy.deepcopy(self.model_config_dict)

        if tools:
            request_config["tools"] = tools
        elif response_format:
            try_modify_message_with_format(messages[-1], response_format)
            request_config["response_format"] = {"type": "json_object"}

        return request_config

    def _run(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatCompletion:
        r"""Runs inference of WatsonX chat completion.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.
            response_format (Optional[Type[BaseModel]], optional): The
                response format. (default: :obj:`None`)
            tools (Optional[List[Dict[str, Any]]], optional): tools to use.
                (default: :obj:`None`)

        Returns:
            ChatCompletion.
        """
        try:
            request_config = self._prepare_request(
                messages, response_format, tools
            )

            # WatsonX expects messages as a list of dictionaries
            response = self._model.chat(
                messages=messages,
                params=request_config,
                tools=tools,
            )

            openai_response = self._to_openai_response(response)
            return openai_response

        except Exception as e:
            logger.error(f"Unexpected error when calling WatsonX API: {e!s}")
            raise

    async def _arun(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatCompletion:
        r"""Runs inference of WatsonX chat completion asynchronously.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.
            response_format (Optional[Type[BaseModel]], optional): The
                response format. (default: :obj:`None`)
            tools (Optional[List[Dict[str, Any]]], optional): tools to use.
                (default: :obj:`None`)

        Returns:
            ChatCompletion.
        """
        try:
            request_config = self._prepare_request(
                messages, response_format, tools
            )

            # WatsonX expects messages as a list of dictionaries
            response = await self._model.achat(
                messages=messages,
                params=request_config,
                tools=tools,
            )

            openai_response = self._to_openai_response(response)
            return openai_response

        except Exception as e:
            logger.error(f"Unexpected error when calling WatsonX API: {e!s}")
            raise

    def check_model_config(self):
        r"""Check whether the model configuration contains any unexpected
        arguments to WatsonX API.

        Raises:
            ValueError: If the model configuration dictionary contains any
                unexpected arguments to WatsonX API.
        """
        for param in self.model_config_dict:
            if param not in WATSONX_API_PARAMS:
                raise ValueError(
                    f"Unexpected argument `{param}` is "
                    "input into WatsonX model backend."
                )

    @property
    def stream(self) -> bool:
        r"""Returns whether the model is in stream mode, which sends partial
        results each time.

        Returns:
            bool: Whether the model is in stream mode.
        """
        return False
