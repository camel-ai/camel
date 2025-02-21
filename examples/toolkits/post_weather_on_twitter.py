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
from colorama import Fore

from camel.agents import ChatAgent
from camel.toolkits import SearchToolkit, TwitterToolkit, WeatherToolkit
from camel.utils import print_text_animated


def main():
    """
    To run this, you need to set the following environment variables:
    - TWITTER_CONSUMER_KEY
    - TWITTER_CONSUMER_SECRET
    - TWITTER_ACCESS_TOKEN
    - TWITTER_ACCESS_TOKEN_SECRET
    - OPENWEATHERMAP_API_KEY
    - GOOGLE_API_KEY
    - SEARCH_ENGINE_ID
    """

    sys_msg = "You are a helpful agent with multiple tools."

    agent = ChatAgent(
        system_message=sys_msg,
        tools=[
            *TwitterToolkit().get_tools(),
            *WeatherToolkit().get_tools(),
            *SearchToolkit().get_tools(),
        ],
    )

    usr_msg = "I'm in Chicago and want to travel to Oxford today. Make a "
    "travel plan for me, considering the weather today. Also announce my "
    "plan on Twitter from my perspective."

    response = agent.step(usr_msg)

    for tool_call in response.info["tool_calls"]:
        print(f"{Fore.YELLOW}{tool_call}{Fore.RESET}\n======")

    print_text_animated(
        f"{Fore.GREEN}{response.msg.content}{Fore.RESET}", delay=0.005
    )


if __name__ == '__main__':
    main()
