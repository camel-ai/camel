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
import time

from camel.agents import BabyAGIAgent
from camel.typing import ModelType


def main() -> None:
    mode_type = ModelType.GPT_3_5_TURBO
    objective = "Solve world hunger."
    first_task = {"task_id": 1, "task_name": "Develop a task list."}

    print("\033[91m\033[1m" + "\n*****OBJECTIVE*****\n" + "\033[0m\033[0m")
    print(objective)

    babyagi_play_session = BabyAGIAgent(objective, mode_type)
    babyagi_play_session.reset(first_task)

    limit = 5
    n = 0
    while n < limit:
        n += 1
        if not babyagi_play_session.tasks_storage.is_empty():

            info = babyagi_play_session.step()
            print("\033[92m\033[1m" + "\n*****CURRENT TASK*****\n" +
                  "\033[0m\033[0m")
            print(
                str(info['current_task'][0]) + ": " + info['current_task'][1])

            print("\033[93m\033[1m" + "\n*****TASK RESULT*****\n" +
                  "\033[0m\033[0m")
            print(info['task_result'])

            print("\033[94m\033[1m" + "\n*****NEW TASKS*****\n" +
                  "\033[0m\033[0m")
            for new_task in info['new_tasks_ordering']:
                print(str(new_task["task_id"]) + ": " + new_task["task_name"])

            print("\033[95m\033[1m" + "\n*****PRIORITIZED TASKS*****\n" +
                  "\033[0m\033[0m")
            for new_task in info['prioritized_tasks_ordering']:
                print(str(new_task["task_id"]) + ": " + new_task["task_name"])

            # Sleep a bit before checking the task list again
            time.sleep(3)


if __name__ == "__main__":
    main()
