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
