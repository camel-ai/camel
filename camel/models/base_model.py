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
import abc
import inspect
import os
import re
from abc import ABC, abstractmethod
from typing import (
    Any,
    AsyncGenerator,
    Dict,
    Generator,
    List,
    Optional,
    Type,
    Union,
)

from openai import AsyncStream, Stream
from openai.lib.streaming.chat import (
    AsyncChatCompletionStreamManager,
    ChatCompletionStreamManager,
)
from pydantic import BaseModel

from camel.logger import get_logger as camel_get_logger
from camel.messages import OpenAIMessage
from camel.types import (
    ChatCompletion,
    ChatCompletionChunk,
    ModelType,
    ParsedChatCompletion,
    UnifiedModelType,
)
from camel.utils import (
    BaseTokenCounter,
    Constants,
    get_current_agent_session_id,
    update_langfuse_trace,
)

if os.environ.get("TRACEROOT_ENABLED", "False").lower() == "true":
    try:
        from traceroot import get_logger  # type: ignore[import]
        from traceroot import trace as observe  # type: ignore[import]

        logger = get_logger('base_model')
    except ImportError:
        from camel.utils import observe

        logger = camel_get_logger('base_model')
else:
    from camel.utils import observe

    logger = camel_get_logger('base_model')


class _StreamLogger:
    r"""Base for stream logging wrappers."""

    def __init__(self, log_path: Optional[str], log_enabled: bool):
        self._log_path = log_path
        self._log_enabled = log_enabled
        self._id = self._model = self._content = ""
        self._finish_reason: Optional[str] = None
        self._usage: Optional[Dict[str, Any]] = None
        self._logged = False

    def _collect(self, chunk: ChatCompletionChunk) -> None:
        self._id = self._id or getattr(chunk, 'id', '')
        self._model = self._model or getattr(chunk, 'model', '')
        if chunk.usage:
            u = chunk.usage
            self._usage = (
                u.model_dump() if hasattr(u, 'model_dump') else u.dict()
            )
        if chunk.choices:
            choice = chunk.choices[0]
            if choice.delta and choice.delta.content:
                self._content += choice.delta.content
            if choice.finish_reason:
                self._finish_reason = choice.finish_reason

    def _log(self) -> None:
        if self._logged or not self._log_enabled or not self._log_path:
            return
        self._logged = True
        import json
        from datetime import datetime

        try:
            with open(self._log_path, "r+") as f:
                data = json.load(f)
                data["response_timestamp"] = datetime.now().isoformat()
                data["response"] = {
                    "id": self._id,
                    "model": self._model,
                    "content": self._content,
                    "finish_reason": self._finish_reason,
                    "usage": self._usage,
                    "streaming": True,
                }
                f.seek(0)
                json.dump(data, f, indent=4)
                f.truncate()
        except Exception:
            pass


class _SyncStreamWrapper(_StreamLogger):
    r"""Sync stream wrapper with logging."""

    def __init__(
        self,
        stream: Union[
            Stream[ChatCompletionChunk],
            Generator[ChatCompletionChunk, None, None],
        ],
        log_path: Optional[str],
        log_enabled: bool,
    ):
        super().__init__(log_path, log_enabled)
        self._stream = stream

    def __iter__(self):
        return self

    def __next__(self) -> ChatCompletionChunk:
        try:
            chunk = next(self._stream)
            self._collect(chunk)
            return chunk
        except StopIteration:
            self._log()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def __del__(self):
        self._log()


class _AsyncStreamWrapper(_StreamLogger):
    r"""Async stream wrapper with logging."""

    def __init__(
        self,
        stream: Union[
            AsyncStream[ChatCompletionChunk],
            AsyncGenerator[ChatCompletionChunk, None],
        ],
        log_path: Optional[str],
        log_enabled: bool,
    ):
        super().__init__(log_path, log_enabled)
        self._stream = stream

    def __aiter__(self):
        return self

    async def __anext__(self) -> ChatCompletionChunk:
        try:
            chunk = await self._stream.__anext__()
            self._collect(chunk)
            return chunk
        except StopAsyncIteration:
            self._log()
            raise

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False

    def __del__(self):
        self._log()


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
        timeout: Optional[float] = Constants.TIMEOUT_THRESHOLD,
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
        # Initialize logging configuration
        self._log_enabled = (
            os.environ.get("CAMEL_MODEL_LOG_ENABLED", "False").lower()
            == "true"
        )
        self._log_dir = os.environ.get("CAMEL_LOG_DIR", "camel_logs")

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

    def _log_request(self, messages: List[OpenAIMessage]) -> Optional[str]:
        r"""Log the request messages to a JSON file if logging is enabled.

        Args:
            messages (List[OpenAIMessage]): The messages to log.

        Returns:
            Optional[str]: The path to the log file if logging is enabled,
                None otherwise.
        """
        if not self._log_enabled:
            return None

        import json
        from datetime import datetime

        from camel.utils.agent_context import get_current_agent_id

        agent_id = get_current_agent_id()

        # Remove _context_summarizer suffix to keep all logs in one directory
        log_agent_id = agent_id
        if agent_id and agent_id.endswith("_context_summarizer"):
            log_agent_id = agent_id[: -len("_context_summarizer")]

        log_subdir = (
            os.path.join(self._log_dir, log_agent_id)
            if log_agent_id
            else self._log_dir
        )
        os.makedirs(log_subdir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        log_file_path = os.path.join(log_subdir, f"conv_{timestamp}.json")

        log_entry = {
            "request_timestamp": datetime.now().isoformat(),
            "model": str(self.model_type),
            "agent_id": agent_id,
            "request": {"messages": messages},
        }

        with open(log_file_path, "w") as f:
            json.dump(log_entry, f, indent=4)

        return log_file_path

    def _log_response(self, log_path: str, response: Any) -> None:
        r"""Log the response to the existing log file.

        Args:
            log_path (str): The path to the log file.
            response (Any): The response to log.
        """
        if not self._log_enabled or not log_path:
            return

        import json
        from datetime import datetime

        with open(log_path, "r+") as f:
            log_data = json.load(f)

            log_data["response_timestamp"] = datetime.now().isoformat()
            if isinstance(response, BaseModel):
                log_data["response"] = response.model_dump()
            else:
                try:
                    json.dumps(response)
                    log_data["response"] = response
                except TypeError:
                    log_data["response"] = str(response)

            f.seek(0)
            json.dump(log_data, f, indent=4)
            f.truncate()

    def _log_and_trace(self) -> None:
        r"""Update Langfuse trace with session metadata.

        This method updates the current Langfuse trace with agent session
        information and model metadata. Called at the start of _run() and
        _arun() methods before API execution.
        """
        agent_session_id = get_current_agent_session_id()
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

    @abstractmethod
    def _run(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[
        ChatCompletion,
        Stream[ChatCompletionChunk],
        ChatCompletionStreamManager[BaseModel],
    ]:
        r"""Runs the query to the backend model in a non-stream mode.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.
            response_format (Optional[Type[BaseModel]]): The format of the
                response.
            tools (Optional[List[Dict[str, Any]]]): The schema of the tools to
                use for the request.

        Returns:
            Union[ChatCompletion, Stream[ChatCompletionChunk], Any]:
                `ChatCompletion` in the non-stream mode, or
                `Stream[ChatCompletionChunk]` in the stream mode,
                or `ChatCompletionStreamManager[BaseModel]` in the structured
                stream mode.
        """
        pass

    @abstractmethod
    async def _arun(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[
        ChatCompletion,
        AsyncStream[ChatCompletionChunk],
        AsyncChatCompletionStreamManager[BaseModel],
    ]:
        r"""Runs the query to the backend model in async non-stream mode.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.
            response_format (Optional[Type[BaseModel]]): The format of the
                response.
            tools (Optional[List[Dict[str, Any]]]): The schema of the tools to
                use for the request.

        Returns:
            Union[ChatCompletion, AsyncStream[ChatCompletionChunk], Any]:
                `ChatCompletion` in the non-stream mode, or
                `AsyncStream[ChatCompletionChunk]` in the stream mode,
                or `AsyncChatCompletionStreamManager[BaseModel]` in the
                structured stream mode.
        """
        pass

    @observe()
    def run(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[
        ChatCompletion,
        Stream[ChatCompletionChunk],
        ChatCompletionStreamManager[BaseModel],
    ]:
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
            Union[ChatCompletion, Stream[ChatCompletionChunk], Any]:
                `ChatCompletion` in the non-stream mode,
                `Stream[ChatCompletionChunk]` in the stream mode, or
                `ChatCompletionStreamManager[BaseModel]` in the structured
                stream mode.
        """
        # Log the request if logging is enabled
        log_path = self._log_request(messages)

        # None -> use default tools
        if tools is None:
            tools = self.model_config_dict.get("tools", None)
        # Empty -> use no tools
        elif not tools:
            tools = None

        logger.info("Running model: %s", self.model_type)
        logger.info("Messages: %s", messages)
        logger.info("Response format: %s", response_format)
        logger.info("Tools: %s", tools)

        result = self._run(messages, response_format, tools)
        logger.info("Result: %s", result)

        # For streaming responses, wrap with logging; otherwise log immediately
        if isinstance(result, Stream) or inspect.isgenerator(result):
            return _SyncStreamWrapper(  # type: ignore[return-value]
                result, log_path, self._log_enabled
            )
        if log_path:
            self._log_response(log_path, result)
        return result

    @observe()
    async def arun(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[
        ChatCompletion,
        AsyncStream[ChatCompletionChunk],
        AsyncChatCompletionStreamManager[BaseModel],
    ]:
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
            Union[ChatCompletion, AsyncStream[ChatCompletionChunk], Any]:
                `ChatCompletion` in the non-stream mode,
                `AsyncStream[ChatCompletionChunk]` in the stream mode, or
                `AsyncChatCompletionStreamManager[BaseModel]` in the structured
                stream mode.
        """
        # Log the request if logging is enabled
        log_path = self._log_request(messages)

        if tools is None:
            tools = self.model_config_dict.get("tools", None)
        elif not tools:
            tools = None

        logger.info("Running model: %s", self.model_type)
        logger.info("Messages: %s", messages)
        logger.info("Response format: %s", response_format)
        logger.info("Tools: %s", tools)

        result = await self._arun(messages, response_format, tools)
        logger.info("Result: %s", result)

        # For streaming responses, wrap with logging; otherwise log immediately
        if isinstance(result, AsyncStream) or inspect.isasyncgen(result):
            return _AsyncStreamWrapper(  # type: ignore[return-value]
                result, log_path, self._log_enabled
            )
        if log_path:
            self._log_response(log_path, result)
        return result

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
        return self.model_type.token_limit

    @property
    def stream(self) -> bool:
        r"""Returns whether the model is in stream mode, which sends partial
        results each time.

        Returns:
            bool: Whether the model is in stream mode.
        """
        return False
