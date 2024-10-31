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
import pytest

from camel.toolkits import FunctionTool
from camel.agents.chat_agent import ChatAgent
from camel.models import OpenAIModel
from camel.messages import BaseMessage
from camel.types import ModelType

def sample_function(a, b):
    """Adds two numbers together."""
    return a + b

@pytest.mark.model_backend
def test_synthesize_output_with_args():
    function_tool = FunctionTool(
        func=sample_function,
        synthesis_mode=True,
        # Not providing synthesis_assistant_model to use default model
    )

    args = {'a': 2, 'b': 3}
    output = function_tool.synthesize_output(args=args)

    assert output.strip() == '5'

@pytest.mark.model_backend
def test_synthesize_output_without_args():
    function_tool = FunctionTool(
        func=sample_function,
        synthesis_mode=True,
        # Not providing synthesis_assistant_model to use default model
    )

    output = function_tool.synthesize_output()

    # Since no arguments are provided, the assistant may return an error
    # message or synthesized output.
    # We can assert that the output is not empty.
    assert output is not None
    assert len(output.strip()) > 0

@pytest.mark.model_backend
def test_synthesize_output_with_response_format():
    # Assuming you have a custom response format
    from camel.models import OpenAIModel

    # Create a response format if applicable (e.g., a Pydantic model)
    response_format = None

    function_tool = FunctionTool(
        func=sample_function,
        synthesis_mode=True,
        response_format=response_format,
    )

    args = {'a': 2, 'b': 3}
    output = function_tool.synthesize_output(args=args)

    assert output.strip() == '5'

@pytest.mark.model_backend
def test_synthesis_output_with_custom_model():
    # Use a specific model by specifying model_type
    custom_model = OpenAIModel(model_type=ModelType.GPT_4O_MINI)

    function_tool = FunctionTool(
        func=sample_function,
        synthesis_mode=True,
        synthesis_assistant_model=custom_model,
    )

    args = {'a': 10, 'b': 15}
    output = function_tool.synthesize_output(args=args)

    assert output.strip() == '25'
