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
from typing import Any, Callable, Dict

from jsonschema.exceptions import SchemaError
from jsonschema.validators import Draft202012Validator as JSONValidator

from camel.utils.commons import get_openai_tool_schema


class OpenAIFunction:
    r"""An abstraction of a function that OpenAI chat models can call. See
    https://platform.openai.com/docs/api-reference/chat/create
    By default, the tool schema will be parsed from the func,
    or you can provide a user-defined tool schema to override.
    Args:
        func (Callable): The function to call.The tool schema
            is parsed from the signature and docstring by default.
        openai_tool_schema: user-defined openai tool schema
            to override the default result. The format can be referd to
            https://platform.openai.com/docs/api-reference/chat/create

    """

    def __init__(self, func: Callable, openai_tool_schema=None):
        self.func = func
        self.openai_tool_schema: Dict[str,
                                      Any] = (openai_tool_schema
                                              or get_openai_tool_schema(func))
        self.properties = self.openai_tool_schema

    @staticmethod
    def validate_openai_tool_schema(openai_tool_schema):
        r'''
            {
            "type": "function",
            "function": {
                "name": "function_name",
                "description": "xxx",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "param1": {
                            "type": "string",
                            "description": "xxx",
                        },
                        "param2": {
                            "type": "string",
                            "description": "xxx",
                        },
                    },
                    "required": ["param1", "param1"],
                },
            }
        }
        '''
        # 1. check the basic format
        # 1.1 top-level: "type","function",
        # the value of "type" should be "function"
        for key in ["type", "function"]:
            if key not in openai_tool_schema.keys():
                raise Exception(f"\"{key}\" is not defined")
        if openai_tool_schema["type"] != "function":
            raise Exception("You should define "
                            "\"type\"==\"function\" in top level")
        # 1.2 second-level: "name","description","parameters",
        # the value of "description" shouldn't be None
        for key in ["name", "description", "parameters"]:
            if key not in openai_tool_schema["function"].keys():
                raise Exception(f"\"{key}\" is not defined")
        if not openai_tool_schema["function"]["description"]:
            raise Exception("miss function description")
        # 1.3 third-level: "type","properties","required",
        # the value of "type" should be "object"
        for key in ["type", "properties", "required"]:
            if key not in openai_tool_schema["function"]["parameters"].keys():
                raise Exception(f"\"{key}\" is not defined")
        if openai_tool_schema["function"]["parameters"]["type"] != "object":
            raise Exception("You should "
                            "define \"type\"==\"object\" in \"parameters\"")

        # 2. validate the json schema of
        # openai_tool_schema["function"]["parameters"]
        try:
            JSONValidator.check_schema(
                openai_tool_schema["function"]["parameters"])
        except SchemaError as e:
            raise e

        # 3. check the parameter description
        for param_name in (openai_tool_schema["function"]["parameters"]
                           ["properties"].keys()):
            param_dict = openai_tool_schema["function"]["parameters"][
                "properties"][param_name]
            if "description" not in param_dict:
                raise Exception(f"miss description "
                                f"of parameter \"{param_name}\"")

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
