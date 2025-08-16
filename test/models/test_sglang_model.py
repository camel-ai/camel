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
from unittest.mock import MagicMock, patch

import pytest

from camel.configs import SGLangConfig
from camel.models import SGLangModel
from camel.types import ModelType, UnifiedModelType
from camel.utils import OpenAITokenCounter


@pytest.fixture
def sglang_model_cleanup():
    r"""Fixture to ensure SGLang model is cleaned up after each test."""
    models = []

    # Mock the server-related functions to avoid actual server startup
    with (
        patch(
            'camel.models.sglang_model._execute_shell_command'
        ) as mock_execute,
        patch('camel.models.sglang_model._wait_for_server') as mock_wait,
        patch('camel.models.sglang_model.OpenAI') as mock_client,
        patch('camel.models.sglang_model.AsyncOpenAI') as mock_async_client,
    ):
        # Configure mocks
        mock_execute.return_value = MagicMock()
        mock_wait.return_value = None
        mock_client.return_value = MagicMock()
        mock_async_client.return_value = MagicMock()

        def _create_model(
            model_type, model_config_dict=None, api_key="sglang"
        ):
            model = SGLangModel(model_type, model_config_dict, api_key=api_key)
            # Set up the model to use our mocks
            model._url = "http://mock-server:30000/v1"
            model._client = mock_client.return_value
            model._async_client = mock_async_client.return_value
            models.append(model)
            return model

        yield _create_model

    # Clean up all models after test
    for model in models:
        try:
            model.cleanup()
        except Exception as e:
            print(f"Error during cleanup: {e}")


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        ModelType.GPT_4,
        ModelType.GPT_4_TURBO,
        ModelType.GPT_4O,
        ModelType.GPT_4O_MINI,
    ],
)
def test_sglang_model(model_type: ModelType, sglang_model_cleanup):
    model = sglang_model_cleanup(model_type)
    assert model.model_type == model_type
    assert model.model_config_dict == SGLangConfig().as_dict()
    assert isinstance(model.token_counter, OpenAITokenCounter)
    assert isinstance(model.model_type, UnifiedModelType)
    assert isinstance(model.token_limit, int)


@pytest.mark.model_backend
def test_sglang_function_call(sglang_model_cleanup):
    test_tool = {
        "type": "function",
        "function": {
            "name": "test_tool",
            "description": "Test function",
            "parameters": {"type": "object", "properties": {}},
        },
    }

    model = sglang_model_cleanup(
        ModelType.GPT_4,
        model_config_dict={"tools": [test_tool]},
    )

    # Create a mock response object
    from openai.types.chat.chat_completion_message_function_tool_call import (
        ChatCompletionMessageFunctionToolCall,
    )

    from camel.types import (
        ChatCompletion,
        ChatCompletionMessage,
        Choice,
        CompletionUsage,
    )

    # create mock response
    mock_response = ChatCompletion(
        id="mock_id",
        object="chat.completion",
        created=1234567890,
        model="meta-llama/Meta-Llama-3.1-8B-Instruct",
        choices=[
            Choice(
                index=0,
                message=ChatCompletionMessage(
                    role="assistant",
                    content=None,
                    tool_calls=[
                        ChatCompletionMessageFunctionToolCall(
                            id="0",
                            type="function",
                            function={"name": "test_tool", "arguments": "{}"},
                        )
                    ],
                ),
                finish_reason="tool_calls",
            )
        ],
        usage=CompletionUsage(
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
        ),
    )

    # Patch the run method to return our mock response
    with patch.object(model, '_run', return_value=mock_response):
        messages = [
            {
                "role": "user",
                "content": "Use test_tool and respond with result",
            }
        ]

        response = model.run(messages=messages)

        assert len(response.choices[0].message.tool_calls) > 0
        tool_call = response.choices[0].message.tool_calls[0]
        assert tool_call.function.name == "test_tool"
