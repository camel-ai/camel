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

r"""
Agent logging utilities for CAMEL.

This module provides utilities to enable automatic logging of agent
interactions with LLMs by wrapping the model backend.

Note:
    This implementation wraps the public `model_backend` attribute and
    intercepts the public `run()` and `arun()` methods. This is safer
    than monkey-patching private methods, as it only relies on the
    public API which is guaranteed to be stable.
"""

from typing import Any, Dict, List, Optional, Type, Union

from openai import AsyncStream, Stream
from openai.lib.streaming.chat import (
    AsyncChatCompletionStreamManager,
    ChatCompletionStreamManager,
)
from openai.types.chat import ChatCompletion, ChatCompletionChunk
from pydantic import BaseModel

from camel.agents import ChatAgent
from camel.logging.prompt_logger import PromptLogger


# Global logger instance
_prompt_logger: Optional[PromptLogger] = None
_original_init = None
_patching_enabled = False


class LoggingModelBackend:
    r"""Wrapper for model backend that logs all interactions.

    This class wraps a model backend and intercepts its `run()` and `arun()`
    methods to log prompts and responses. It acts as a transparent proxy,
    forwarding all other attribute accesses to the wrapped backend.

    Args:
        backend: The model backend to wrap.
        logger: The PromptLogger instance to use for logging.
    """

    def __init__(self, backend: Any, logger: PromptLogger) -> None:
        # Use object.__setattr__ to avoid triggering __setattr__
        object.__setattr__(self, '_backend', backend)
        object.__setattr__(self, '_logger', logger)

    def run(
        self,
        messages: List[Dict[str, Any]],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[
        ChatCompletion,
        Stream[ChatCompletionChunk],
        ChatCompletionStreamManager[BaseModel],
    ]:
        r"""Run the model and log the interaction.

        Args:
            messages: Message list in OpenAI format.
            response_format: Optional response format.
            tools: Optional tools schema.

        Returns:
            The model response.
        """
        # Call the original run method
        response = self._backend.run(messages, response_format, tools)

        # Log the complete conversation (input + output)
        if self._logger and isinstance(response, ChatCompletion):
            # Create a copy of messages and add the assistant response
            full_messages = list(messages)

            # Extract assistant response from ChatCompletion
            if response.choices and len(response.choices) > 0:
                assistant_message = {
                    "role": "assistant",
                    "content": response.choices[0].message.content or "",
                }
                full_messages.append(assistant_message)

            # Log the complete conversation
            model_info = str(self._backend.model_type)
            self._logger.log_prompt(full_messages, model_info=model_info)

        return response

    async def arun(
        self,
        messages: List[Dict[str, Any]],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[
        ChatCompletion,
        AsyncStream[ChatCompletionChunk],
        AsyncChatCompletionStreamManager[BaseModel],
    ]:
        r"""Run the model asynchronously and log the interaction.

        Args:
            messages: Message list in OpenAI format.
            response_format: Optional response format.
            tools: Optional tools schema.

        Returns:
            The model response.
        """
        # Call the original arun method
        response = await self._backend.arun(messages, response_format, tools)

        # Log the complete conversation (input + output)
        if self._logger and isinstance(response, ChatCompletion):
            # Create a copy of messages and add the assistant response
            full_messages = list(messages)

            # Extract assistant response from ChatCompletion
            if response.choices and len(response.choices) > 0:
                assistant_message = {
                    "role": "assistant",
                    "content": response.choices[0].message.content or "",
                }
                full_messages.append(assistant_message)

            # Log the complete conversation
            model_info = str(self._backend.model_type)
            self._logger.log_prompt(full_messages, model_info=model_info)

        return response

    def __getattr__(self, name: str) -> Any:
        r"""Proxy all other attributes to the wrapped backend."""
        return getattr(self._backend, name)

    def __setattr__(self, name: str, value: Any) -> None:
        r"""Proxy all attribute sets to the wrapped backend."""
        if name in ('_backend', '_logger'):
            object.__setattr__(self, name, value)
        else:
            setattr(self._backend, name, value)


def enable_agent_logging(
    log_file_path: str,
    verbose: bool = True,
) -> PromptLogger:
    r"""Enable automatic logging for all ChatAgent interactions.

    This function wraps the ChatAgent's model backend to automatically log
    all prompts and responses. The logging captures the complete conversation
    including system messages, user inputs, and assistant responses.

    Note:
        This implementation wraps the public `model_backend` attribute and
        only relies on public methods (`run()` and `arun()`). This is safer
        than monkey-patching private methods as it uses the stable public API.

    Args:
        log_file_path (str): Path to the log file where prompts will
            be saved.
        verbose (bool, optional): Whether to print confirmation messages.
            (default: :obj:`True`)

    Returns:
        PromptLogger: The logger instance being used for logging.

    Raises:
        RuntimeError: If logging is already enabled.

    Example:
        >>> from camel.logging import enable_agent_logging
        >>> logger = enable_agent_logging("agent_logs.log")
        >>> # Now all ChatAgent interactions will be logged automatically
        >>> agent = ChatAgent(...)
        >>> response = agent.step(user_msg)
        >>> # The interaction is logged in agent_logs.log
    """
    global _prompt_logger, _original_init, _patching_enabled

    if _patching_enabled:
        raise RuntimeError(
            "Agent logging is already enabled. "
            "Call disable_agent_logging() first if you want to change "
            "the log file."
        )

    # Create the logger
    _prompt_logger = PromptLogger(log_file_path)

    # Store the original __init__ method
    _original_init = ChatAgent.__init__

    def logged_init(self, *args, **kwargs):
        r"""Wrapper for __init__ that wraps the model backend."""
        # Call the original __init__
        _original_init(self, *args, **kwargs)

        # Wrap the model_backend with logging
        if _prompt_logger:
            self.model_backend = LoggingModelBackend(
                self.model_backend,
                _prompt_logger
            )

    # Apply the patch to __init__
    ChatAgent.__init__ = logged_init
    _patching_enabled = True

    if verbose:
        print("✅ Agent logging enabled")
        print(f"📝 Logging to: {log_file_path}\n")

    return _prompt_logger


def disable_agent_logging(verbose: bool = True) -> None:
    r"""Disable automatic logging for ChatAgent interactions.

    This function restores the original ChatAgent behavior by removing
    the backend wrapper.

    Args:
        verbose (bool, optional): Whether to print confirmation messages.
            (default: :obj:`True`)

    Example:
        >>> from camel.logging import disable_agent_logging
        >>> disable_agent_logging()
        >>> # Agent interactions are no longer logged
    """
    global _prompt_logger, _original_init, _patching_enabled

    if not _patching_enabled:
        if verbose:
            print("⚠️  Agent logging is not currently enabled")
        return

    # Restore the original __init__ method
    if _original_init is not None:
        ChatAgent.__init__ = _original_init

    _prompt_logger = None
    _original_init = None
    _patching_enabled = False

    if verbose:
        print("✅ Agent logging disabled\n")


def get_logger() -> Optional[PromptLogger]:
    r"""Get the current PromptLogger instance if logging is enabled.

    Returns:
        Optional[PromptLogger]: The logger instance, or None if logging
            is not enabled.

    Example:
        >>> from camel.logging import get_logger
        >>> logger = get_logger()
        >>> if logger:
        ...     stats = logger.get_stats()
        ...     print(f"Logged {stats['total_prompts']} prompts")
    """
    return _prompt_logger


def is_logging_enabled() -> bool:
    r"""Check if agent logging is currently enabled.

    Returns:
        bool: True if logging is enabled, False otherwise.

    Example:
        >>> from camel.logging import is_logging_enabled
        >>> if is_logging_enabled():
        ...     print("Logging is active")
    """
    return _patching_enabled
