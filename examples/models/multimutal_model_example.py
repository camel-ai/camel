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
from io import BytesIO

import requests
from PIL import Image

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.models.interlm_xcomposer_model import OperationMode
from camel.types import ModelPlatformType


def load_image_from_url(url: str) -> Image.Image:
    r"""Load an image from a given URL.

    Args:
        url (str): The url resource for image.

    Returns:
        Image: The `Image` of the image.
    """
    response = requests.get(url)
    if response.status_code != 200:
        raise ValueError(f"Failed to load image from URL: {url}")
    image = Image.open(BytesIO(response.content))
    return image


def load_video_from_url(url: str) -> bytes:
    r"""Load video data from a given URL.

    Args:
        url (str): The url resource for video.

    Returns:
        bytes: The byte format of the video.
    """
    response = requests.get(url)
    if response.status_code != 200:
        raise ValueError(f"Failed to load video from URL: {url}")
    return response.content


# Get the resources from the urls.
video_url = 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4'
video_bytes = load_video_from_url(video_url)
image_url = 'https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg'
image = load_image_from_url(image_url)
images = [image, image]


ollama_model = ModelFactory.create(
    model_platform=ModelPlatformType.INTERNLM,
    model_type="internlm-xcomposer2d5-7b",
    model_config_dict={
        "model_path": "internlm/internlm-xcomposer2d5-7b",
        # InterLM XComposer provides different operation modes.
        "operation_mode": OperationMode.CHAT,
        "model_kwargs": {  # use `AutoModel` config in `transformers` library
            "cache_dir": None,
        },
    },
)


assistant_sys_msg = BaseMessage.make_assistant_message(
    role_name="Assistant",
    content="You are a helpful assistant.",
)


agent = ChatAgent(assistant_sys_msg, model=ollama_model, token_limit=4096)


user_msg = BaseMessage.make_user_message(
    role_name="User",
    content="What did you see in the image?",
    video_bytes=video_bytes,
    image_list=images,
)
assistant_response = agent.step(user_msg)
print(assistant_response.msg.content)

"""
===============================================================================
Hi there! *waves* Hi to the amazing team at CAMEL AI - Autonomous and 
Communicative Agents Laboratory! It's great to connect with you all. I'm 
excited to learn more about your work in developing autonomous and 
communicative agents, exploring the intersection of artificial intelligence, 
robotics, and human-computer interaction. Keep pushing the boundaries of 
what's possible!
===============================================================================
"""
