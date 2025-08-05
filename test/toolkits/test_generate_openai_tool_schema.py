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

from camel.agents import ChatAgent
from camel.models import BaseModelBackend
from camel.toolkits import FunctionTool, generate_docstring


def sample_function(a: int, b: str = "default") -> bool:
    """
    This function checks if the integer is positive and
    if the string is non-empty.

    Args:
        a (int): The integer value to check.
        b (str): The string to verify. Default is 'default'.

    Returns:
        bool: True if both conditions are met, otherwise False.
    """
    return a > 0 and len(b) > 0


@patch.object(FunctionTool, 'validate_openai_tool_schema')
@patch.object(FunctionTool, 'synthesize_openai_tool_schema')
def test_synthesize_openai_tool_schema(
    mock_generate_schema, mock_validate_schema
):
    # Mock the validate_openai_tool_schema return None
    mock_validate_schema.return_value = None

    # Mock the synthesize_openai_tool_schema to return a specific schema
    mock_schema = {
        'type': 'function',
        'function': {
            'name': 'sample_function',
            'description': (
                'This function checks if the integer is positive and\n'
                'if the string is non-empty.'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'a': {
                        'type': 'integer',
                        'description': 'The integer value to check.',
                    },
                    'b': {
                        'type': 'string',
                        'description': (
                            "The string to verify. Default is 'default'."
                        ),
                        'default': 'default',
                    },
                },
                'required': ['a'],
            },
        },
    }
    mock_generate_schema.return_value = mock_schema

    # Create FunctionTool instance with synthesize_schema=True
    function_tool = FunctionTool(
        func=sample_function,
        synthesize_schema=True,
        synthesize_schema_model=None,
    )

    # Assert that the generated schema matches the expected schema
    assert function_tool.openai_tool_schema == mock_schema
    mock_generate_schema.assert_called_once()


@pytest.fixture
def mock_model():
    # Create a mock model to simulate BaseModelBackend behavior
    mock_model = MagicMock(spec=BaseModelBackend)
    mock_model.model_type = MagicMock()
    mock_model.model_type.value_for_tiktoken = "mock_value_for_tiktoken"
    mock_model.model_config_dict = {}
    mock_model.value_for_tiktoken = MagicMock(return_value=1000)
    return mock_model


@patch('camel.models.ModelFactory.create')
@patch.object(ChatAgent, 'step')
def test_generate_docstring(
    mock_chat_agent_step, mock_model_factory, mock_model
):
    code = """
    def sample_function(a: int, b: str = "default") -> bool:
        return a > 0 and len(b) > 0
    """

    # Mock the model factory to return the mock model
    mock_model_factory.return_value = mock_model

    # Ensure mock_model has required attributes
    mock_model.model_type = MagicMock()
    mock_model.model_type.value_for_tiktoken = "mock_value_for_tiktoken"
    mock_model.model_config_dict = {}
    mock_model.value_for_tiktoken = MagicMock(return_value=1000)

    # Mock ChatAgent's step method return value
    mock_message = MagicMock()
    mock_message.content = (
        "This function checks if the integer is positive and "
        "if the string is non-empty.\n"
        "Args:\n    a (int): The integer value to check.\n"
        "    b (str): The string to verify. Default is 'default'.\n"
        "Returns:\n    bool: True if both conditions are met, "
        "otherwise False."
    )
    mock_response = MagicMock()
    mock_response.msgs = [mock_message]
    mock_response.msg = mock_message
    mock_response.terminated = True
    mock_chat_agent_step.return_value = mock_response

    # Generate docstring
    try:
        docstring = generate_docstring(code, mock_model)
    except AttributeError as e:
        pytest.fail(
            f"generate_docstring() raised AttributeError unexpectedly: {e}"
        )
    except RuntimeError as e:
        pytest.fail(
            f"generate_docstring() raised RuntimeError unexpectedly: {e}"
        )

    expected_docstring = (
        "This function checks if the integer is positive and "
        "if the string is non-empty.\n"
        "Args:\n    a (int): The integer value to check.\n"
        "    b (str): The string to verify. Default is 'default'.\n"
        "Returns:\n    bool: True if both conditions are met, "
        "otherwise False."
    )

    assert docstring == expected_docstring


@patch('camel.models.ModelFactory.create')
@patch.object(ChatAgent, 'step')
def test_function_tool_generate_schema_with_retries(
    mock_chat_agent_step, mock_model_factory
):
    # Mock the model factory to return a mock model
    mock_model = MagicMock(spec=BaseModelBackend)
    mock_model.model_type = MagicMock()
    mock_model.model_type.value_for_tiktoken = "mock_value_for_tiktoken"
    mock_model.model_config_dict = {}
    mock_model.value_for_tiktoken = MagicMock(return_value=1000)
    mock_model_factory.return_value = mock_model

    # Mock ChatAgent's step method to simulate retries
    mock_message = MagicMock()
    mock_message.content = (
        "This function checks if the integer is positive and\n"
        "if the string is non-empty.\n"
        "Args:\n    a (int): The integer value to check.\n"
        "    b (str): The string to verify. Default is 'default'.\n"
        "Returns:\n    bool: True if both conditions are met, otherwise False."
    )
    mock_response = MagicMock()
    mock_response.msgs = [mock_message]
    mock_response.msg = mock_message
    mock_response.terminated = True

    # Configure the step method to fail the first time
    # and succeed the second time
    mock_chat_agent_step.side_effect = [
        Exception("Validation failed"),
        mock_response,
    ]

    # Create FunctionTool instance with synthesize_schema=True
    function_tool = FunctionTool(
        func=sample_function,
        synthesize_schema=True,
        synthesize_schema_model=mock_model,
        synthesize_schema_max_retries=2,
    )

    expected_schema = {
        'type': 'function',
        'function': {
            'name': 'sample_function',
            'description': (
                'This function checks if the integer is positive and\n'
                'if the string is non-empty.'
            ),
            'strict': True,
            'parameters': {
                'type': 'object',
                'properties': {
                    'a': {
                        'type': 'integer',
                        'description': 'The integer value to check.',
                    },
                    'b': {
                        'type': ['string', 'null'],
                        'description': (
                            "The string to verify. Default is 'default'."
                        ),
                    },
                },
                'required': ['a', 'b'],
                'additionalProperties': False,
            },
        },
    }

    assert function_tool.openai_tool_schema == expected_schema
