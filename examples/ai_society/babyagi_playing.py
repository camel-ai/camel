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
from camel.generators import SystemMessageGenerator
from camel.typing import ModelType, RoleType, TaskType
from camel.messages import BaseMessage
from camel.configs import ChatGPTConfig


def main() -> None:
    model = ModelType.GPT_3_5_TURBO
    model_config = ChatGPTConfig()
    system_msg = SystemMessageGenerator(
        task_type=TaskType.AI_SOCIETY).from_dict(
            dict(assistant_role="doctor"),
            role_tuple=("doctor", RoleType.ASSISTANT),
        )
    objective = "Solve gastric cancel."

    print("\033[91m\033[1m" + "\n*****OBJECTIVE*****\n" + "\033[0m\033[0m")
    print(objective)

    babyagi_play_session = BabyAGIAgent(system_msg, objective,
                           model=model, model_config=model_config)
    babyagi_play_session.reset()

    limit = 15
    n = 0
    babyagi_play_session.tasks_storage.append({'task_name': objective})
    while n < limit:
        n += 1
        if not babyagi_play_session.tasks_storage.is_empty():
            task = babyagi_play_session.tasks_storage.popleft()
            prompt = 'Instruction: ' + task['task_name']
            user_msg = BaseMessage(role_name="Patient", \
                       role_type=RoleType.USER, meta_dict=dict(), 
                       content=prompt)
            response = babyagi_play_session.step(user_msg)
            info = response.info['log_info']
            print("\033[92m\033[1m" + "\n*****CURRENT TASK*****\n" +
                  "\033[0m\033[0m")
            print(info['current_task'])

            print("\033[93m\033[1m" + "\n*****TASK RESULT*****\n" +
                  "\033[0m\033[0m")
            print(info['task_result'])

            if (info['new_tasks'] and info['prioritized_tasks']):
                print("\033[94m\033[1m" + "\n*****NEW TASKS*****\n" +
                      "\033[0m\033[0m")
                for i, new_task in enumerate(info['new_tasks'][:5]):
                    print(str(i) + ": " + new_task["task_name"])

                print("\033[95m\033[1m" + "\n*****PRIORITIZED TASKS*****\n" +
                      "\033[0m\033[0m")
                for i, new_task in enumerate(info['prioritized_tasks'][:5]):
                    print(str(i) + ": " + new_task["task_name"])

            # Sleep a bit before checking the task list again
            time.sleep(3)

if __name__ == "__main__":
    main()

