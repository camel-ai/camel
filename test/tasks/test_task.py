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

from camel.tasks import Task, TaskState


def test_task():
    """Test basic Task functionality."""
    task = Task(content="a start task", id="0")
    sub_task_1 = Task(content="a sub task 1", id="1")
    sub_task_2 = Task(content="a sub task 2", id="2")
    task.add_subtask(sub_task_1)
    task.add_subtask(sub_task_2)
    task.set_state(TaskState.DONE)

    print(task.to_string())
    assert task.state == TaskState.DONE

    task.set_state(TaskState.RUNNING)
    print(task.to_string(state=True))

    print(task.get_result())


def test_task_hierarchy():
    """
    Test Task hierarchy management:
    Task 0: a start task
        Task 1: a sub task 1
        Task 2: a sub task 2
            Task 2.1: a sub task of task 2
            Task 2.2: a sub task of task 2
        Task 3: a sub task 3
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

    # Test task hierarchy structure
    assert len(root_task.subtasks) == 3
    assert len(sub_task_2.subtasks) == 2
    assert sub_task_2_1.parent == sub_task_2
    assert sub_task_2_2.parent == sub_task_2
    assert sub_task_1.parent == root_task

    # Test task depth
    assert root_task.get_depth() == 1
    assert sub_task_1.get_depth() == 2
    assert sub_task_2_1.get_depth() == 3


def test_task_state_management():
    """Test Task state management and propagation."""
    root_task = Task(content="root task", id="0")
    sub_task = Task(content="sub task", id="1")
    root_task.add_subtask(sub_task)

    # Test state propagation to parent
    sub_task.set_state(TaskState.RUNNING)
    assert root_task.state == TaskState.RUNNING

    # Test state propagation to children
    root_task.set_state(TaskState.DONE)
    assert sub_task.state == TaskState.DONE


def test_task_operations():
    """Test basic Task operations like add, remove, and result management."""
    task = Task(content="test task", id="0")

    # Test result management
    assert task.result == ""
    task.update_result("test result")
    assert task.result == "test result"
    assert task.state == TaskState.DONE

    # Test subtask operations
    sub_task = Task(content="sub task", id="1")
    task.add_subtask(sub_task)
    assert len(task.subtasks) == 1
    assert sub_task.parent == task

    task.remove_subtask("1")
    assert len(task.subtasks) == 0


@pytest.fixture
def temp_image():
    # Create temporary image file and return PIL Image object
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img = Image.new("RGB", (10, 10), color="blue")
        img.save(f, format="PNG")
        f.flush()
        # Load image into memory to avoid file dependency
        with Image.open(f.name) as loaded_img:
            image = loaded_img.copy()
        yield image
    os.remove(f.name)


@pytest.fixture
def temp_video_bytes():
    # Create temporary video file and read as bytes
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        video_data = b"fake video data"
        f.write(video_data)
        f.flush()
        yield video_data
    os.remove(f.name)


def test_image_task_management(temp_image):
    """
    Test Task with image support:
    Task 0: Analyze image
        Task 1: Detect objects in image
        Task 2: Recognize text in image
            Task 2.1: Recognize title text
            Task 2.2: Recognize body text
        Task 3: Generate image description
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

    # Test image-related attributes
    assert root_task.image_list == [temp_image]
    assert root_task.image_detail == "high"
    assert len(root_task.subtasks) == 3
    assert len(sub_task_2.subtasks) == 2


def test_video_task_management(temp_video_bytes):
    """
    Test Task with video support:
    Task 0: Analyze video
        Task 1: Detect people in video
        Task 2: Recognize speech in video
            Task 2.1: Recognize opening dialogue
            Task 2.2: Recognize ending dialogue
        Task 3: Generate video summary
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

    # Test video-related attributes
    assert root_task.video_bytes == temp_video_bytes
    assert root_task.video_detail == "high"
    assert len(root_task.subtasks) == 3
    assert len(sub_task_2.subtasks) == 2


def test_task_from_message():
    """Test creating Task from BaseMessage."""
    from camel.messages import BaseMessage

    message = BaseMessage.make_user_message(
        role_name="user", content="test message content"
    )
    task = Task.from_message(message)

    assert task.content == "test message content"
    assert task.id == "0"
