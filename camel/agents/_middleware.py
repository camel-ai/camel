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
from dataclasses import dataclass
from typing import List

from camel.messages import OpenAIMessage
from camel.types import ChatCompletion, UnifiedModelType


@dataclass
class MiddlewareContext:
    r"""Context information passed to middleware during processing.

    Attributes:
        model_type (UnifiedModelType): The type of model being used.
        agent_id (str): The unique identifier of the agent.
        iteration (int): The current iteration number within the agent
            step loop.
    """

    model_type: UnifiedModelType
    agent_id: str
    iteration: int


class MiddlewareError(Exception):
    r"""Raised when a middleware fails during request or response processing.

    Attributes:
        middleware_name (str): The class name of the middleware that failed.
        phase (str): The phase in which the error occurred
            (``"process_request"`` or ``"process_response"``).
    """

    def __init__(self, message: str, middleware_name: str, phase: str) -> None:
        super().__init__(message)
        self.middleware_name = middleware_name
        self.phase = phase


class MessageMiddleware:
    r"""Base class for message middleware.

    Middleware provides a unified hook mechanism for intercepting and
    modifying messages before they are sent to the model backend
    (pre-invocation) and responses after they are received
    (post-invocation).

    """

    def process_request(
        self,
        messages: List[OpenAIMessage],
        context: MiddlewareContext,
    ) -> List[OpenAIMessage]:
        r"""Process messages before sending to the model backend.

        Args:
            messages (List[OpenAIMessage]): The messages to be sent to
                the model.
            context (MiddlewareContext): Context about the current
                invocation.

        Returns:
            List[OpenAIMessage]: The processed messages.
        """
        return messages

    def process_response(
        self,
        response: ChatCompletion,
        context: MiddlewareContext,
    ) -> ChatCompletion:
        r"""Process the response received from the model backend.

        Args:
            response (ChatCompletion): The model response.
            context (MiddlewareContext): Context about the current
                invocation.

        Returns:
            ChatCompletion: The processed response.
        """
        return response
