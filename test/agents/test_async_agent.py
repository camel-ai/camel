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
import asyncio

from camel.agents.chat_agent import ChatAgent
from camel.agents.embodied_agent import EmbodiedAgent
from camel.messages.base import BaseMessage
from camel.responses.agent_responses import ChatAgentResponse


def test_Async_Agent():
    assistant_sys_msg = BaseMessage.make_assistant_message(
        role_name="Assistant",
        content="You are a helpful assistant.",
        )
    user_msg = BaseMessage.make_user_message(
        role_name="User",
        content="Hello!",
        )
    chatagent_1 = ChatAgent(assistant_sys_msg)
    chatagent_2 = ChatAgent(assistant_sys_msg)
    embodiedagent = EmbodiedAgent(assistant_sys_msg)

    loop = asyncio.get_event_loop()

    tasks = [
            loop.create_task(chatagent_1.astep(user_msg)),
            loop.create_task(chatagent_2.astep(user_msg)),
            loop.create_task(embodiedagent.astep(user_msg))
        ]
    wait_coro = asyncio.wait(tasks)
    loop.run_until_complete(wait_coro)

    for task in tasks:
        assert isinstance(task.result(), ChatAgentResponse)
  
    loop.close()
