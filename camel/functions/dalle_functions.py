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
import base64
import os
import uuid
from io import BytesIO
from typing import List, Literal

from openai import OpenAI
from PIL import Image

from camel.functions import OpenAIFunction


def base64_to_image(base64_string):
    try:
        image_data = base64.b64decode(base64_string)
        image_buffer = BytesIO(image_data)
        image = Image.open(image_buffer)
        return image
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def image_path_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def image_to_base64(image):
    try:
        buffered_image = BytesIO()
        image.save(buffered_image, format="PNG")
        buffered_image.seek(0)
        image_bytes = buffered_image.read()
        base64_str = base64.b64encode(image_bytes).decode('utf-8')
        return base64_str
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def get_dalle_img(
    model: str,
    prompt: str,
    size: Literal['256x256', '512x512', '1024x1024', '1792x1024', '1024x1792'],
    quality: Literal['standard', 'hd'],
    n: int,
    image_path: str,
) -> str:
    """Generate an image using OpenAI's DALL-E model.
    Args:
        model (str): The specific DALL-E model to use for image generation,
            including "dall-e-3" and "dall-e-2". Defaults to "dall-e-3".
        prompt (str): The text prompt based on which the image is generated.
        size (str): The size specification of the image.
            Must be one of "256x256","512x512", or "1024x1024" for
            "dall-e-2". Must be one of "1024x1024",
            "1792x1024", or "1024x1792" for "dall-e-3".
        quality (str): The quality setting for the image generation,
            including "standard" and "hd". Defaults to "standard".
        n (int): The number of images to generate. Must be between 1 and 10.
            For "dall-e-3", only n=1 is supported. Defaults to 1.
    Returns:
    str: The image data as a base64 string.
    """

    dalle_client = OpenAI()
    response = dalle_client.images.generate(
        model=model,
        prompt=prompt,
        size=size,
        quality=quality,
        n=n,
        response_format="b64_json",
    )
    image_b64 = response.data[0].b64_json
    image = base64_to_image(image_b64)

    os.makedirs("img", exist_ok=True)
    image_path = f"img/{uuid.uuid4()!s}.png"
    image.save(image_path)

    return f"{image_path}"


DALLE_FUNCS: List[OpenAIFunction] = [
    OpenAIFunction(func) for func in [get_dalle_img]
]
