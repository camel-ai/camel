# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
import base64
from io import BytesIO
from typing import Any, Dict, Optional

import pytest
from PIL import Image

from camel.types import ModelType, OpenAIVisionDetailType
from camel.utils import OpenAITokenCounter


@pytest.mark.parametrize(
    "width,height,detail,token_cost",
    [
        (1024, 1024, OpenAIVisionDetailType.HIGH, 765),
        (1024, 1024, OpenAIVisionDetailType.AUTO, 765),
        (2048, 4096, OpenAIVisionDetailType.HIGH, 1105),
        (2048, 4096, OpenAIVisionDetailType.LOW, 85),
    ],
)
def test_openai_count_token_from_image(
    width: int, height: int, detail: OpenAIVisionDetailType, token_cost: int
):
    image = Image.new("RGB", (width, height), "black")
    assert (
        OpenAITokenCounter(ModelType.GPT_4O_MINI)._count_tokens_from_image(
            image, detail
        )
        == token_cost
    )


def _image_message(
    url: str, detail: Optional[str] = None
) -> Dict[str, Any]:
    r"""Build an OpenAI message holding a single image part."""
    image_url: Dict[str, Any] = {"url": url}
    if detail is not None:
        image_url["detail"] = detail
    return {
        "role": "user",
        "content": [{"type": "image_url", "image_url": image_url}],
    }


def _base64_png(width: int, height: int) -> str:
    buffer = BytesIO()
    Image.new("RGB", (width, height), "black").save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(
        buffer.getvalue()
    ).decode("ascii")


def test_openai_count_tokens_base64_image_without_detail():
    r"""`detail` is optional and defaults to "auto" when omitted."""
    counter = OpenAITokenCounter(ModelType.GPT_4O_MINI)
    url = _base64_png(1024, 1024)

    omitted = counter.count_tokens_from_messages([_image_message(url)])
    explicit_auto = counter.count_tokens_from_messages(
        [_image_message(url, OpenAIVisionDetailType.AUTO.value)]
    )
    high = counter.count_tokens_from_messages(
        [_image_message(url, OpenAIVisionDetailType.HIGH.value)]
    )

    assert omitted == explicit_auto
    assert high == explicit_auto


def test_openai_count_tokens_url_image_without_detail():
    r"""A remote image carries no detail key and cannot be fetched."""
    counter = OpenAITokenCounter(ModelType.GPT_4O_MINI)

    omitted = counter.count_tokens_from_messages(
        [_image_message("https://example.com/image.png")]
    )
    explicit_low = counter.count_tokens_from_messages(
        [
            _image_message(
                "https://example.com/image.png",
                OpenAIVisionDetailType.LOW.value,
            )
        ]
    )

    assert omitted == explicit_low
