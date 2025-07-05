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
import uuid
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel

from camel.configs import LITELLM_API_PARAMS, LiteLLMConfig
from camel.messages import OpenAIMessage
from camel.models import BaseModelBackend
from camel.types import ChatCompletion, ModelType
from camel.utils import (
    BaseTokenCounter,
    LiteLLMTokenCounter,
    dependencies_required,
    get_current_agent_session_id,
    update_current_observation,
    update_langfuse_trace,
)

if os.environ.get("LANGFUSE_ENABLED", "False").lower() == "true":
    try:
        from langfuse.decorators import observe
    except ImportError:
        from camel.utils import observe
else:
    from camel.utils import observe


class LiteLLMModel(BaseModelBackend):
    r"""Constructor for LiteLLM backend with OpenAI compatibility.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created, such as GPT-3.5-turbo, Claude-2, etc.
        model_config_dict (Optional[Dict[str, Any]], optional): A dictionary
            that will be fed into:obj:`completion()`. If:obj:`None`,
            :obj:`LiteLLMConfig().as_dict()` will be used.
            (default: :obj:`None`)
        api_key (Optional[str], optional): The API key for authenticating with
            the model service. (default: :obj:`None`)
        url (Optional[str], optional): The url to the model service.
            (default: :obj:`None`)
        token_counter (Optional[BaseTokenCounter], optional): Token counter to
            use for the model. If not provided, :obj:`LiteLLMTokenCounter` will
            be used. (default: :obj:`None`)
        timeout (Optional[float], optional): The timeout value in seconds for
            API calls. If not provided, will fall back to the MODEL_TIMEOUT
            environment variable or default to 180 seconds.
            (default: :obj:`None`)
        **kwargs (Any): Additional arguments to pass to the client
            initialization.
    """

    # NOTE: Currently stream mode is not supported.

    @dependencies_required('litellm')
    def __init__(
        self,
        model_type: Union[ModelType, str],
        model_config_dict: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        token_counter: Optional[BaseTokenCounter] = None,
        timeout: Optional[float] = None,
        **kwargs: Any,
    ) -> None:
        from litellm import completion

        if model_config_dict is None:
            model_config_dict = LiteLLMConfig().as_dict()
        timeout = timeout or float(os.environ.get("MODEL_TIMEOUT", 180))
        super().__init__(
            model_type, model_config_dict, api_key, url, token_counter, timeout
        )
        self.client = completion
        self.kwargs = kwargs

    def _convert_response_from_litellm_to_openai(
        self, response
    ) -> ChatCompletion:
        r"""Converts a response from the LiteLLM format to the OpenAI format.

        Parameters:
            response (LiteLLMResponse): The response object from LiteLLM.

        Returns:
            ChatCompletion: The response object in OpenAI's format.
        """

        converted_choices = []
        for choice in response.choices:
            # Build the assistant message dict
            msg_dict: Dict[str, Any] = {
                "role": choice.message.role,
                "content": choice.message.content,
            }

            if getattr(choice.message, "tool_calls", None):
                msg_dict["tool_calls"] = choice.message.tool_calls

            elif getattr(choice.message, "function_call", None):
                func_call = choice.message.function_call
                msg_dict["tool_calls"] = [
                    {
                        "id": f"call_{uuid.uuid4().hex[:24]}",
                        "type": "function",
                        "function": {
                            "name": getattr(func_call, "name", None),
                            "arguments": getattr(func_call, "arguments", "{}"),
                        },
                    }
                ]

            converted_choices.append(
                {
                    "index": choice.index,
                    "message": msg_dict,
                    "finish_reason": choice.finish_reason,
                }
            )

        return ChatCompletion.construct(
            id=response.id,
            choices=converted_choices,
            created=getattr(response, "created", None),
            model=getattr(response, "model", None),
            object=getattr(response, "object", None),
            system_fingerprint=getattr(response, "system_fingerprint", None),
            usage=getattr(response, "usage", None),
        )

    @property
    def token_counter(self) -> BaseTokenCounter:
        r"""Initialize the token counter for the model backend.

        Returns:
            BaseTokenCounter: The token counter following the model's
                tokenization style.
        """
        if not self._token_counter:
            self._token_counter = LiteLLMTokenCounter(self.model_type)
        return self._token_counter

    async def _arun(self) -> None:  # type: ignore[override]
        raise NotImplementedError

    @observe(as_type='generation')
    def _run(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatCompletion:
        r"""Runs inference of LiteLLM chat completion.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI format.

        Returns:
            ChatCompletion
        """

        request_config = self.model_config_dict.copy()
        if tools:
            request_config['tools'] = tools
        if response_format:
            request_config['response_format'] = response_format

        update_current_observation(
            input={
                "messages": messages,
                "tools": tools,
            },
            model=str(self.model_type),
            model_parameters=self.model_config_dict,
        )
        # Update Langfuse trace with current agent session and metadata
        agent_session_id = get_current_agent_session_id()
        if agent_session_id:
            update_langfuse_trace(
                session_id=agent_session_id,
                metadata={
                    "source": "camel",
                    "agent_id": agent_session_id,
                    "agent_type": "camel_chat_agent",
                    "model_type": str(self.model_type),
                },
                tags=["CAMEL-AI", str(self.model_type)],
            )

        response = self.client(
            timeout=self._timeout,
            api_key=self._api_key,
            base_url=self._url,
            model=self.model_type,
            messages=messages,
            **request_config,
            **self.kwargs,
        )
        response = self._convert_response_from_litellm_to_openai(response)

        update_current_observation(
            usage=response.usage,
        )
        return response

    def check_model_config(self):
        r"""Check whether the model configuration contains any unexpected
        arguments to LiteLLM API.

        Raises:
            ValueError: If the model configuration dictionary contains any
                unexpected arguments.
        """
        for param in self.model_config_dict:
            if param not in LITELLM_API_PARAMS:
                raise ValueError(
                    f"Unexpected argument `{param}` is "
                    "input into LiteLLM model backend."
                )
