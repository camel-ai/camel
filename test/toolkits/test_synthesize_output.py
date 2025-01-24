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
import pytest
from pydantic import BaseModel, Field

from camel.models import OpenAIModel
from camel.toolkits import FunctionTool
from camel.types import ModelType


def sample_function(a, b):
    """Adds two numbers together."""
    return a + b


@pytest.mark.model_backend
def test_synthesize_execution_output_with_kwargs():
    function_tool = FunctionTool(
        func=sample_function,
        synthesize_output=True,
        # Not providing synthesize_output_model to use default model
    )

    kwargs = {'a': 2, 'b': 3}
    output = function_tool.synthesize_execution_output(kwargs=kwargs)

    assert output.strip() == '5'


@pytest.mark.model_backend
def test_synthesize_execution_output_without_kwargs():
    function_tool = FunctionTool(
        func=sample_function,
        synthesize_output=True,
        # Not providing synthesize_output_model to use default model
    )

    output = function_tool.synthesize_execution_output()

    # Since no arguments are provided, the assistant may return an error
    # message or synthesized output.
    # We can assert that the output is not empty.
    assert output is not None
    assert len(output.strip()) > 0


class FormattedResponse(BaseModel):
    sum_value: int = Field(description="The sum value.")


@pytest.mark.model_backend
def test_synthesize_execution_output_with_synthesize_output_format():
    # Assuming you have a custom response format

    # Create a response format if applicable (e.g., a Pydantic model)
    synthesize_output_format = FormattedResponse

    function_tool = FunctionTool(
        func=sample_function,
        synthesize_output=True,
        synthesize_output_format=synthesize_output_format,
    )

    kwargs = {'a': 2, 'b': 3}
    output = function_tool.synthesize_execution_output(kwargs=kwargs)

    assert output.strip() == '{"sum_value":5}'


@pytest.mark.model_backend
def test_synthesize_output_with_custom_model():
    # Use a specific model by specifying model_type
    custom_model = OpenAIModel(model_type=ModelType.GPT_4O_MINI)

    function_tool = FunctionTool(
        func=sample_function,
        synthesize_output=True,
        synthesize_output_model=custom_model,
    )

    kwargs = {'a': 10, 'b': 15}
    output = function_tool.synthesize_execution_output(kwargs=kwargs)

    assert output.strip() == '25'
