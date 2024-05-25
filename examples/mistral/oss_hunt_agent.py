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
import os

from camel.agents import ChatAgent
from camel.configs import MistralConfig
from camel.functions import OpenAIFunction
from camel.functions.search_functions import search_google
from camel.functions.twitter_function import create_tweet
from camel.messages import BaseMessage
from camel.types import ModelType, RoleType

os.environ["MISTRAL_API_KEY"] = "XpTqOjvetVjtCfRSYkOfxY2te1cfvbTp"
os.environ["GOOGLE_API_KEY"] = "AIzaSyBIaVHuNCnH2-B4SQbqOvy2lMOlGOLYCEk"
os.environ["SEARCH_ENGINE_ID"] = "e6d9bb79dc6794f38"

create_tweet_tool = OpenAIFunction(create_tweet)
search_google_tool = OpenAIFunction(search_google)

tools = [
    search_google_tool.openai_tool_schema,
    create_tweet_tool.openai_tool_schema,
]

model_config_dict = dict(
    tools=tools,
    tool_choice="auto",
)

query_1 = "What's the status of my transaction T1001?"
query_2 = "Post a tweet to say 'Hello World' on twitter"
query_3 = "Use google research to find out the date of today"

# bm = BaseMessage.make_user_message('user', query_2).to_openai_message(
#     OpenAIBackendRole.USER)
# print(bm)

# mistral_model = MistralModel(ModelType.MISTRAL_LARGE, model_config_dict)
# print(mistral_model.run([bm]))

# Start from here

model_config = MistralConfig(
    tools=tools,
    tool_choice="auto",
)

system_message = BaseMessage(
    role_name="mistral agent",
    role_type=RoleType.DEFAULT,
    meta_dict={},
    content="You are a helpful assistant.",
)

mistral_agent = ChatAgent(
    system_message=system_message,
    model_type=ModelType.MISTRAL_LARGE,
    model_config=model_config,
    function_list=[create_tweet_tool, search_google_tool],
)

bm = BaseMessage.make_user_message('user', query_3)

mistral_agent.reset()
response = mistral_agent.step(bm)
print(response.msg)
