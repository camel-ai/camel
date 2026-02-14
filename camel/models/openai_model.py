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

from __future__ import annotations

import hashlib
import logging
from typing import Any, Dict, List, Optional, Union

from openai import AsyncOpenAI, OpenAI
from pydantic import BaseModel, Field

from camel.messages import OpenAIMessage
from camel.models.base_model import BaseModelBackend
from camel.types import ChatCompletion, ChatCompletionChunk, ModelType

logger = logging.getLogger(__name__)


class OpenAIModel(BaseModelBackend):
    r"""OpenAI model class that implements the BaseModelBackend interface."""

    model_config = {
        "arbitrary_types_allowed": True,
    }

    model_type: ModelType = Field(...)
    model_config_dict: Dict[str, Any] = Field(default_factory=dict)
    _async_client: Optional[AsyncOpenAI] = None
    _sync_client: Optional[OpenAI] = None

    def __init__(self, model_type: ModelType, **kwargs: Any):
        r"""Initialize the OpenAI model with the given model type and
        configuration.

        Args:
            model_type (ModelType): The type of the model.
            **kwargs: Additional keyword arguments for model configuration.
        """
        super().__init__(model_type=model_type, **kwargs)

    def _validate_tool_call_id(self, tool_call_id: str) -> str:
        """Validate and truncate tool call ID to meet OpenAI's length requirement.
        
        Args:
            tool_call_id (str): The original tool call ID
            
        Returns:
            str: Validated ID (truncated or hashed if too long)
        """
        max_length = 40
        if len(tool_call_id) <= max_length:
            return tool_call_id
        
        # Hash long IDs to ensure uniqueness while meeting length constraints
        return hashlib.sha256(tool_call_id.encode()).hexdigest()[:max_length]

    def _process_messages_for_tool_calls(
        self, messages: List[OpenAIMessage]
    ) -> List[OpenAIMessage]:
        """Process messages to ensure tool call IDs meet length requirements.
        
        Args:
            messages (List[OpenAIMessage]): List of messages to process
            
        Returns:
            List[OpenAIMessage]: Processed messages with validated tool call IDs
        """
        processed_messages = []
        for message in messages:
            if hasattr(message, "tool_calls") and message.tool_calls:
                new_tool_calls = []
                for tool_call in message.tool_calls:
                    if hasattr(tool_call, "id") and tool_call.id:
                        tool_call.id = self._validate_tool_call_id(tool_call.id)
                    new_tool_calls.append(tool_call)
                message.tool_calls = new_tool_calls
            processed_messages.append(message)
        return processed_messages

    async def _arequest_chat_completion(
        self,
        messages: List[OpenAIMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatCompletion:
        r"""Asynchronously request a chat completion from the OpenAI API.

        Args:
            messages (List[OpenAIMessage]): List of messages.
            tools (Optional[List[Dict[str, Any]]]): List of tools.
                (default: :obj:`None`)

        Returns:
            ChatCompletion: The chat completion response.
        """
        if self._async_client is None:
            self._async_client = AsyncOpenAI(**self.model_config_dict)

        # Process messages to validate tool call IDs
        processed_messages = self._process_messages_for_tool_calls(messages)

        return await self._async_client.chat.completions.create(
            model=self.model_type.value,
            messages=[msg.model_dump() for msg in processed_messages],
            tools=tools,
            **self._get_non_none_fields(),
        )

    def _request_chat_completion(
        self,
        messages: List[OpenAIMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatCompletion:
        r"""Request a chat completion from the OpenAI API.

        Args:
            messages (List[OpenAIMessage]): List of messages.
            tools (Optional[List[Dict[str, Any]]]): List of tools.
                (default: :obj:`None`)

        Returns:
            ChatCompletion: The chat completion response.
        """
        if self._sync_client is None:
            self._sync_client = OpenAI(**self.model_config_dict)

        # Process messages to validate tool call IDs
        processed_messages = self._process_messages_for_tool_calls(messages)

        return self._sync_client.chat.completions.create(
            model=self.model_type.value,
            messages=[msg.model_dump() for msg in processed_messages],
            tools=tools,
            **self._get_non_none_fields(),
        )

    async def _astream_chat_completion(
        self,
        messages: List[OpenAIMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Any:
        r"""Asynchronously stream a chat completion from the OpenAI API.

        Args:
            messages (List[OpenAIMessage]): List of messages.
            tools (Optional[List[Dict[str, Any]]]): List of tools.
                (default: :obj:`None`)

        Returns:
            Any: The chat completion stream response.
        """
        if self._async_client is None:
            self._async_client = AsyncOpenAI(**self.model_config_dict)

        # Process messages to validate tool call IDs
        processed_messages = self._process_messages_for_tool_calls(messages)

        return await self._async_client.chat.completions.create(
            model=self.model_type.value,
            messages=[msg.model_dump() for msg in processed_messages],
            tools=tools,
            stream=True,
            **self._get_non_none_fields(),
        )

    def _stream_chat_completion(
        self,
        messages: List[OpenAIMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Any:
        r"""Stream a chat completion from the OpenAI API.

        Args:
            messages (List[OpenAIMessage]): List of messages.
            tools (Optional[List[Dict[str, Any]]]): List of tools.
                (default: :obj:`None`)

        Returns:
            Any: The chat completion stream response.
        """
        if self._sync_client is None:
            self._sync_client = OpenAI(**self.model_config_dict)

        # Process messages to validate tool call IDs
        processed_messages = self._process_messages_for_tool_calls(messages)

        return self._sync_client.chat.completions.create(
            model=self.model_type.value,
            messages=[msg.model_dump() for msg in processed_messages],
            tools=tools,
            stream=True,
            **self._get_non_none_fields(),
        )