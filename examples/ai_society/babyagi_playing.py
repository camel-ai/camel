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

    babyagi_play_session = BabyAGIAgent(objective, mode_type)
    babyagi_play_session.init_tasks(first_task)

    limit = 5
    n = 0
    while n < limit:
        n += 1
        if not babyagi_play_session.tasks_storage.is_empty():
            # Step 1: Pull the first task
            task = babyagi_play_session.tasks_storage.popleft()
            print("\033[92m\033[1m" + "\n*****NEXT TASK*****\n" +
                  "\033[0m\033[0m")
            print(str(task['task_id']) + ": " + task['task_name'])

            # Send to execution function to complete the task
            # based on the context
            result = babyagi_play_session.execution_agent(
                objective, task["task_name"])
            print("\033[93m\033[1m" + "\n*****TASK RESULT*****\n" +
                  "\033[0m\033[0m")
            print(result)

            # Step 2: Enrich result and store in the results storage
            # This is where you should enrich the result if needed
            enriched_result = {"data": result}
            # extract the actual result from the dictionary
            # since we don't do enrichment currently
            # vector = enriched_result["data"]

            result_id = f"result_{task['task_id']}"
            babyagi_play_session.results_storage.add(task, result, result_id)

            # Step 3: Create new tasks and re-prioritize task list
            # only the main instance in cooperative mode does that
            new_tasks = babyagi_play_session.task_creation_agent(
                objective,
                enriched_result,
                task["task_name"],
                babyagi_play_session.tasks_storage.get_task_names(),
            )

            print('Adding new tasks to task_storage')
            for new_task in new_tasks:
                new_task.update({
                    "task_id":
                    babyagi_play_session.tasks_storage.next_task_id()
                })
                print(str(new_task))
                babyagi_play_session.tasks_storage.append(new_task)

            prioritized_tasks = babyagi_play_session.prioritization_agent()
            if prioritized_tasks:
                babyagi_play_session.tasks_storage.replace(prioritized_tasks)

            # Sleep a bit before checking the task list again
            time.sleep(3)


if __name__ == "__main__":
    main()
