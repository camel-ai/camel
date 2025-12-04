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

from camel.tasks import Task


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


def create_image_task(image_path: str, task_id: str = "0") -> Task:
    """Create a task with image support."""
    image = load_image(image_path)
    return Task(
        content=(
            "Analyze the image and "
            "provide a detailed description of what you see."
        ),
        image_list=[image],
        id=task_id,
    )


def create_video_task(video_path: str, task_id: str = "1") -> Task:
    """Create a task with video support."""
    video_bytes = load_video(video_path)
    return Task(
        content=("Analyze the video and " "provide a summary of the content."),
        video_bytes=video_bytes,
        id=task_id,
    )


def demonstrate_multimodal_tasks():
    """Demonstrate Task with multimodal support after refactoring."""

    # Example paths - adjust these to match your actual file locations
    img_path = "./examples/tasks/task_image.png"
    video_path = "./examples/tasks/task_video.mov"

    tasks = []

    # Try to create image task
    try:
        image_task = create_image_task(img_path, task_id="0")
        tasks.append(image_task)
        print("✓ Image task created successfully")
        print(f"  - Content: {image_task.content}")
        print(f"  - Image count: {len(image_task.image_list)}")
        print(f"  - Image detail: {image_task.image_detail}")
    except FileNotFoundError as e:
        print(f"✗ Skipping image task: {e}")

    # Try to create video task
    try:
        video_task = create_video_task(video_path, task_id="1")
        tasks.append(video_task)
        print("✓ Video task created successfully")
        print(f"  - Content: {video_task.content}")
        print(f"  - Video size: {len(video_task.video_bytes)} bytes")
        print(f"  - Video detail: {video_task.video_detail}")
    except FileNotFoundError as e:
        print(f"✗ Skipping video task: {e}")

    if not tasks:
        print("No valid tasks found. Please ensure example files exist.")
        print(
            "You can create your own image/video files and update the paths."
        )
        return

    print(f"\n=== Created {len(tasks)} multimodal tasks ===")

    # Demonstrate task hierarchy with multimodal content
    for i, task in enumerate(tasks):
        print(f"\n--- Task {i+1} ---")
        print(task.to_string())

        # Create some example subtasks
        if task.image_list:
            # Image analysis subtasks
            sub_task_1 = Task(
                content="Identify all objects visible in the image",
                id=f"{task.id}.1",
            )
            sub_task_2 = Task(
                content="Describe the overall scene and context",
                id=f"{task.id}.2",
            )
            sub_task_3 = Task(
                content="Analyze colors, lighting, and composition",
                id=f"{task.id}.3",
            )
        else:
            # Video analysis subtasks
            sub_task_1 = Task(
                content="Identify key events and actions in the video",
                id=f"{task.id}.1",
            )
            sub_task_2 = Task(
                content="Describe the audio content and dialogue",
                id=f"{task.id}.2",
            )
            sub_task_3 = Task(
                content="Summarize the overall narrative or purpose",
                id=f"{task.id}.3",
            )

        task.add_subtask(sub_task_1)
        task.add_subtask(sub_task_2)
        task.add_subtask(sub_task_3)

        print(f"\nTask {task.id} now has {len(task.subtasks)} subtasks:")
        print(task.to_string())


if __name__ == "__main__":
    demonstrate_multimodal_tasks()

    print("\n" + "=" * 80)
    print("NOTE: This example demonstrates Task with multimodal support.")
    print("For advanced features like task decomposition, composition,")
    print("and management, please use the Workforce system.")
    print("=" * 80)
