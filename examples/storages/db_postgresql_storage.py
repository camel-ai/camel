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


from pydantic import BaseModel, Field

from camel.agents import ChatAgent
from camel.configs.openai_config import ChatGPTConfig
from camel.memories.agent_memories import ChatHistoryMemory
from camel.memories.context_creators.score_based import ScoreBasedContextCreator
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

# Define system message
assistant_sys_msg = BaseMessage.make_assistant_message(
    role_name="Assistant",
    content="You are a helpful assistant.",
)

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
    model_config_dict=ChatGPTConfig().as_dict(),
)

context_creator = ScoreBasedContextCreator(model.token_counter, 
                                           model.token_limit)
# save data in database, Currently, only the SQLAlchemy format for PostgreSQL 
# is supported.
memory = ChatHistoryMemory(
            context_creator, 
            db_connect_str="postgresql://username:password@localhost/test")

# Set agent
camel_agent = ChatAgent(assistant_sys_msg, model=model, memory=memory)

user_msg = BaseMessage.make_user_message(
    role_name="User",
    content="Tell a jokes.",
)

# Get response information
response = camel_agent.step(user_msg)
print(response.msgs[0].content)

