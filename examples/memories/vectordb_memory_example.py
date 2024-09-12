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

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.memories import ScoreBasedContextCreator, VectorDBMemory
from camel.messages import BaseMessage as bm
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType


def main():
    sys_msg = bm.make_assistant_message(
        role_name="smart assistant",
        content="you are a smart assistant about the world.",
    )

    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O_MINI,
        model_config_dict=ChatGPTConfig().as_dict(),
    )

    context_creator = ScoreBasedContextCreator(
        model.token_counter, model.token_limit
    )

    memory = VectorDBMemory(context_creator)

    agent = ChatAgent(
        system_message=sys_msg, message_window_size=10, memory=memory
    )

    usr_msg = bm.make_user_message(
        role_name="CAMEL user", content="hi, this is David."
    )

    response = agent.step(usr_msg)

    print(response.msgs[0].content)


if __name__ == "__main__":
    main()
