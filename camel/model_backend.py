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
from typing import Any, Dict


class ModelBackend(ABC):
    """Base class for different model backends.
       May be OpenAI API, a local LLM, a stub for unit tests, etc."""

    @abstractmethod
    def run(*args, **kwargs) -> Dict[str, Any]:
        """Runs the query to the backend model.

        Raises:
            RuntimeError: if the return value from OpenAI API
            is not a dict that is expected.

        Returns:
            Dict[str, Any]: All backends must return a dict in OpenAI format.
        """
        pass


class OpenAIModel(ModelBackend):
    """OpenAI API in a unified ModelBackend

    Args:
        ModelBackend (_type_): _description_
    """

    def run(*args, **kwargs) -> Dict[str, Any]:

        import openai
        response = openai.ChatCompletion.create(*args, **kwargs)
        if not isinstance(response, Dict):
            raise RuntimeError("Unexpected return from OpenAI API")
        return response


class StubModel(ModelBackend):
    """A dummy model used for unit tests."""

    def run(*args, **kwargs) -> Dict[str, Any]:
        ARBITRARY_STRING = "Lorem Ipsum"

        return dict(
            id="stub_model_id",
            usage=dict(),
            choices=[
                dict(finish_reason="stop",
                     message=dict(content=ARBITRARY_STRING, role="assistant"))
            ],
        )


class ModelFactory:
    """Factory of backend models.

    Raises:
        ValueError: in case the provided string
        descriptor of a model is unknown.
    """

    @staticmethod
    def create(name: str) -> ModelBackend:
        model_map: Dict[str, ModelBackend] = {
            "openai": OpenAIModel,
            "stub": StubModel,
        }
        if name not in model_map:
            raise ValueError("Unknown model")
        model_class = model_map[name]
        return model_class
