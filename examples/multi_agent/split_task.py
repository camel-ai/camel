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
import json

from colorama import Fore

from camel.agents.role_assignment_agent import RoleAssignmentAgent
from camel.configs import ChatGPTConfig


def main(model_type=None) -> None:
    task_prompt = "Develop a trading bot for the stock market."

    model_config_description = ChatGPTConfig()
    role_assignment_agent = RoleAssignmentAgent(
        model=model_type, model_config=model_config_description)

    num_roles = 5

    role_descriptions_dict = role_assignment_agent.run(task_prompt=task_prompt,
                                                       num_roles=num_roles)

    context_text = """### **Enterprise Overview:**
**Enterprise Name:** GlobalTradeCorp
**Industry:** Financial Technology
**Years in Business:** 15 years
**Key Business Area:** Developing trading algorithms and financial tools for institutions and retail traders.

### **Background & Need:**
GlobalTradeCorp has always been at the forefront of financial innovations. With the advent of algorithmic trading, our institution saw a rise in demand for automated tools that can aid both retail and institutional traders. Our clientele base, ranging from hedge funds to independent day traders, has been expressing the need for a sophisticated trading bot that can adapt to the ever-changing stock market dynamics.

### **Existing Infrastructure & Tools:**
- **Trading Platforms**: Our enterprise uses a mix of MetaTrader 4, Thinkorswim, and proprietary platforms for executing trades.
- **Data Feed**: We receive real-time data feeds from Bloomberg Terminal, which includes stock prices, news alerts, and other relevant trading information.
- **Cloud Infrastructure**: Most of our applications are hosted on AWS, leveraging services like EC2, RDS, and Lambda.
- **Current Bots**: We have a few basic trading bots in place, mainly for forex trading, based on predefined strategies like MACD crossovers and Bollinger Bands.

### **Objective of the New Trading Bot:**
The new trading bot should be able to:
1. Analyze large datasets in real-time, including stock prices, news feeds, and social media sentiments.
2. Make buy/sell decisions based on a mix of predefined strategies and adaptive AI algorithms.
3. Automatically adjust its strategies based on market conditions (e.g., bull markets, bear markets, high volatility).
4. Provide a user-friendly interface where traders can set their risk levels, investment amounts, and other preferences.
5. Offer simulation modes for back-testing strategies.

### **Challenges & Considerations:**
- **Latency**: Every millisecond counts in algorithmic trading. The bot should be optimized for speed.
- **Regulations**: Ensure the bot adheres to all SEC regulations and other regional financial guidelines.
- **Error Handling**: A minor bug or miscalculation can lead to significant losses. Robust error handling and fail-safes are crucial.
- **Adaptability**: Stock markets are influenced by myriad factors. The bot should be adaptable and not overly reliant on any single strategy."""  # noqa: E501

    subtasks_with_dependencies_dict = role_assignment_agent.split_tasks(
        task_prompt=task_prompt, role_descriptions_dict=role_descriptions_dict,
        num_subtasks=None,
        context_text=context_text)  # let LLM decide the number of subtasks
    subtasks = [
        subtasks_with_dependencies_dict[key]["description"]
        for key in sorted(subtasks_with_dependencies_dict.keys())
    ]

    if subtasks is None:
        raise ValueError("subtasks is None.")

    print(Fore.BLUE + "Dependencies among subtasks: " +
          json.dumps(subtasks_with_dependencies_dict, indent=4))
    for (i, subtask) in enumerate(subtasks_with_dependencies_dict.keys()):
        print(Fore.GREEN + f"Subtask {i+1}:\n" +
              f"{subtasks_with_dependencies_dict[subtask]['description']}")
        deps = subtasks_with_dependencies_dict[subtask]["dependencies"]
        print(Fore.CYAN + "Dependencies: [" + ", ".join(dep
                                                        for dep in deps) + "]")
    for (i, (role_name,
             role_description)) in enumerate(role_descriptions_dict.items()):
        print(Fore.GREEN + f"Role {i + 1}. {role_name}: {role_description}")


if __name__ == "__main__":
    main()
