# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
import os
import tempfile

import pytest
from PIL import Image

from camel.tasks import Task, TaskGroup, TaskManager
from camel.tasks.task import parse_response_grouped


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


def test_task_group_basic_add_remove():
    group = TaskGroup(content="Group summary", id="g1")
    task1 = Task(content="Task 1", id="t1")
    task2 = Task(content="Task 2", id="t2")

    # Add tasks
    group.add_task(task1)
    group.add_task(task2)

    assert task1 in group.get_tasks()
    assert task2 in group.get_tasks()
    assert task1.group is group
    assert task2.group is group

    # Adding the same task again should be a no-op (no duplicates)
    group.add_task(task1)
    assert group.get_tasks().count(task1) == 1

    # Removing a task should also clear its group reference
    group.remove_task(task1)
    assert task1 not in group.get_tasks()
    assert task1.group is None

    # Removing a task that is not in the group should not raise
    group.remove_task(task1)


def test_task_group_set_id():
    group = TaskGroup(content="Group summary")
    original_id = group.id

    group.set_id("custom-group-id")

    assert group.id == "custom-group-id"
    assert group.id != original_id


def test_task_set_group_links_with_task_group():
    group = TaskGroup(content="Group summary", id="g1")
    task = Task(content="Linked task", id="t1")

    # Directly setting the group on task should add it into the group's list
    task.set_group(group)

    assert task.group is group
    assert task in group.get_tasks()


def test_parse_response_grouped_creates_task_groups():
    response = """
    <tasks>
        <task_group>
            <summary>Group 1 summary</summary>
            <task>First task in group 1</task>
            <task>Second task in group 1</task>
        </task_group>
        <task_group>
            <summary>Group 2 summary</summary>
            <task>Only task in group 2</task>
        </task_group>
    </tasks>
    """

    tasks = parse_response_grouped(response, task_id="0")

    # We should have three tasks across two groups
    assert len(tasks) == 3

    t1, t2, t3 = tasks

    # IDs should be hierarchical: 0.<group_idx>.<task_idx>
    assert t1.id == "0.1.1"
    assert t2.id == "0.1.2"
    assert t3.id == "0.2.1"

    # Group relationships
    assert isinstance(t1.group, TaskGroup)
    assert isinstance(t2.group, TaskGroup)
    assert isinstance(t3.group, TaskGroup)

    # First two tasks share the same group; third is in a different group
    assert t1.group is t2.group
    assert t1.group is not t3.group

    # Group metadata
    group1 = t1.group
    group2 = t3.group
    assert group1.id == "0.1"
    assert group2.id == "0.2"
    assert group1.content == "Group 1 summary"
    assert group2.content == "Group 2 summary"

    # Group task lists should be consistent
    assert t1 in group1.get_tasks()
    assert t2 in group1.get_tasks()
    assert t3 in group2.get_tasks()


def test_parse_response_grouped_requires_task_group():
    # Missing <task_group> should raise a clear error
    bad_response = "<tasks></tasks>"

    with pytest.raises(ValueError) as exc_info:
        parse_response_grouped(bad_response, task_id="0")

    assert "<tasks> must contain at least one <task_group>" in str(
        exc_info.value
    )


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
