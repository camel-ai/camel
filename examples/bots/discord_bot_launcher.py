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
from camel.configs import ChatGPTConfig
from camel.messages import BaseMessage
from camel.models import OpenAIModel
from camel.retrievers import AutoRetriever
from camel.types import ModelType, StorageType
from examples.bots import DiscordBot

DEFAULT_CONTENT = """Objective: 
You are a customer service bot designed to assist users
with inquiries related to our open-source project. 
Your responses should be informative, concise, and helpful.

Instructions:
    Understand User Queries:
        Carefully read and understand the user's question.
        Focus on keywords and context to determine the user's intent.
    Search for Relevant Information:
        Use the provided dataset and refer to the RAG
        (file to find answers that closely match the user's query.
        The RAG file contains detailed interactions and should be your
        primary resource for crafting responses.
    Provide Clear and Concise Responses: Your answers should 
        be clear and to the point. Avoid overly technical
        language unless the user's query indicates 
        familiarity with technical terms.
    Encourage Engagement: Where applicable, encourage users
        to contribute to the project or seek further
        assistance.

Response Structure:
    Greeting: Begin with a polite greeting or acknowledgment.
    Main Response: Provide the main answer to the user's query.
    Additional Information: Offer any extra tips or direct the
        user to additional resources if necessary.
    Closing: Close the response politely, encouraging
        further engagement if appropriate.

Tone:
    Professional: Maintain a professional tone that 
        instills confidence in the user.
    Friendly: Be approachable and friendly to make users 
        feel comfortable.
    Helpful: Always aim to be as helpful as possible,
        guiding users to solutions.        
"""

parser = argparse.ArgumentParser(
    description="Arguments for discord bot.",
)
parser.add_argument(
    "--sys_msg",
    type=str,
    help="System message for the discord bot.",
    required=False,
    default=DEFAULT_CONTENT,
)
parser.add_argument(
    "--model_type",
    type=str,
    help="Model type for the discord bot.",
    required=False,
    default=ModelType.GPT_3_5_TURBO.value,
)
parser.add_argument(
    "--local_storage",
    action="store_true",
    help="Whether to use local storage for discord bot.",
    required=False,
)
parser.add_argument(
    "--storage_local_path",
    help="Path for local storage.",
    required=False,
    default="local_data/",
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
        system_message=assistant_sys_msg,
        model=model,
        message_window_size=10,
    )
    auto_retriever = None
    vector_storage_local_path = ""
    if args.local_storage:
        auto_retriever = AutoRetriever(
            vector_storage_local_path="examples/bots",
            storage_type=StorageType.QDRANT,
        )
        vector_storage_local_path = [args.storage_local_path]

    bot = DiscordBot(
        agent,
        auto_retriever=auto_retriever,
        vector_storage_local_path=vector_storage_local_path,
    )
    bot.run()


if __name__ == "__main__":
    main()
