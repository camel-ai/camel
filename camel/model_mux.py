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


class ModelMultiplexor(ABC):

    @abstractmethod
    def run(*args, **kwargs) -> Dict:
        pass


class OpenAIModel(ModelMultiplexor):

    def run(*args, **kwargs) -> Dict[str, Any]:
        import openai
        response = openai.ChatCompletion.create(**kwargs)
        if not isinstance(response, Dict):
            raise RuntimeError("Unexpected return from OpenAI API")
        return response


class StubModel(ModelMultiplexor):

    def run(*args, **kwargs) -> Dict[str, Any]:
        return dict(
            id="qwe",
            usage=dict(),
            choices=[
                dict(finish_reason="stop",
                     message=dict(content="Lorem Ipsum", role="assistant"))
            ],
        )


class ModelFactory:

    @staticmethod
    def create(name: str) -> ModelMultiplexor:
        model_map: Dict[str, ModelMultiplexor] = {
            "openai": OpenAIModel,
            "stub": StubModel,
        }
        if name not in model_map:
            raise ValueError("Unknown model")
        model_class = model_map[name]
        return model_class
