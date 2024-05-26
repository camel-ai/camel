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

from camel.messages import BaseMessage as bm
from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.functions import MATH_FUNCS, SEARCH_FUNCS



sys_msg = bm.make_assistant_message(
    role_name='assistant',
    content='you are a helpful assistant')

model_config = ChatGPTConfig(
    stream=False,
)

agent2 = ChatAgent(
    system_message=sys_msg,
    message_window_size=10,
    model_config=model_config,
    )


agent2.reset()
# Define a user message
usr_msg = bm.make_user_message(
    role_name='prof. claude shannon',
    content='say hi to me')
# Sending the message to the agent
response_generator = agent2.step(usr_msg)
# print("type of ChatAgent response")
# print(type(response_generator))

for response in response_generator:
    print(response)
    # for msg in response.msgs:
    #     print(msg) 









# tools = [
#   {
#     "type": "function",
#     "function": {
#       "name": "get_current_weather",
#       "description": "Get the current weather in a given location",
#       "parameters": {
#         "type": "object",
#         "properties": {
#           "location": {
#             "type": "string",
#             "description": "The city and state, e.g. San Francisco, CA",
#           },
#           "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
#         },
#         "required": ["location"],
#       },
#     }
#   }
# ]

# from openai import OpenAI
# client = OpenAI()

# response = client.chat.completions.create(
#     model="gpt-3.5-turbo",
#     messages=[
#         {"role": "system", "content": "You are a helpful assistant."},
#         {"role": "user", "content":"What's the weather like in Boston today?"}
#     ],
#     stream=True,
#     tools=tools,
#     tool_choice="required"
#     )

# # print(response)


# for chunk in response:
#     # print(chunk)

#     choice = chunk.choices[0]
#     # print(choice)
#     # print(choice.delta.content, end="", flush=True)
#     print(choice.delta.tool_calls)

# # print(response.choices[0])