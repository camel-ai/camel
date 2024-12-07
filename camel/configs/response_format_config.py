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

from typing import Any, Dict, List, Literal, Optional, Type

from pydantic import BaseModel


class ResponseFormat(BaseModel):
    r"""ResponseFormat defines the structure and configuration for formatting
    responses.

    Attributes:
        type (Literal["choice", "json", "regex"]):
            Specifies the type of the response format:
            - "choice": A predefined set of options.
            - "json": A JSON object structure.
            - "regex": A string pattern defined by a regular expression.

        method (Literal["outlines", "builtins"]):
            Specifies the method used to process the response:
            - "outlines": Uses the Outlines library for response generation.
            - "builtins": Relies on camel built-in implementations.

        regex (Optional[str]):
            A regular expression string to validate the response format.
            Required when `type` is "regex".

        json_schema (Optional[Dict[str, Any]]):
            A JSON schema to validate responses if `type` is "json".

        pydantic_object (Optional[Type[BaseModel]]):
            A Pydantic model class for validating responses if `type` is
            "json".

        choices (Optional[List[str]]):
            A list of predefined options if `type` is "choice".
    """

    type: Literal["choice", "json", "regex"]
    method: Literal["outlines", "builtins", "openai"] = "builtins"
    regex: str = ""
    json_schema: Optional[Dict[str, Any]] = None
    pydantic_object: Optional[Type[BaseModel]] = None
    choices: Optional[List[str]] = None
