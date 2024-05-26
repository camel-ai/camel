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
from camel.toolkits import GithubToolkit
from camel.messages import BaseMessage
from camel.types import ModelType, RoleType

os.environ["MISTRAL_API_KEY"] = "XpTqOjvetVjtCfRSYkOfxY2te1cfvbTp"
os.environ["GOOGLE_API_KEY"] = "AIzaSyBIaVHuNCnH2-B4SQbqOvy2lMOlGOLYCEk"
os.environ["SEARCH_ENGINE_ID"] = "e6d9bb79dc6794f38"
os.environ['TWITTER_CONSUMER_KEY'] = 'y6YKgE3WxSInjVGNKCyWZOO2s'
os.environ[
    'TWITTER_CONSUMER_SECRET'] = 'WDjrFEiJhMIQIqVne3RSgkqOwckj7eHIWZDUaZP1Enftnhb8Ad'

create_tweet_tool = OpenAIFunction(create_tweet)
search_google_tool = OpenAIFunction(search_google)
repo_name = "mistralai/mistral-inference"
github_tools = GithubToolkit(repo_name=repo_name).get_tools()

# tools = [
#     search_google_tool.openai_tool_schema,
#     create_tweet_tool.openai_tool_schema,
# ]

tools = [tool.openai_tool_schema for tool in github_tools]

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

# prompt = f"Summarize this pull request as a twitter {merged_prs[0]}"
# prompt = f"""
#     You need to write a summary of the latest pull requests of {repo_name} that were merged last two days.
#     You can use the provided github function retrieve_pull_requests to retrieve the list of pull requests that were merged.
#     The function will return a list of pull requests with the following properties: title, body, and diffs.
#     Diffs is a list of dictionaries with the following properties: filename, diff.
#     You will have to look closely at each diff to understand the changes that were made in each pull request.
#     Output a twitter post that describes recent changes in the project and thanks the contributors.

#     Here is an example of a summary for one pull request:
#     📢 We've improved function calling in the 🐪 CAMEL-AI framework!
#     This update enhances the handling of various docstring styles and supports enum types, ensuring more accurate and reliable function calls.
#     Thanks to our contributor Jiahui Zhang for making this possible.
#     """
prompt = f"""
    You need to write a summary of the latest pull requests of {repo_name}.
    You have to use the provided github function retrieve_pull_requests to retrieve the list of pull requests that were merged.
    The function takes no parameters.
    The function will return a list of pull requests with the following properties: title, body, and diffs.
    Diffs is a list of dictionaries with the following properties: filename, diff.
    You will have to look closely at each diff to understand the changes that were made in each pull request.
    Output a twitter post that describes recent changes in the project and thanks the contributors.
    Please not exceeds the character limit of 280 characters.
    """

model_config = MistralConfig(
    tools=[github_tools[3].openai_tool_schema],
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
    function_list=[github_tools[3]],
)

bm = BaseMessage.make_user_message('user', prompt)

mistral_agent.reset()
response = mistral_agent.step(bm)
# print(response)
print(response.msg.content)

# Post tweet Agent

model_config_2 = MistralConfig(
    tools=[create_tweet_tool.openai_tool_schema],
    tool_choice="auto",
)

system_message_2 = BaseMessage(
    role_name="mistral agent",
    role_type=RoleType.DEFAULT,
    meta_dict={},
    content="You are a helpful assistant for posting tweets.",
)

mistral_agent_2 = ChatAgent(
    system_message=system_message_2,
    model_type=ModelType.MISTRAL_LARGE,
    model_config=model_config_2,
    function_list=[create_tweet_tool],
)

prompt_2 = f"Post a tweet to say '{response.msg.content}' on twitter"
bm_2 = BaseMessage.make_user_message('user', prompt_2)
mistral_agent_2.reset()
response_2 = mistral_agent_2.step(bm_2)
print(response_2.msg.content)
