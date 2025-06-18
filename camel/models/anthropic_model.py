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
from typing import Any, Dict, List, Optional, Union

from openai import AsyncStream, Stream

from camel.configs import ANTHROPIC_API_PARAMS, AnthropicConfig
from camel.messages import OpenAIMessage
from camel.models.openai_compatible_model import OpenAICompatibleModel
from camel.types import ChatCompletion, ChatCompletionChunk, ModelType
from camel.utils import (
    AnthropicTokenCounter,
    BaseTokenCounter,
    api_keys_required,
    dependencies_required,
)


def strip_trailing_whitespace_from_messages(
    messages: List[OpenAIMessage],
) -> List[OpenAIMessage]:
    r"""Strip trailing whitespace from all message contents in a list of
    messages. This is necessary because the Anthropic API doesn't allow
    trailing whitespace in message content.

    Args:
        messages (List[OpenAIMessage]): List of messages to process

    Returns:
        List[OpenAIMessage]: The processed messages with trailing whitespace
            removed
    """
    if not messages:
        return messages

    # Create a deep copy to avoid modifying the original messages
    processed_messages = [dict(msg) for msg in messages]

    # Process each message
    for msg in processed_messages:
        if "content" in msg and msg["content"] is not None:
            if isinstance(msg["content"], str):
                msg["content"] = msg["content"].rstrip()
            elif isinstance(msg["content"], list):
                # Handle content that's a list of content parts (e.g., for
                # multimodal content)
                for i, part in enumerate(msg["content"]):
                    if (
                        isinstance(part, dict)
                        and "text" in part
                        and isinstance(part["text"], str)
                    ):
                        part["text"] = part["text"].rstrip()
                    elif isinstance(part, str):
                        msg["content"][i] = part.rstrip()

    return processed_messages  # type: ignore[return-value]


class AnthropicModel(OpenAICompatibleModel):
    r"""Anthropic API in a unified OpenAICompatibleModel interface.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created, one of CLAUDE_* series.
        model_config_dict (Optional[Dict[str, Any]], optional): A dictionary
            that will be fed into `openai.ChatCompletion.create()`.  If
            :obj:`None`, :obj:`AnthropicConfig().as_dict()` will be used.
            (default: :obj:`None`)
        api_key (Optional[str], optional): The API key for authenticating with
            the Anthropic service. (default: :obj:`None`)
        url (Optional[str], optional): The url to the Anthropic service.
            (default: :obj:`https://api.anthropic.com/v1/`)
        token_counter (Optional[BaseTokenCounter], optional): Token counter to
            use for the model. If not provided, :obj:`AnthropicTokenCounter`
            will be used. (default: :obj:`None`)
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
            ("api_key", "ANTHROPIC_API_KEY"),
        ]
    )
    @dependencies_required('anthropic')
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
            model_config_dict = AnthropicConfig().as_dict()
        api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        url = (
            url
            or os.environ.get("ANTHROPIC_API_BASE_URL")
            or "https://api.anthropic.com/v1/"
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

        # Monkey patch the AnthropicTokenCounter to handle trailing whitespace
        self._patch_anthropic_token_counter()

    @property
    def token_counter(self) -> BaseTokenCounter:
        r"""Initialize the token counter for the model backend.

        Returns:
            BaseTokenCounter: The token counter following the model's
                tokenization style.
        """
        if not self._token_counter:
            self._token_counter = AnthropicTokenCounter(self.model_type)
        return self._token_counter

    def check_model_config(self):
        r"""Check whether the model configuration is valid for anthropic
        model backends.

        Raises:
            ValueError: If the model configuration dictionary contains any
                unexpected arguments to Anthropic API.
        """
        for param in self.model_config_dict:
            if param not in ANTHROPIC_API_PARAMS:
                raise ValueError(
                    f"Unexpected argument `{param}` is "
                    "input into Anthropic model backend."
                )

    def _request_chat_completion(
        self,
        messages: List[OpenAIMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        # Strip trailing whitespace from all message contents to prevent
        # Anthropic API errors
        processed_messages = strip_trailing_whitespace_from_messages(messages)

        # Call the parent class method
        return super()._request_chat_completion(processed_messages, tools)

    async def _arequest_chat_completion(
        self,
        messages: List[OpenAIMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]:
        # Strip trailing whitespace from all message contents to prevent
        # Anthropic API errors
        processed_messages = strip_trailing_whitespace_from_messages(messages)

        # Call the parent class method
        return await super()._arequest_chat_completion(
            processed_messages, tools
        )

    def _patch_anthropic_token_counter(self):
        r"""Monkey patch the AnthropicTokenCounter class to handle trailing
        whitespace.

        This patches the count_tokens_from_messages method to strip trailing
        whitespace from message content before sending to the Anthropic API.
        """
        import functools

        from anthropic.types import MessageParam

        from camel.utils import AnthropicTokenCounter

        original_count_tokens = (
            AnthropicTokenCounter.count_tokens_from_messages
        )

        @functools.wraps(original_count_tokens)
        def patched_count_tokens(self, messages):
            # Process messages to remove trailing whitespace
            processed_messages = strip_trailing_whitespace_from_messages(
                messages
            )

            # Use the processed messages with the original method
            return self.client.messages.count_tokens(
                messages=[
                    MessageParam(
                        content=str(msg["content"]),
                        role="user" if msg["role"] == "user" else "assistant",
                    )
                    for msg in processed_messages
                ],
                model=self.model,
            ).input_tokens

        # Apply the monkey patch
        AnthropicTokenCounter.count_tokens_from_messages = patched_count_tokens
