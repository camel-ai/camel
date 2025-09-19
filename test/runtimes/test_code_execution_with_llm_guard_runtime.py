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

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.runtimes import LLMGuardRuntime
from camel.toolkits.code_execution import CodeExecutionToolkit
from camel.types import ModelPlatformType, ModelType


def test_code_execution_with_llm_guard_runtime():
    runtime = LLMGuardRuntime(verbose=True).add(
        *CodeExecutionToolkit().get_tools()
    )

    tools = runtime.get_tools()

    assert len(tools) == 2

    assert tools[0].get_function_name() == "ignore_risk"
    assert tools[1].get_function_name() == "execute_code"

    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    # set up agent
    assistant_sys_msg = BaseMessage.make_assistant_message(
        role_name="Teacher",
        content=(
            "You are a personal math tutor and programmer. "
            "When asked a math question, "
            "write and run Python code to answer the question."
        ),
    )

    agent = ChatAgent(
        assistant_sys_msg,
        model,
        tools=tools,
    )
    agent.reset()

    # set up agent

    prompt = (
        "Weng earns $12 an hour for babysitting. "
        "Yesterday, she just did 51 minutes of babysitting."
        "How much did she earn?"
    )
    user_msg = BaseMessage.make_user_message(role_name="User", content=prompt)

    agent.step(user_msg)
