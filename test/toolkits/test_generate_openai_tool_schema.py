from unittest.mock import MagicMock, patch
import pytest
from camel.models.base_model import BaseModelBackend
from camel.messages import BaseMessage
from camel.agents import ChatAgent
from camel.toolkits import FunctionTool, generate_docstring


def sample_function(a: int, b: str = "default") -> bool:
    """
    This function checks if the integer is positive and if the string is non-empty.

    Args:
        a (int): The integer value to check.
        b (str): The string to verify. Default is "default".

    Returns:
        bool: True if both conditions are met, otherwise False.
    """
    return a > 0 and len(b) > 0

@patch.object(ChatAgent, 'step')
@patch('camel.models.ModelFactory.create')
def test_generate_openai_tool_schema(mock_create_model, mock_chat_agent_step):
    # Mock model instance
    mock_model_instance = MagicMock()
    mock_model_instance.model_config_dict = {}
    mock_create_model.return_value = mock_model_instance

    # Mock ChatAgent's step method return value
    mock_message = MagicMock()
    mock_message.content = (
        "This function checks if the integer is positive and if the string is non-empty.\n"
        "Args:\n    a (int): The integer value to check.\n    b (str): The string to verify. Default is 'default'.\n"
        "Returns:\n    bool: True if both conditions are met, otherwise False."
    )
    mock_response = MagicMock()
    mock_response.msgs = [mock_message]
    mock_response.msg = mock_message
    mock_response.terminated = True
    mock_chat_agent_step.return_value = mock_response

    # Create FunctionTool instance
    function_tool = FunctionTool(func=sample_function)

    # Generate schema
    try:
        schema = function_tool.generate_openai_tool_schema(schema_assistant=mock_model_instance)
    except Exception as e:
        pytest.fail(f"generate_openai_tool_schema() raised an exception unexpectedly: {e}")

    if schema is None:
        pytest.fail("generate_openai_tool_schema() returned None unexpectedly.")

    # Adjusted expected schema with 'default' key in 'b' parameter
    expected_schema = {
        'type': 'function',
        'function': {
            'name': 'sample_function',
            'description': 'This function checks if the integer is positive and if the string is non-empty.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'a': {
                        'type': 'integer',
                        'description': 'The integer value to check.'
                    },
                    'b': {
                        'type': 'string',
                        'description': "The string to verify. Default is 'default'.",
                        'default': 'default'  # Include this line
                    }
                },
                'required': ['a']
            }
        }
    }

    assert schema == expected_schema


@pytest.fixture
def mock_model():
    # Create a mock model to simulate BaseModelBackend behavior
    mock_model = MagicMock(spec=BaseModelBackend)
    mock_model.model_type = MagicMock()
    mock_model.model_type.value_for_tiktoken = "mock_value_for_tiktoken"
    mock_model.model_config_dict = {}
    mock_model.value_for_tiktoken = MagicMock(return_value=1000)
    return mock_model

@patch.object(ChatAgent, 'step')
def test_generate_docstring(mock_chat_agent_step, mock_model):
    code = """
    def sample_function(a: int, b: str = "default") -> bool:
        return a > 0 and len(b) > 0
    """

    # Ensure mock_model has required attributes
    mock_model.model_type = MagicMock()
    mock_model.model_type.value_for_tiktoken = "mock_value_for_tiktoken"
    mock_model.model_config_dict = {}
    mock_model.value_for_tiktoken = MagicMock(return_value=1000)

    # Mock ChatAgent's step method return value
    mock_message = MagicMock()
    mock_message.content = (
        "This function checks if the integer is positive and if the string is non-empty.\n"
        "Args:\n    a (int): The integer value to check.\n    b (str): The string to verify. Default is 'default'.\n"
        "Returns:\n    bool: True if both conditions are met, otherwise False."
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
        pytest.fail(f"generate_docstring() raised AttributeError unexpectedly: {e}")
    except RuntimeError as e:
        pytest.fail(f"generate_docstring() raised RuntimeError unexpectedly: {e}")

    expected_docstring = (
        "This function checks if the integer is positive and if the string is non-empty.\n"
        "Args:\n    a (int): The integer value to check.\n    b (str): The string to verify. Default is 'default'.\n"
        "Returns:\n    bool: True if both conditions are met, otherwise False."
    )

    assert docstring == expected_docstring