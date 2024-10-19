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
from camel.messages import BaseMessage
from camel.toolkits import TWITTER_FUNCS, WEATHER_FUNCS


def main():
    """
    To run this, you need to set the following environment variables:
    - TWITTER_CONSUMER_KEY
    - TWITTER_CONSUMER_SECRET
    - TWITTER_ACCESS_TOKEN
    - TWITTER_ACCESS_TOKEN_SECRET
    - OPENWEATHERMAP_API_KEY
    """

    sys_msg = BaseMessage.make_assistant_message(
        role_name="Assistant",
        content="You are an agent that can help me with my Twitter account.",
    )

    agent = ChatAgent(
        system_message=sys_msg, tools=[*TWITTER_FUNCS, *WEATHER_FUNCS]
    )

    usr_msg = BaseMessage.make_user_message(
        role_name="User",
        content="Check the weather in New York City and post it on Twitter.",
    )

    response = agent.step(usr_msg)
    print(response.msg.content)


if __name__ == '__main__':
    main()
