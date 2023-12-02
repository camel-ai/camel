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
from typing import Any, Callable, Dict, Optional

from jsonschema.exceptions import SchemaError
from jsonschema.validators import Draft202012Validator as JSONValidator
from openai.types.beta.threads.run import ToolAssistantToolsFunction
from pydantic import ValidationError

from camel.utils.commons import get_openai_tool_schema


class OpenAIFunction:
    r"""An abstraction of a function that OpenAI chat models can call. See
    https://platform.openai.com/docs/api-reference/chat/create.

    By default, the tool schema will be parsed from the func, or you can
    provide a user-defined tool schema to override.

    Args:
        func (Callable): The function to call.The tool schema is parsed from
            the signature and docstring by default.
        openai_tool_schema (Optional[Dict[str, Any]], optional): user-defined
            openai tool schema to override the default result.
            (default: :obj:`None`)
    """

    def __init__(
        self,
        func: Callable,
        openai_tool_schema: Optional[Dict[str, Any]] = None,
    ):
        self.func = func
        self.openai_tool_schema = (openai_tool_schema
                                   or get_openai_tool_schema(func))
        self.properties = self.openai_tool_schema

    @staticmethod
    def validate_openai_tool_schema(openai_tool_schema):
        # Automatically validates whether the openai_tool_schema passed
        # complies with the specifications of the ToolAssistantToolsFunction.
        try:
            ToolAssistantToolsFunction.model_validate(openai_tool_schema)
        except ValidationError as e:
            raise e
        # check the function description
        if not openai_tool_schema["function"]["description"]:
            raise ValueError("miss function description")
        # Validate whether parameters
        # meet the JSON Schema reference specifications.
        # See https://platform.openai.com/docs/guides/gpt/function-calling
        # for examples, and the
        # https://json-schema.org/understanding-json-schema/ for
        # documentation about the format.
        parameters = openai_tool_schema["function"]["parameters"]
        try:
            JSONValidator.check_schema(parameters)
        except SchemaError as e:
            raise e
        # check the parameter description
        properties = parameters["properties"]
        for param_name in properties.keys():
            param_dict = properties[param_name]
            if "description" not in param_dict:
                raise ValueError(
                    f'miss description of parameter "{param_name}"')

    def get_openai_tool_schema(self):
        self.validate_openai_tool_schema(self.openai_tool_schema)
        return self.openai_tool_schema

    def set_openai_tool_schema(self, schema: Dict):
        self.openai_tool_schema = schema

    def get_openai_function_schema(self):
        self.validate_openai_tool_schema(self.openai_tool_schema)
        return self.openai_tool_schema["function"]

    def set_openai_function_schema(self, openai_function_schema):
        self.openai_tool_schema["function"] = openai_function_schema

    def get_function_name(self):
        self.validate_openai_tool_schema(self.openai_tool_schema)
        return self.openai_tool_schema["function"]["name"]

    def set_function_name(self, name):
        self.openai_tool_schema["function"]["name"] = name

    def get_function_description(self):
        self.validate_openai_tool_schema(self.openai_tool_schema)
        return self.openai_tool_schema["function"]["description"]

    def set_function_description(self, description):
        self.openai_tool_schema["function"]["description"] = description

    def get_paramter_description(self, param_name):
        self.validate_openai_tool_schema(self.openai_tool_schema)
        return self.openai_tool_schema["function"]["parameters"]["properties"][
            param_name]["description"]

    def set_paramter_description(self, param_name, description):
        self.openai_tool_schema["function"]["parameters"]["properties"][
            param_name]["description"] = description

    def get_parameter(self, param_name):
        self.validate_openai_tool_schema(self.openai_tool_schema)
        return self.openai_tool_schema["function"]["parameters"]["properties"][
            param_name]

    def set_parameter(self, param_name, value):
        self.openai_tool_schema["function"]["parameters"]["properties"][
            param_name] = value

    @property
    def parameters(self) -> Dict[str, Any]:
        r"""Getter method for the property :obj:`parameters`.

        Returns:
            Dict[str, Any]: the dictionary containing information of
                parameters of this function.
        """
        self.validate_openai_tool_schema(self.openai_tool_schema)
        return self.openai_tool_schema["function"]["parameters"]["properties"]

    @parameters.setter
    def parameters(self, value: Dict[str, Any]):
        r"""Setter method for the property :obj:`parameters`. It will
        firstly check if the input parameters schema is valid. If invalid,
        the method will raise :obj:`jsonschema.exceptions.SchemaError`.

        Args:
            value (Dict[str, Any]): the new dictionary value for the
                function's parameters.
        """
        self.openai_tool_schema["function"]["parameters"]["properties"] = value
