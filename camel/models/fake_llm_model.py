# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
from typing import Any, Dict, List, Optional, Union

from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_message import (
    ChatCompletionMessage,
    FunctionCall,
)
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
)
from openai.types.completion_usage import CompletionUsage

from camel.configs import ChatGPTConfig
from camel.messages import OpenAIMessage
from camel.models import BaseModelBackend
from camel.types import (
    ChatCompletion,
    ModelType,
)
from camel.utils import (
    BaseTokenCounter,
    FakeTokenCounter,
)


class FakeLLMModel(BaseModelBackend):
    r"""Fake LLM for test purposes. Users can set mock responses for
        specific inputs.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created.
        model_config_dict (Optional[Dict[str, Any]], optional): A dictionary
            that will be fed into:obj:`openai.ChatCompletion.create()`. If
            :obj:`None`, :obj:`ChatGPTConfig().as_dict()` will be used.
            (default: :obj:`None`)
        api_key (Optional[str], optional): The API key for authenticating
            with the OpenAI service. (default: :obj:`None`)
        url (Optional[str], optional): The url to the OpenAI service.
            (default: :obj:`None`)
        token_counter (Optional[BaseTokenCounter], optional): Token counter to
            use for the model. If not provided, :obj:`OpenAITokenCounter` will
            be used. (default: :obj:`None`)
        responses (Optional[Dict[str, str]], optional): A dictionary of mock
            user messages and corresponding responses. If the user message is
            found in the dictionary, the response will be returned; otherwise
            it will be "I'm not sure how to respond to that."
            (default: :obj:`None`)
        completion_kwargs (Optional[Dict[str, Any]], optional): A dictionary of
            completion kwargs to be used in the mock response choices.
            (default: :obj:`None`)
    """

    def __init__(
        self,
        model_type: Union[ModelType, str],
        model_config_dict: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        token_counter: Optional[BaseTokenCounter] = None,
        responses: Optional[Dict[str, str]] = None,
        completion_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize config dictionary with ChatGPTConfig if not provided.
        Fake llm doesn't actually use model_config_dict,
        just for compatibility."""
        if model_config_dict is None:
            model_config_dict = ChatGPTConfig().as_dict()
        super().__init__(
            model_type, model_config_dict, api_key, url, token_counter
        )

        # Default mock responses, can be overridden by user-defined responses
        self._responses = {
            "Hi!": "Hello!",
            "What is the weather today?": "It's sunny outside.",
            "Tell me a joke.": "Why don't skeletons fight each other? "
            "They don't have the guts!",
        }
        if responses:
            self._responses.update(responses)

        self._completion_kwargs = {"function_call": None, "tool_calls": None}
        if completion_kwargs:
            self._completion_kwargs.update(completion_kwargs)

    def set_mock_response(self, user_input: str, response: str) -> None:
        """Allow users to set or update a mock response dynamically.

        Args:
            user_input (str): The input query to match.
            response (str): The response to return for the given input.
        """
        self._responses[user_input] = response

    # Ensure the function_call type is correct
    def _get_function_call(self) -> Optional[FunctionCall]:
        value = self._completion_kwargs.get("function_call")
        if isinstance(value, FunctionCall):
            return value
        return None

    # Ensure the tool_calls type is correct
    def _get_tool_calls(self) -> Optional[List[ChatCompletionMessageToolCall]]:
        value = self._completion_kwargs.get("tool_calls")
        if isinstance(value, list):
            return value
        return None

    @property
    def token_counter(self) -> BaseTokenCounter:
        """Initialize the mock token counter for testing."""
        if not self._token_counter:
            self._token_counter = FakeTokenCounter()
        return self._token_counter

    def run(
        self,
        messages: List[OpenAIMessage],
    ) -> ChatCompletion:
        r"""Simulates running a query to a backend model.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.

        Returns:
            ChatCompletion:
                A ChatCompletion object formatted for the OpenAI API.
                The stream mode is not supported in fake model, so it always
                returns a single ChatCompletion object. The response content
                is determined by the last user message in the input list.
                Users cam specify mock responses for specific inputs in
                initialization or using `set_mock_response()` method.
        """
        user_message = ""
        content = messages[-1].get("content")
        if isinstance(content, str):
            user_message = content
        elif isinstance(content, List):
            for c in content:
                if c["type"] == "text":
                    user_message = c["text"]

        response_content = self._responses.get(
            user_message, "I'm not sure how to respond to that."
        )

        # Create a mock response in ChatCompletion format
        mock_response = ChatCompletion(
            id="mock_response_id",
            choices=[
                Choice(
                    finish_reason="stop",
                    index=0,
                    logprobs=None,
                    message=ChatCompletionMessage(
                        content=response_content,
                        role="assistant",
                        function_call=self._get_function_call(),
                        tool_calls=self._get_tool_calls(),
                    ),
                )
            ],
            created=123456789,
            model="mock-model-2024",
            object="chat.completion",
            system_fingerprint="mock_fp_123456",
            usage=CompletionUsage(
                completion_tokens=len(response_content.split()),
                prompt_tokens=self.count_tokens_from_messages(messages),
                total_tokens=len(response_content.split())
                + self.count_tokens_from_messages(messages),
            ),
        )
        return mock_response

    def check_model_config(self):
        """Check the configuration for the mock backend.
        For mock LLM, we assume that all configs are acceptable
        for the mock model."""
        pass
