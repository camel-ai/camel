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


@pytest.fixture
def temp_image():
    # Create temporary image file and return PIL Image object
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
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        f.write(b"fake video data")
        f.flush()
        f.seek(0)
        video_bytes = f.read()
        yield video_bytes
    os.remove(f.name)


def test_image_task_management():
    """
    Task 0: 分析图片
        Task 1: 检测图片中的物体
        Task 2: 识别图片中的文字
            Task 2.1: 识别标题文字
            Task 2.2: 识别正文文字
        Task 3: 生成图片描述
    """
    from camel.tasks.task import Task, TaskManager

    root_task = Task(content="分析图片", id="0")
    sub_task_1 = Task(content="检测图片中的物体", id="1")
    sub_task_2 = Task(content="识别图片中的文字", id="2")
    sub_task_3 = Task(content="生成图片描述", id="3")
    sub_task_2_1 = Task(content="识别标题文字", id="2.1")
    sub_task_2_2 = Task(content="识别正文文字", id="2.2")

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


def test_video_task_management():
    """
    Task 0: 分析视频
        Task 1: 检测视频中的人物
        Task 2: 识别视频中的语音
            Task 2.1: 识别开头对白
            Task 2.2: 识别结尾对白
        Task 3: 生成视频摘要
    """
    from camel.tasks.task import Task, TaskManager

    root_task = Task(content="分析视频", id="0")
    sub_task_1 = Task(content="检测视频中的人物", id="1")
    sub_task_2 = Task(content="识别视频中的语音", id="2")
    sub_task_3 = Task(content="生成视频摘要", id="3")
    sub_task_2_1 = Task(content="识别开头对白", id="2.1")
    sub_task_2_2 = Task(content="识别结尾对白", id="2.2")

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
