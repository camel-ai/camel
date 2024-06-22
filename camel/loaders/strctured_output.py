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

import pydantic
from pydantic import BaseModel, Field


class JokeResponse(BaseModel):
    joke: str = Field(description="a joke")
    funny_level: str = Field(description="Funny level, from 1 to 10")


class StructuredOutput:
    r"""A class to 
    """

    def __init__(self, parse_type):
        r"""
        """
        self.parse_type = parse_type

    # NOTE :from CAMEL's current design, this function can be moved to `ChatAgent side`
    def function_call_json_parser(self, query, pydantic_params: BaseModel):
        from openai import OpenAI

        client = OpenAI()
        json_schema = self.parse_pydantic_as_json(pydantic_params)

        response = client.chat.completions.create(
            model="gpt-3.5-turbo", response_format={"type": "json_object"},
            messages=[{
                "role":
                "system",
                "content":
                "You are a helpful assistant designed to output JSON."
            }, {
                "role": "user",
                "content": query
            }], tools=[json_schema],
            tool_choice={'name': 'return_json_format_response'})

        return response.choices[0].message.function_call.arguments

    def parse_pydantic_as_json(self, pydantic_params: BaseModel):
        source_dict = {
            "name": "return_json_format_response",
            "description": "Return the respnse of json format",
            "parameters": {
                "type": "object",
                "properties": {},
            },
            "required": [],
        }

        pydantic_params_schema = self.get_pydantic_object_schema(
            pydantic_params)
        source_dict["parameters"]["properties"] = \
        pydantic_params_schema["properties"]
        source_dict["required"] = \
        pydantic_params_schema["required"]

        return source_dict

    # copy langchain
    def get_pydantic_object_schema(self, pydantic_params: BaseModel):
        PYDANTIC_MAJOR_VERSION = self.get_pydantic_major_version()
        if PYDANTIC_MAJOR_VERSION == 2:
            if issubclass(pydantic_params, pydantic.BaseModel):
                return pydantic_params.model_json_schema()
            elif issubclass(pydantic_params, pydantic.v1.BaseModel):
                return pydantic_params.schema()
        return pydantic_params.schema()

    # copy langchain
    def get_pydantic_major_version(self) -> int:
        """Get the major version of Pydantic."""
        try:
            import pydantic

            return int(pydantic.__version__.split(".")[0])
        except ImportError:
            return 0
