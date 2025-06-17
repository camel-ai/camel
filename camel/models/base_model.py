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
import abc
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, Union

from openai import AsyncStream, Stream
from pydantic import BaseModel

from camel.messages import OpenAIMessage
from camel.types import (
    ChatCompletion,
    ChatCompletionChunk,
    ModelType,
    ParsedChatCompletion,
    UnifiedModelType,
)
from camel.utils import BaseTokenCounter


class ModelBackendMeta(abc.ABCMeta):
    r"""Metaclass that automatically preprocesses messages in run method.

    Automatically wraps the run method of any class inheriting from
    BaseModelBackend to preprocess messages (remove <think> tags) before they
    are sent to the model.
    """

    def __new__(mcs, name, bases, namespace):
        r"""Wraps run method with preprocessing if it exists in the class."""
        if 'run' in namespace:
            original_run = namespace['run']

            def wrapped_run(
                self, messages: List[OpenAIMessage], *args, **kwargs
            ):
                messages = self.preprocess_messages(messages)
                return original_run(self, messages, *args, **kwargs)

            namespace['run'] = wrapped_run
        return super().__new__(mcs, name, bases, namespace)


class BaseModelBackend(ABC, metaclass=ModelBackendMeta):
    r"""Base class for different model backends.
    It may be OpenAI API, a local LLM, a stub for unit tests, etc.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created.
        model_config_dict (Optional[Dict[str, Any]], optional): A config
            dictionary. (default: :obj:`{}`)
        api_key (Optional[str], optional): The API key for authenticating
            with the model service. (default: :obj:`None`)
        url (Optional[str], optional): The url to the model service.
            (default: :obj:`None`)
        token_counter (Optional[BaseTokenCounter], optional): Token
            counter to use for the model. If not provided,
            :obj:`OpenAITokenCounter` will be used. (default: :obj:`None`)
        timeout (Optional[float], optional): The timeout value in seconds for
            API calls. (default: :obj:`None`)
        max_retries (int, optional): Maximum number of retries
            for API calls. (default: :obj:`3`)
    """

    def __init__(
        self,
        model_type: Union[ModelType, str],
        model_config_dict: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        token_counter: Optional[BaseTokenCounter] = None,
        timeout: Optional[float] = None,
        max_retries: int = 3,
    ) -> None:
        self.model_type: UnifiedModelType = UnifiedModelType(model_type)
        if model_config_dict is None:
            model_config_dict = {}
        self.model_config_dict = model_config_dict
        self._api_key = api_key
        self._url = url
        self._token_counter = token_counter
        self._timeout = timeout
        self._max_retries = max_retries
        self.check_model_config()

    @property
    @abstractmethod
    def token_counter(self) -> BaseTokenCounter:
        r"""Initialize the token counter for the model backend.

        Returns:
            BaseTokenCounter: The token counter following the model's
                tokenization style.
        """
        pass

    def preprocess_messages(
        self, messages: List[OpenAIMessage]
    ) -> List[OpenAIMessage]:
        r"""Preprocess messages before sending to model API.
        Removes thinking content from assistant and user messages.
        Automatically formats messages for parallel tool calls if tools are
        detected.

        Args:
            messages (List[OpenAIMessage]): Original messages.

        Returns:
            List[OpenAIMessage]: Preprocessed messages
        """
        # Process all messages in a single pass
        processed_messages = []
        tool_calls_buffer: List[OpenAIMessage] = []
        tool_responses_buffer: Dict[str, OpenAIMessage] = {}
        has_tool_calls = False

        for msg in messages:
            # Remove thinking content if needed
            role = msg.get('role')
            content = msg.get('content')
            if role in ['assistant', 'user'] and isinstance(content, str):
                if '<think>' in content and '</think>' in content:
                    content = re.sub(
                        r'<think>.*?</think>', '', content, flags=re.DOTALL
                    ).strip()
                processed_msg = dict(msg)
                processed_msg['content'] = content
            else:
                processed_msg = dict(msg)

            # Check and track tool calls/responses
            is_tool_call = (
                processed_msg.get("role") == "assistant"
                and "tool_calls" in processed_msg
            )
            is_tool_response = (
                processed_msg.get("role") == "tool"
                and "tool_call_id" in processed_msg
            )

            if is_tool_call or is_tool_response:
                has_tool_calls = True

            # Store the processed message for later formatting if needed
            processed_messages.append(processed_msg)

        # If no tool calls detected, return the processed messages
        if not has_tool_calls:
            return processed_messages  # type: ignore[return-value]

        # Format messages for parallel tool calls
        formatted_messages = []
        tool_calls_buffer = []
        tool_responses_buffer = {}

        for msg in processed_messages:  # type: ignore[assignment]
            # If this is an assistant message with tool calls, add it to the
            # buffer
            if msg.get("role") == "assistant" and "tool_calls" in msg:
                tool_calls_buffer.append(msg)
                continue

            # If this is a tool response, add it to the responses buffer
            if msg.get("role") == "tool" and "tool_call_id" in msg:
                tool_call_id = msg.get("tool_call_id")
                if isinstance(tool_call_id, str):
                    tool_responses_buffer[tool_call_id] = msg
                continue

            # Process any complete tool call + responses before adding regular
            # messages
            if tool_calls_buffer and tool_responses_buffer:
                # Add the assistant message with tool calls
                assistant_msg = tool_calls_buffer[0]
                formatted_messages.append(assistant_msg)

                # Add all matching tool responses for this assistant message
                tool_calls = assistant_msg.get("tool_calls", [])
                if isinstance(tool_calls, list):
                    for tool_call in tool_calls:
                        tool_call_id = tool_call.get("id")
                        if (
                            isinstance(tool_call_id, str)
                            and tool_call_id in tool_responses_buffer
                        ):
                            formatted_messages.append(
                                tool_responses_buffer[tool_call_id]
                            )
                            del tool_responses_buffer[tool_call_id]

                tool_calls_buffer.pop(0)

            # Add the current regular message
            formatted_messages.append(msg)

        # Process any remaining buffered tool calls and responses
        while tool_calls_buffer:
            assistant_msg = tool_calls_buffer[0]
            formatted_messages.append(assistant_msg)

            tool_calls = assistant_msg.get("tool_calls", [])
            if isinstance(tool_calls, list):
                for tool_call in tool_calls:
                    tool_call_id = tool_call.get("id")
                    if (
                        isinstance(tool_call_id, str)
                        and tool_call_id in tool_responses_buffer
                    ):
                        formatted_messages.append(
                            tool_responses_buffer[tool_call_id]
                        )
                        del tool_responses_buffer[tool_call_id]

            tool_calls_buffer.pop(0)

        # Add any remaining tool responses
        for response in tool_responses_buffer.values():
            formatted_messages.append(response)

        return formatted_messages

    @abstractmethod
    def _run(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        pass

    @abstractmethod
    async def _arun(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]:
        pass

    def run(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        r"""Runs the query to the backend model.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.
            response_format (Optional[Type[BaseModel]]): The response format
                to use for the model. (default: :obj:`None`)
            tools (Optional[List[Tool]]): The schema of tools to use for the
                model for this request. Will override the tools specified in
                the model configuration (but not change the configuration).
                (default: :obj:`None`)

        Returns:
            Union[ChatCompletion, Stream[ChatCompletionChunk]]:
                `ChatCompletion` in the non-stream mode, or
                `Stream[ChatCompletionChunk]` in the stream mode.
        """
        # None -> use default tools
        if tools is None:
            tools = self.model_config_dict.get("tools", None)
        # Empty -> use no tools
        elif not tools:
            tools = None
        return self._run(messages, response_format, tools)

    async def arun(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]:
        r"""Runs the query to the backend model asynchronously.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.
            response_format (Optional[Type[BaseModel]]): The response format
                to use for the model. (default: :obj:`None`)
            tools (Optional[List[Tool]]): The schema of tools to use for the
                model for this request. Will override the tools specified in
                the model configuration (but not change the configuration).
                (default: :obj:`None`)

        Returns:
            Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]:
                `ChatCompletion` in the non-stream mode, or
                `AsyncStream[ChatCompletionChunk]` in the stream mode.
        """
        if tools is None:
            tools = self.model_config_dict.get("tools", None)
        elif not tools:
            tools = None
        return await self._arun(messages, response_format, tools)

    @abstractmethod
    def check_model_config(self):
        r"""Check whether the input model configuration contains unexpected
        arguments

        Raises:
            ValueError: If the model configuration dictionary contains any
                unexpected argument for this model class.
        """
        pass

    def count_tokens_from_messages(self, messages: List[OpenAIMessage]) -> int:
        r"""Count the number of tokens in the messages using the specific
        tokenizer.

        Args:
            messages (List[Dict]): message list with the chat history
                in OpenAI API format.

        Returns:
            int: Number of tokens in the messages.
        """
        return self.token_counter.count_tokens_from_messages(messages)

    def _to_chat_completion(
        self, response: ParsedChatCompletion
    ) -> ChatCompletion:
        if len(response.choices) > 1:
            print("Warning: Multiple response choices detected")

        choice = dict(
            index=response.choices[0].index,
            message={
                "role": response.choices[0].message.role,
                "content": response.choices[0].message.content,
                "tool_calls": response.choices[0].message.tool_calls,
                "parsed": response.choices[0].message.parsed,
            },
            finish_reason=response.choices[0].finish_reason,
        )

        obj = ChatCompletion.construct(
            id=response.id,
            choices=[choice],
            created=response.created,
            model=response.model,
            object="chat.completion",
            usage=response.usage,
        )
        return obj

    @property
    def token_limit(self) -> int:
        r"""Returns the maximum token limit for a given model.

        This method retrieves the maximum token limit either from the
        `model_config_dict` or from the model's default token limit.

        Returns:
            int: The maximum token limit for the given model.
        """
        return (
            self.model_config_dict.get("max_tokens")
            or self.model_type.token_limit
        )

    @property
    def stream(self) -> bool:
        r"""Returns whether the model is in stream mode, which sends partial
        results each time.

        Returns:
            bool: Whether the model is in stream mode.
        """
        return False
