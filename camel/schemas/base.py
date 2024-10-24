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
from abc import ABC, abstractmethod
from typing import Callable, Optional, Type, Union

from pydantic import BaseModel

from camel.utils import get_format


class BaseConverter(ABC):
    r"""A base class for schema outputs that includes functionality
    for managing the response format.

    Args:
        output_schema (Optional[Type[BaseModel]], optional): The expected
            format of the response. (default: :obj:`None`)
    """

    def __init__(self, output_schema: Optional[Type[BaseModel]] = None):
        self.output_schema = output_schema

    @abstractmethod
    def convert(
        self, text: str, output_schema: Optional[Type[BaseModel]] = None
    ) -> BaseModel:
        """
        Structures the input text into the expected response format.

        Args:
            text (str): The input text to be structured.
            output_schema (Optional[Type[BaseModel]], optional):
                The expected format of the response. Defaults to None.

        Returns:
            Optional[BaseModel]: The structured response.
        """
        pass
