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
import pytest
from PIL import Image

from camel.types import OpenAIImageDetailType
from camel.utils.token_counting import count_tokens_from_image


@pytest.mark.parametrize(
    "width,height,detail,token_cost",
    [
        (1024, 1024, OpenAIImageDetailType.HIGH, 765),
        (1024, 1024, OpenAIImageDetailType.AUTO, 765),
        (2048, 4096, OpenAIImageDetailType.HIGH, 1105),
        (2048, 4096, OpenAIImageDetailType.LOW, 85),
    ],
)
def test_openai_count_token_from_image(
    width: int, height: int, detail: OpenAIImageDetailType, token_cost: int
):
    image = Image.new("RGB", (width, height), "black")
    assert count_tokens_from_image(image, detail) == token_cost
