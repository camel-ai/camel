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
import time
from typing import Any, Dict, List, Optional, Union

from openai import AsyncStream, Stream

from camel.configs import MODELSCOPE_API_PARAMS, ModelScopeConfig
from camel.messages import OpenAIMessage
from camel.models.openai_compatible_model import OpenAICompatibleModel
from camel.types import (
    ChatCompletion,
    ChatCompletionChunk,
    ModelType,
)
from camel.utils import (
    BaseTokenCounter,
    api_keys_required,
)


class ModelScopeModel(OpenAICompatibleModel):
    r"""ModelScope API in a unified OpenAICompatibleModel interface.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created, one of ModelScope series.
        model_config_dict (Optional[Dict[str, Any]], optional): A dictionary
            that will be fed into:obj:`openai.ChatCompletion.create()`. If
            :obj:`None`, :obj:`ModelScopeConfig().as_dict()` will be used.
            (default: :obj:`None`)
        api_key (Optional[str], optional): The MODELSCOPE_SDK_TOKEN for
            authenticating with the ModelScope service. (default: :obj:`None`)
            refer to the following link for more details:
            https://modelscope.cn/my/myaccesstoken
        url (Optional[str], optional): The url to the ModelScope service.
            (default: :obj:`https://api-inference.modelscope.cn/v1/`)
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
            ("api_key", 'MODELSCOPE_SDK_TOKEN'),
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
            model_config_dict = ModelScopeConfig().as_dict()
        api_key = api_key or os.environ.get("MODELSCOPE_SDK_TOKEN")
        url = url or os.environ.get(
            "MODELSCOPE_API_BASE_URL",
            "https://api-inference.modelscope.cn/v1/",
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

    def _post_handle_response(
        self, response: Union[ChatCompletion, Stream[ChatCompletionChunk]]
    ) -> ChatCompletion:
        r"""Handle reasoning content with <think> tags at the beginning."""
        if not isinstance(response, Stream):
            # Handle non-streaming response (existing logic)
            if self.model_config_dict.get("extra_body", {}).get(
                "enable_thinking", False
            ):
                reasoning_content = response.choices[
                    0
                ].message.reasoning_content  # type: ignore[attr-defined]
                combined_content = (
                    f"<think>\n{reasoning_content}\n</think>\n"
                    if reasoning_content
                    else ""
                )
                response_content = response.choices[0].message.content or ""
                combined_content += response_content

                # Construct a new ChatCompletion with combined content
                return ChatCompletion.construct(
                    id=response.id,
                    choices=[
                        dict(
                            finish_reason=response.choices[0].finish_reason,
                            index=response.choices[0].index,
                            logprobs=response.choices[0].logprobs,
                            message=dict(
                                role=response.choices[0].message.role,
                                content=combined_content,
                            ),
                        )
                    ],
                    created=response.created,
                    model=response.model,
                    object="chat.completion",
                    system_fingerprint=response.system_fingerprint,
                    usage=response.usage,
                )
            else:
                return response  # Return original if no thinking enabled

        # Handle streaming response
        accumulated_reasoning = ""
        accumulated_content = ""
        final_chunk = None
        usage_data = None  # Initialize usage data
        role = "assistant"  # Default role

        for chunk in response:
            final_chunk = chunk  # Keep track of the last chunk for metadata
            if chunk.choices:
                delta = chunk.choices[0].delta
                if delta.role:
                    role = delta.role  # Update role if provided
                if (
                    hasattr(delta, 'reasoning_content')
                    and delta.reasoning_content
                ):
                    accumulated_reasoning += delta.reasoning_content
                if delta.content:
                    accumulated_content += delta.content

            if hasattr(chunk, 'usage') and chunk.usage:
                usage_data = chunk.usage

        combined_content = (
            f"<think>\n{accumulated_reasoning}\n</think>\n"
            if accumulated_reasoning
            else ""
        ) + accumulated_content

        # Construct the final ChatCompletion object from accumulated
        # stream data
        if final_chunk:
            finish_reason = "stop"  # Default finish reason
            logprobs = None
            if final_chunk.choices:
                finish_reason = (
                    final_chunk.choices[0].finish_reason or finish_reason
                )
                if hasattr(final_chunk.choices[0], 'logprobs'):
                    logprobs = final_chunk.choices[0].logprobs

            return ChatCompletion.construct(
                # Use data from the final chunk or defaults
                id=final_chunk.id
                if hasattr(final_chunk, 'id')
                else "streamed-completion",
                choices=[
                    dict(
                        finish_reason=finish_reason,
                        index=0,
                        logprobs=logprobs,
                        message=dict(
                            role=role,
                            content=combined_content,
                        ),
                    )
                ],
                created=final_chunk.created
                if hasattr(final_chunk, 'created')
                else int(time.time()),
                model=final_chunk.model
                if hasattr(final_chunk, 'model')
                else self.model_type,
                object="chat.completion",
                system_fingerprint=final_chunk.system_fingerprint
                if hasattr(final_chunk, 'system_fingerprint')
                else None,
                usage=usage_data,
            )
        else:
            # Handle cases where the stream was empty or invalid
            return ChatCompletion.construct(
                id="empty-stream",
                choices=[
                    dict(
                        finish_reason="error",
                        index=0,
                        message=dict(role="assistant", content=""),
                    )
                ],
                created=int(time.time()),
                model=self.model_type,
                object="chat.completion",
                usage=usage_data,
            )

    def _request_chat_completion(
        self,
        messages: List[OpenAIMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        request_config = self.model_config_dict.copy()

        if tools:
            request_config["tools"] = tools

        return self._post_handle_response(
            self._client.chat.completions.create(
                messages=messages,
                model=self.model_type,
                **request_config,
            )
        )

    async def _arequest_chat_completion(
        self,
        messages: List[OpenAIMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]:
        request_config = self.model_config_dict.copy()

        if tools:
            request_config["tools"] = tools

        response = await self._async_client.chat.completions.create(
            messages=messages,
            model=self.model_type,
            **request_config,
        )
        return self._post_handle_response(response)

    def check_model_config(self):
        r"""Check whether the model configuration contains any
        unexpected arguments to ModelScope API.

        Raises:
            ValueError: If the model configuration dictionary contains any
                unexpected arguments to ModelScope API.
        """
        for param in self.model_config_dict:
            if param not in MODELSCOPE_API_PARAMS:
                raise ValueError(
                    f"Unexpected argument `{param}` is "
                    "input into ModelScope model backend."
                )
