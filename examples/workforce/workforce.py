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
from camel.agents.chat_agent import ChatAgent
from camel.messages.base import BaseMessage
from camel.tasks.task import Task
from camel.workforce.internal_workforce import InternalWorkforce
from camel.workforce.leaf_workforce import LeafWorkforce
from camel.workforce.task_channel import TaskChannel


def main():
    human_task = Task(content='develop a python program of investing stock.')

    public_channel = TaskChannel()

    sys_msg_1 = BaseMessage.make_assistant_message(
        role_name="programmer",
        content="You are a python programmer.",
    )
    sys_msg_2 = BaseMessage.make_assistant_message(
        role_name="researcher",
        content="You are good at marketing",
    )
    sys_msg_3 = BaseMessage.make_assistant_message(
        role_name="product owner",
        content="You are familiar with internet.",
    )
    agent_1 = ChatAgent(sys_msg_1)
    agent_2 = ChatAgent(sys_msg_2)
    agent_3 = ChatAgent(sys_msg_3)

    unit_workforce_1 = LeafWorkforce(1, 'agent1', agent_1, public_channel)
    unit_workforce_2 = LeafWorkforce(2, 'agent2', agent_2, public_channel)
    unit_workforce_3 = LeafWorkforce(3, 'agent3', agent_3, public_channel)

    workforces = InternalWorkforce(
        4,
        'a software group',
        [unit_workforce_1, unit_workforce_2, unit_workforce_3],
        None,
        public_channel,
    )

    workforces.start()

    workforces.process_task(human_task)
