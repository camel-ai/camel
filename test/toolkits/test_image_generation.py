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
import pytest
from PIL import Image

from camel.toolkits import ImageGenToolkit


@pytest.fixture
def image_toolkit():
    return ImageGenToolkit()


def test_base64_to_image_valid(image_toolkit):
    valid_base64_string = "iVBORw0KGgoAAAANSUhEUgAAAAUA\
                            AAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO\
                            9TXL0Y4OHwAAAABJRU5ErkJggg=="
    if valid_base64_string.startswith('data:image/png;base64,'):
        valid_base64_string = valid_base64_string[22:]

    image = image_toolkit.base64_to_image(valid_base64_string)

    # test base64 converts to image
    assert isinstance(
        image, Image.Image
    ), "The function should return a PIL Image object"


def test_base64_to_image_invalid(image_toolkit):
    invalid_base64_string = "invalid_base64_string"

    image = image_toolkit.base64_to_image(invalid_base64_string)

    # check response is None
    assert (
        image is None
    ), "The function should return None for an invalid base64 string"


def test_toolkit_initialization_and_tools(image_toolkit):
    # test that toolkit initializes properly
    assert image_toolkit is not None

    # test that only generate_image tool is available
    tools = image_toolkit.get_tools()
    assert len(tools) == 1, "Should only have one tool available"
    assert (
        tools[0].func.__name__ == "generate_image"
    ), "Tool should be generate_image"
