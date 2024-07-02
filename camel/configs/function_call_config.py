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
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from .openai_config import (
    ChatGPTConfig,
    ChatGPTVisionConfig,
)

if TYPE_CHECKING:
    from camel.functions import OpenAIFunction


@dataclass(frozen=True)
class FunctionCallingConfig(ChatGPTConfig):
    r"""Defines the parameters for generating chat completions using the
    OpenAI API with functions included.
    Args:
        functions (List[Dict[str, Any]]): A list of functions the model may
            generate JSON inputs for.
        function_call (Union[Dict[str, str], str], optional): Controls how the
            model responds to function calls. :obj:`"none"` means the model
            does not call a function, and responds to the end-user.
            :obj:`"auto"` means the model can pick between an end-user or
            calling a function. Specifying a particular function via
            :obj:`{"name": "my_function"}` forces the model to call that
            function. (default: :obj:`"auto"`)
    """

    functions: List[Dict[str, Any]] = field(default_factory=list)
    function_call: Union[Dict[str, str], str] = "auto"

    @classmethod
    def from_openai_function_list(
        cls,
        function_list: List[OpenAIFunction],
        function_call: Union[Dict[str, str], str] = "auto",
        kwargs: Optional[Dict[str, Any]] = None,
    ):
        r"""Class method for creating an instance given the function-related
        arguments.
        Args:
            function_list (List[OpenAIFunction]): The list of function objects
                to be loaded into this configuration and passed to the model.
            function_call (Union[Dict[str, str], str], optional): Controls how
                the model responds to function calls, as specified in the
                creator's documentation.
            kwargs (Optional[Dict[str, Any]]): The extra modifications to be
                made on the original settings defined in :obj:`ChatGPTConfig`.
        Return:
            FunctionCallingConfig: A new instance which loads the given
                function list into a list of dictionaries and the input
                :obj:`function_call` argument.
        """
        return cls(
            functions=[
                func.get_openai_function_schema() for func in function_list
            ],
            function_call=function_call,
            **(kwargs or {}),
        )


@dataclass(frozen=True)
class FunctionCallingVisionConfig(ChatGPTVisionConfig):
    r"""Defines the parameters for generating chat completions using the
    OpenAI API with functions included.
    Args:
        functions (List[Dict[str, Any]]): A list of functions the model may
            generate JSON inputs for.
        function_call (Union[Dict[str, str], str], optional): Controls how the
            model responds to function calls. :obj:`"none"` means the model
            does not call a function, and responds to the end-user.
            :obj:`"auto"` means the model can pick between an end-user or
            calling a function. Specifying a particular function via
            :obj:`{"name": "my_function"}` forces the model to call that
            function. (default: :obj:`"auto"`)
    """

    functions: List[Dict[str, Any]] = field(default_factory=list)
    function_call: Union[Dict[str, str], str] = "auto"

    @classmethod
    def from_openai_function_list(
        cls,
        function_list: List[OpenAIFunction],
        function_call: Union[Dict[str, str], str] = "auto",
        kwargs: Optional[Dict[str, Any]] = None,
    ):
        r"""Class method for creating an instance given the function-related
        arguments.
        Args:
            function_list (List[OpenAIFunction]): The list of function objects
                to be loaded into this configuration and passed to the model.
            function_call (Union[Dict[str, str], str], optional): Controls how
                the model responds to function calls, as specified in the
                creator's documentation.
            kwargs (Optional[Dict[str, Any]]): The extra modifications to be
                made on the original settings defined in
                :obj:`ChatGPTVisionConfig`.
        Return:
            FunctionCallingConfig: A new instance which loads the given
                function list into a list of dictionaries and the input
                :obj:`function_call` argument.
        """
        return cls(
            functions=[
                func.get_openai_function_schema() for func in function_list
            ],
            function_call=function_call,
            **(kwargs or {}),
        )
