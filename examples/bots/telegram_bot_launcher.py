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
import argparse

from camel.agents import ChatAgent
from camel.configs.openai_config import ChatGPTConfig
from camel.messages import BaseMessage
from camel.models import OpenAIModel
from camel.types import ModelType
from examples.bots import TelegramBot

parser = argparse.ArgumentParser(
    description="Arguments for telegram bot.",
)
parser.add_argument(
    "--sys_msg",
    type=str,
    help="System message for the telegram bot.",
    required=False,
    default="You are a helpful assistant.",
)
parser.add_argument(
    "--model_type",
    type=str,
    help="Model type for the telegram bot.",
    required=False,
    default=ModelType.GPT_3_5_TURBO.value,
)

args = parser.parse_args()


def main():
    assistant_sys_msg = BaseMessage.make_assistant_message(
        role_name="Assistant",
        content=args.sys_msg,
    )
    model = OpenAIModel(
        model_type=ModelType(args.model_type),
        model_config_dict=ChatGPTConfig().__dict__,
    )
    agent = ChatAgent(
        assistant_sys_msg,
        model=model,
    )
    bot = TelegramBot(agent)
    bot.run()


if __name__ == "__main__":
    main()
