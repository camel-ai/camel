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

import io
import os

from PIL import Image

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.tasks import (
    Task,
    TaskManager,
)
from camel.types import (
    ModelPlatformType,
    ModelType,
)

model = ModelFactory.create(
    model_platform=ModelPlatformType.QWEN,
    model_type=ModelType.QWEN_VL_MAX,
    model_config_dict={"temperature": 0.0},
)


def load_image(image_path: str) -> Image.Image:
    """
    Load an image and ensure it has a valid format like PNG or JPEG.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")

    with Image.open(image_path) as img:
        img_format = img.format or "PNG"

        buffer = io.BytesIO()
        img.save(buffer, format=img_format)
        buffer.seek(0)
        return Image.open(buffer)


def load_video(video_path: str) -> bytes:
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
    with open(video_path, "rb") as f:
        return f.read()


# set up agent
assistant_sys_msg = "You are a personal math tutor and programmer."
agent = ChatAgent(assistant_sys_msg, model=model)
agent.reset()


def create_image_task(image_path: str, task_id: str = "0") -> Task:
    image = load_image(image_path)
    return Task(
        content="The task is in the image.", image_list=[image], id=task_id
    )


def create_video_task(video_path: str, task_id: str = "1") -> Task:
    video_bytes = load_video(video_path)
    return Task(
        content="The task is in the video.",
        video_bytes=video_bytes,
        id=task_id,
    )


# Example usage
img_path = "./examples/tasks/task_image.png"
video_path = "./examples/tasks/task_video.mov"

tasks = []
try:
    image_task = create_image_task(img_path, task_id="0")
    tasks.append(image_task)
except FileNotFoundError as e:
    print(f"Skipping image task: {e}")

try:
    video_task = create_video_task(video_path, task_id="1")
    tasks.append(video_task)
except FileNotFoundError as e:
    print(f"Skipping video task: {e}")

if not tasks:
    print("No valid tasks found. Please ensure example files exist.")
    exit(1)

for task in tasks:
    task_manager = TaskManager(task)

    evolved_task = task_manager.evolve(task, agent=agent)
    if evolved_task is not None:
        print(evolved_task.to_string())
    else:
        print("Evolved task is None.")

    new_tasks = task.decompose(agent=agent)
    for t in new_tasks:
        print(t.to_string())

# ruff: noqa: E501
"""
===============================================================================
Task 0: Weng earns $12 an hour for babysitting. Yesterday, she just did 51 
minutes of babysitting. How much did she earn?

Task 0.0: Weng earns $12 an hour for babysitting. However, her hourly rate 
increases by $2 for every additional hour worked beyond the first hour. 
Yesterday, she babysat for a total of 3 hours and 45 minutes. How much did she 
earn in total for her babysitting services?

Task 0.0: Convert 51 minutes to hours.

Task 0.1: Calculate the proportion of 51 minutes to an hour.

Task 0.2: Multiply the proportion by Weng's hourly rate to find out how much 
she earned for 51 minutes of babysitting.
===============================================================================
"""
