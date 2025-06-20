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
import os
import tempfile

import pytest
from PIL import Image

from camel.tasks import Task, TaskManager


def test_task():
    task = Task(content="a start task", id="0")
    sub_task_1 = Task(content="a sub task 1", id="1")
    sub_task_2 = Task(content="a sub task 2", id="2")
    task.add_subtask(sub_task_1)
    task.add_subtask(sub_task_2)
    task.set_state("DONE")

    print(task.to_string())
    assert task.state == "DONE"

    task.set_state("RUNNING")
    print(task.to_string(state=True))

    print(task.get_result())


def test_task_management():
    """
    Tests hierarchical task creation, subtask management, and topological sorting within the TaskManager.
    
    Builds a tree of tasks with nested subtasks, verifies the string representation of the hierarchy, checks the topological sort order of subtasks, and asserts correct task ordering after adding tasks to the manager.
    """
    root_task = Task(content="a start task", id="0")
    sub_task_1 = Task(content="a sub task 1", id="1")
    sub_task_2 = Task(content="a sub task 2", id="2")
    sub_task_3 = Task(content="a sub task 3", id="3")
    sub_task_2_1 = Task(content="a sub task of task 2", id="2.1")
    sub_task_2_2 = Task(content="a sub task of task 2", id="2.2")
    root_task.add_subtask(sub_task_1)
    root_task.add_subtask(sub_task_2)
    root_task.add_subtask(sub_task_3)
    sub_task_2.add_subtask(sub_task_2_1)
    sub_task_2.add_subtask(sub_task_2_2)

    print("\n===\n" + root_task.to_string() + "\n===\n")

    manager = TaskManager(root_task)
    new_tasks = [
        sub_task_1,
        sub_task_2,
        sub_task_2_1,
        sub_task_2_2,
        sub_task_3,
    ]

    sorted_tasks = manager.topological_sort(new_tasks)
    sorted_tasks_ids = [task.id for task in sorted_tasks]
    print(sorted_tasks_ids)
    assert sorted_tasks_ids == ["1", "2.1", "2.2", "2", "3"]

    manager.add_tasks(new_tasks)
    print([task.id for task in manager.tasks])
    assert [task.id for task in manager.tasks] == [
        "1",
        "2.1",
        "2.2",
        "2",
        "3",
        "0",
    ]


@pytest.fixture
def temp_image():
    # Create temporary image file and return PIL Image object
    """
    Pytest fixture that creates and yields a temporary 10x10 blue PNG image as a PIL Image object.
    
    The temporary image file is deleted after the test using this fixture completes.
    """
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img = Image.new("RGB", (10, 10), color="blue")
        img.save(f, format="PNG")
        f.flush()
        image = Image.open(f.name)
        yield image
    os.remove(f.name)


@pytest.fixture
def temp_video_bytes():
    # Create temporary video file and read as bytes
    """
    Pytest fixture that creates a temporary MP4 file with fake video data and yields its bytes.
    
    The temporary file is deleted after the test completes.
    """
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        f.write(b"fake video data")
        f.flush()
        f.seek(0)
        video_bytes = f.read()
        yield video_bytes
    os.remove(f.name)


def test_image_task_management(temp_image):
    """
    Tests hierarchical task management for image analysis, including subtasks for object detection, text recognition, and description generation, using a temporary image.
    
    Verifies correct construction of the task hierarchy, topological sorting of subtasks, and task addition order in the TaskManager.
    """
    root_task = Task(
        content="Analyze image",
        id="0",
        image_list=[temp_image],
        image_detail="high",
    )
    sub_task_1 = Task(content="Detect objects in image", id="1")
    sub_task_2 = Task(content="Recognize text in image", id="2")
    sub_task_3 = Task(content="Generate image description", id="3")
    sub_task_2_1 = Task(content="Recognize title text", id="2.1")
    sub_task_2_2 = Task(content="Recognize body text", id="2.2")

    root_task.add_subtask(sub_task_1)
    root_task.add_subtask(sub_task_2)
    root_task.add_subtask(sub_task_3)
    sub_task_2.add_subtask(sub_task_2_1)
    sub_task_2.add_subtask(sub_task_2_2)

    print("\n===\n" + root_task.to_string() + "\n===\n")

    manager = TaskManager(root_task)
    new_tasks = [
        sub_task_1,
        sub_task_2,
        sub_task_2_1,
        sub_task_2_2,
        sub_task_3,
    ]

    sorted_tasks = manager.topological_sort(new_tasks)
    sorted_tasks_ids = [task.id for task in sorted_tasks]
    print(sorted_tasks_ids)
    assert sorted_tasks_ids == ["1", "2.1", "2.2", "2", "3"]

    manager.add_tasks(new_tasks)
    print([task.id for task in manager.tasks])
    assert [task.id for task in manager.tasks] == [
        "1",
        "2.1",
        "2.2",
        "2",
        "3",
        "0",
    ]


def test_video_task_management(temp_video_bytes):
    """
    Tests hierarchical task management for video analysis, including subtasks for people detection, speech recognition (with nested dialogue recognition), and summary generation.
    
    Verifies correct construction of the task hierarchy, topological sorting of subtasks, and task addition order in the TaskManager when handling video data.
    """
    root_task = Task(
        content="Analyze video",
        id="0",
        video_bytes=temp_video_bytes,
        video_detail="high",
    )
    sub_task_1 = Task(content="Detect people in video", id="1")
    sub_task_2 = Task(content="Recognize speech in video", id="2")
    sub_task_3 = Task(content="Generate video summary", id="3")
    sub_task_2_1 = Task(content="Recognize opening dialogue", id="2.1")
    sub_task_2_2 = Task(content="Recognize ending dialogue", id="2.2")

    root_task.add_subtask(sub_task_1)
    root_task.add_subtask(sub_task_2)
    root_task.add_subtask(sub_task_3)
    sub_task_2.add_subtask(sub_task_2_1)
    sub_task_2.add_subtask(sub_task_2_2)

    print("\n===\n" + root_task.to_string() + "\n===\n")

    manager = TaskManager(root_task)
    new_tasks = [
        sub_task_1,
        sub_task_2,
        sub_task_2_1,
        sub_task_2_2,
        sub_task_3,
    ]

    sorted_tasks = manager.topological_sort(new_tasks)
    sorted_tasks_ids = [task.id for task in sorted_tasks]
    print(sorted_tasks_ids)
    assert sorted_tasks_ids == ["1", "2.1", "2.2", "2", "3"]

    manager.add_tasks(new_tasks)
    print([task.id for task in manager.tasks])
    assert [task.id for task in manager.tasks] == [
        "1",
        "2.1",
        "2.2",
        "2",
        "3",
        "0",
    ]
