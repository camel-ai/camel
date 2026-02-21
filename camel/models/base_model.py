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
from abc import ABC, abstractmethod
from contextvars import ContextVar
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


class _ClientLoggingProxy:
    r"""Proxy that syncs request logs with final client call payloads."""

    def __init__(self, target: Any, backend: "BaseModelBackend"):
        self._target = target
        self._backend = backend

    @staticmethod
    def _is_passthrough_value(value: Any) -> bool:
        return isinstance(
            value,
            (
                str,
                bytes,
                int,
                float,
                bool,
                type(None),
                dict,
                list,
                tuple,
                set,
            ),
        )

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._target, name)
        if name.startswith("__") or self._is_passthrough_value(attr):
            return attr
        return _ClientLoggingProxy(attr, self._backend)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        normalized_kwargs = self._backend._normalize_client_call_kwargs(
            self._target, args, kwargs
        )
        if self._backend._should_sync_request_log(normalized_kwargs):
            self._backend._sync_request_log_with_client_kwargs(
                normalized_kwargs
            )
        return self._target(*args, **kwargs)

    def __repr__(self) -> str:
        return repr(self._target)


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
            with open(self._log_path, "r+", encoding="utf-8") as f:
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
                json.dump(data, f, indent=4, ensure_ascii=False, default=str)
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
    r"""Metaclass that automatically pre/post-processes the run method.

    Automatically wraps the run and arun methods of any class inheriting from
    BaseModelBackend to:
    - Preprocess messages (remove <think> tags) before sending to the model.
    - Postprocess responses (extract <think> tags into reasoning_content)
      after receiving from the model.
    """

    def __new__(mcs, name, bases, namespace):
        r"""Wraps run/arun methods with pre/post-processing."""
        if 'run' in namespace:
            original_run = namespace['run']

            def wrapped_run(
                self, messages: List[OpenAIMessage], *args, **kwargs
            ):
                messages = self.preprocess_messages(messages)
                result = original_run(self, messages, *args, **kwargs)
                result = self.postprocess_response(result)
                return result

            namespace['run'] = wrapped_run

        if 'arun' in namespace:
            original_arun = namespace['arun']

            async def wrapped_arun(
                self, messages: List[OpenAIMessage], *args, **kwargs
            ):
                messages = self.preprocess_messages(messages)
                result = await original_arun(self, messages, *args, **kwargs)
                result = self.postprocess_response(result)
                return result

            namespace['arun'] = wrapped_arun

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
        extract_thinking_from_response (bool, optional): Whether to
            extract ``<think>`` tags from model response content into
            the ``reasoning_content`` field. When enabled, if a model
            embeds reasoning in ``<think>`` tags within the response
            content (and ``reasoning_content`` is not already set),
            the tags will be extracted into ``reasoning_content`` and
            removed from ``content``. (default: :obj:`True`)
    """

    def __setattr__(self, name: str, value: Any) -> None:
        if (
            name in {"_client", "_async_client"}
            and value is not None
            and not isinstance(value, _ClientLoggingProxy)
        ):
            value = _ClientLoggingProxy(value, self)
        super().__setattr__(name, value)

    def __init__(
        self,
        model_type: Union[ModelType, str],
        model_config_dict: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        token_counter: Optional[BaseTokenCounter] = None,
        timeout: Optional[float] = Constants.TIMEOUT_THRESHOLD,
        max_retries: int = 3,
        extract_thinking_from_response: bool = True,
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
        self._extract_thinking_from_response = extract_thinking_from_response
        # Initialize logging configuration
        self._log_enabled = os.environ.get(
            "CAMEL_MODEL_LOG_ENABLED", "False"
        ).strip().lower() in {"1", "true", "yes", "on"}
        default_model_config_log = "True" if self._log_enabled else "False"
        self._log_model_config_dict_enabled = os.environ.get(
            "CAMEL_MODEL_LOG_MODEL_CONFIG_ENABLED",
            default_model_config_log,
        ).strip().lower() in {"1", "true", "yes", "on"}
        self._log_dir = os.environ.get("CAMEL_LOG_DIR", "camel_logs")
        self._log_path_context: ContextVar[Optional[str]] = ContextVar(
            f"camel_model_log_path_{id(self)}",
            default=None,
        )

    @property
    @abstractmethod
    def token_counter(self) -> BaseTokenCounter:
        r"""Initialize the token counter for the model backend.

        Returns:
            BaseTokenCounter: The token counter following the model's
                tokenization style.
        """
        pass

    def _prepare_request_config(
        self,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        r"""Prepare the request configuration dictionary.

        Creates a deep copy of the model config and handles tool-related
        parameters. If no tools are specified, removes parallel_tool_calls
        as OpenAI API only allows it when tools are present.

        Args:
            tools (Optional[List[Dict[str, Any]]]): The tools to include
                in the request. (default: :obj:`None`)

        Returns:
            Dict[str, Any]: The prepared request configuration.
        """
        import copy

        request_config = copy.deepcopy(self.model_config_dict)

        if tools:
            request_config["tools"] = tools
        else:
            # Remove parallel_tool_calls if no tools are specified
            # as OpenAI API only allows it when tools are present
            request_config.pop("parallel_tool_calls", None)

        return request_config

    def _resolve_tools(
        self,
        tools: Optional[List[Dict[str, Any]]],
    ) -> Optional[List[Dict[str, Any]]]:
        r"""Resolve tools for the current request."""
        if tools is None:
            default_tools = self.model_config_dict.get("tools", None)
            return default_tools if isinstance(default_tools, list) else None
        if not tools:
            return None
        return tools

    def _build_request_log_model_config_dict(
        self,
        tools: Optional[List[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        r"""Build model_config_dict snapshot for request logging."""
        import copy

        request_log_model_config_dict = copy.deepcopy(self.model_config_dict)
        if tools is not None:
            request_log_model_config_dict["tools"] = tools
        else:
            request_log_model_config_dict.pop("tools", None)
            request_log_model_config_dict.pop("parallel_tool_calls", None)
        return request_log_model_config_dict

    def _normalize_client_call_kwargs(
        self,
        call: Any,
        args: Any,
        kwargs: Dict[str, Any],
    ) -> Dict[str, Any]:
        r"""Normalize client call arguments into a keyword dictionary."""
        if not args:
            return kwargs
        try:
            signature = inspect.signature(call)
            bound = signature.bind_partial(*args, **kwargs)
            normalized_kwargs = dict(bound.arguments)
            normalized_kwargs.pop("self", None)
            return normalized_kwargs
        except Exception:
            return kwargs

    def _should_sync_request_log(self, kwargs: Dict[str, Any]) -> bool:
        r"""Check whether a client call should sync request logs."""
        messages = kwargs.get("messages")
        return isinstance(messages, list) and len(kwargs) > 1

    def _extract_model_config_from_client_kwargs(
        self, kwargs: Dict[str, Any]
    ) -> Dict[str, Any]:
        r"""Extract model config payload from client call kwargs."""
        import copy

        model_config_dict: Dict[str, Any] = {}
        for key, value in kwargs.items():
            if key in {"messages", "model"}:
                continue
            try:
                model_config_dict[key] = copy.deepcopy(value)
            except Exception:
                model_config_dict[key] = value
        return model_config_dict

    def _sync_request_log_with_client_kwargs(
        self, kwargs: Dict[str, Any]
    ) -> None:
        r"""Sync request log with final payload passed to the model client."""
        if not self._log_enabled:
            return

        log_path = self._log_path_context.get()
        if not log_path:
            return

        messages = kwargs.get("messages")
        if not isinstance(messages, list):
            return

        import copy
        import json

        try:
            logged_messages = copy.deepcopy(messages)
        except Exception:
            logged_messages = messages

        request_entry: Dict[str, Any] = {"messages": logged_messages}
        if self._log_model_config_dict_enabled:
            request_entry["model_config_dict"] = (
                self._extract_model_config_from_client_kwargs(kwargs)
            )

        try:
            with open(log_path, "r+", encoding="utf-8") as f:
                log_data = json.load(f)
                log_data["request"] = request_entry
                f.seek(0)
                json.dump(
                    log_data,
                    f,
                    indent=4,
                    ensure_ascii=False,
                    default=str,
                )
                f.truncate()
        except Exception:
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

        from camel.models._utils import extract_thinking_from_content

        for msg in messages:
            # Remove thinking content if needed
            role = msg.get('role')
            content = msg.get('content')
            if (
                self._extract_thinking_from_response
                and role in ['assistant', 'user']
                and isinstance(content, str)
            ):
                content, _ = extract_thinking_from_content(content)
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

    def postprocess_response(self, response: Any) -> Any:
        r"""Postprocess model response to extract ``<think>`` tags.

        For non-streaming responses, if the model embeds reasoning in
        ``<think>`` tags within the response content (and
        ``reasoning_content`` is not already set), extracts the content
        of the tags into ``reasoning_content`` and removes them from
        ``content``.

        Streaming responses and other non-ChatCompletion types are
        returned as-is.

        Args:
            response: The model response. May be a
                :obj:`ChatCompletion`, a streaming object, or other
                types.

        Returns:
            The response, potentially with ``reasoning_content``
            populated and ``content`` cleaned.
        """
        # Skip streaming responses — they are handled downstream
        if (
            isinstance(response, (Stream, AsyncStream))
            or inspect.isgenerator(response)
            or inspect.isasyncgen(response)
        ):
            return response

        if not self._extract_thinking_from_response:
            return response

        if not hasattr(response, 'choices') or not response.choices:
            return response

        from camel.models._utils import extract_thinking_from_content

        for choice in response.choices:
            message = getattr(choice, 'message', None)
            if message is None:
                continue
            content = getattr(message, 'content', None)
            if not isinstance(content, str):
                continue
            existing = getattr(message, 'reasoning_content', None)
            message.content, reasoning = extract_thinking_from_content(
                content, existing
            )
            if reasoning is not None:
                message.reasoning_content = reasoning

        return response

    def _log_request(
        self,
        messages: List[OpenAIMessage],
        model_config_dict: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        r"""Log the request messages to a JSON file if logging is enabled.

        Args:
            messages (List[OpenAIMessage]): The messages to log.
            model_config_dict (Optional[Dict[str, Any]]): The effective
                model configuration used for this request.

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

        request_entry: Dict[str, Any] = {"messages": messages}
        if self._log_model_config_dict_enabled:
            request_entry["model_config_dict"] = (
                model_config_dict
                if model_config_dict is not None
                else self.model_config_dict
            )

        log_entry: Dict[str, Any] = {
            "request_timestamp": datetime.now().isoformat(),
            "model": str(self.model_type),
            "agent_id": agent_id,
            "request": request_entry,
        }

        with open(log_file_path, "w", encoding="utf-8") as f:
            json.dump(log_entry, f, indent=4, ensure_ascii=False, default=str)

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

        with open(log_path, "r+", encoding="utf-8") as f:
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
            json.dump(log_data, f, indent=4, ensure_ascii=False, default=str)
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
        tools = self._resolve_tools(tools)
        request_log_model_config_dict = (
            self._build_request_log_model_config_dict(tools)
            if self._log_model_config_dict_enabled
            else None
        )
        # Log the request if logging is enabled
        log_path = self._log_request(messages, request_log_model_config_dict)

        logger.info("Running model: %s", self.model_type)
        logger.info("Messages: %s", messages)
        if self._log_model_config_dict_enabled:
            logger.info("Model config dict: %s", request_log_model_config_dict)
        logger.info("Response format: %s", response_format)
        logger.info("Tools: %s", tools)

        final_log_path = log_path
        log_path_token = self._log_path_context.set(log_path)
        try:
            result = self._run(messages, response_format, tools)
            final_log_path = self._log_path_context.get() or final_log_path
        finally:
            self._log_path_context.reset(log_path_token)
        logger.info("Result: %s", result)

        # For streaming responses, wrap with logging; otherwise log immediately
        if isinstance(result, Stream) or inspect.isgenerator(result):
            return _SyncStreamWrapper(  # type: ignore[return-value]
                result, final_log_path, self._log_enabled
            )
        if final_log_path:
            self._log_response(final_log_path, result)
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
        tools = self._resolve_tools(tools)
        request_log_model_config_dict = (
            self._build_request_log_model_config_dict(tools)
            if self._log_model_config_dict_enabled
            else None
        )
        # Log the request if logging is enabled
        log_path = self._log_request(messages, request_log_model_config_dict)

        logger.info("Running model: %s", self.model_type)
        logger.info("Messages: %s", messages)
        if self._log_model_config_dict_enabled:
            logger.info("Model config dict: %s", request_log_model_config_dict)
        logger.info("Response format: %s", response_format)
        logger.info("Tools: %s", tools)

        final_log_path = log_path
        log_path_token = self._log_path_context.set(log_path)
        try:
            result = await self._arun(messages, response_format, tools)
            final_log_path = self._log_path_context.get() or final_log_path
        finally:
            self._log_path_context.reset(log_path_token)
        logger.info("Result: %s", result)

        # For streaming responses, wrap with logging; otherwise log immediately
        if isinstance(result, AsyncStream) or inspect.isasyncgen(result):
            return _AsyncStreamWrapper(  # type: ignore[return-value]
                result, final_log_path, self._log_enabled
            )
        if final_log_path:
            self._log_response(final_log_path, result)
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
