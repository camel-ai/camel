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
from typing import Any, Dict, List

from overrides import override

from camel.models import BaseModelBackend
from camel.typing import ModelType


class StubModel(BaseModelBackend):
    r"""A dummy model used for unit tests."""
    model_type = ModelType.STUB

    def __init__(self, model_type: ModelType,
                 model_config_dict: Dict[str, Any]) -> None:
        r"""All arguments are unused for the dummy model."""
        pass

    @override
    def run(self, messages: List[Dict]) -> Dict[str, Any]:
        r"""Run fake inference by returning a fixed string.
        All arguments are unused for the dummy model.

        Returns:
            Dict[str, Any]: Response in the OpenAI API format.
        """
        ARBITRARY_STRING = "Lorem Ipsum"

        return dict(
            id="stub_model_id",
            usage=dict(),
            choices=[
                dict(finish_reason="stop",
                     message=dict(content=ARBITRARY_STRING, role="assistant"))
            ],
        )
