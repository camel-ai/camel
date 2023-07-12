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
from typing import Callable, Dict, Optional

from jsonschema.validators import Draft202012Validator

from camel.utils import parse_doc


class OpenAIFunction:
    r"""An abstraction of a function that OpenAI chat models can call. See
    https://platform.openai.com/docs/guides/gpt/function-calling. If
    :obj:`description` and :obj:`parameters` are both :obj:`None`, try to use
    document parser to generate them.

    Args:
        func (Callable): The function to call.
        name (str, optional): The name of the function to be called. Must be
            a-z, A-Z, 0-9, or contain underscores and dashes, with a maximum
            length of 64. If :obj:`None`, use the name of :obj:`func`.
        description (Optional[str], optional): The description of what the
            function does. (default: :obj:`None`)
        parameters (Optional[Dict], optional): The parameters the functions
            accepts, described as a JSON Schema object. See the `guide <https:
            //platform.openai.com/docs/guides/gpt/function-calling>`_ for
            examples, and the `JSON Schema reference <https://json-schema.org/
            understanding-json-schema/>`_ for documentation about the format.
    """

    def __init__(self, func: Callable, name: Optional[str] = None,
                 description: Optional[str] = None,
                 parameters: Optional[Dict] = None):
        self.func = func
        self.name = name or func.__name__
        self.description = description
        self.parameters = parameters
        if self.description is None and self.parameters is None:
            info = parse_doc(self.func)
            self.description = info["description"]
            self.parameters = info["parameters"]

    @property
    def parameters(self):
        return self._parameters

    @parameters.setter
    def parameters(self, value):
        # Check if the parameters schema is valid.
        # Raise jsonschema.exceptions.SchemaError if invalid.
        if value is not None:
            Draft202012Validator.check_schema(value)
        self._parameters = value

    def as_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }
