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
from typing import Callable, Optional, Union

from pydantic import BaseModel

from camel.utils import get_format

from .prompts import DEFAULT_STRUCTURED_PROMPTS


class BaseStructedModel(ABC):
    """
    A base class for structured models that includes functionality
    for managing the response format.
    """

    def __init__(
        self, target: Optional[BaseModel] = None, prompt: Optional[str] = None
    ):
        """
        Initializes the BaseStructedModel with an optional response format.

        Args:
            target (Optional[BaseModel]): The expected format of the response.
                Defaults to None.
            prompt (Optional[str]): The prompt to be used for the model.
                Defaults to None.
        """
        self.target = target
        self.prompt = prompt or DEFAULT_STRUCTURED_PROMPTS

    @staticmethod
    def get_format(
        input_data: Optional[Union[str, type, Callable]] = None,
    ) -> BaseModel:
        """
        Formats the input data into the expected response format.

        Args:
            input_data (Optional[Union[str, type, Callable]]):
                The input data to be formatted. Defaults to None.

        Returns:
            BaseModel: The formatted response.
        """
        return get_format(input_data)

    @abstractmethod
    def structure(self, text: str) -> Optional[BaseModel]:
        """
        Structures the input text into the expected response format.

        Args:
            text (str): The input text to be structured.

        Returns:
            Optional[BaseModel]: The structured response.
        """
        pass
