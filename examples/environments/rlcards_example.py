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

"""
This example demonstrates how to use the RLCards environments in CAMEL.
It shows how to create and interact with both Blackjack and Leduc Hold'em
environments.
"""

import asyncio
from typing import List

from camel.environments import (
    Action,
    BlackjackEnv,
    LeducHoldemEnv,
    Observation,
)


async def simulate_agent_response(
    observation: Observation, actions: List[str]
) -> str:
    """
    Simulate an agent's response by selecting from a list of predefined actions
    In a real scenario, this would be replaced with an actual LLM call.

    Args:
        observation: The current observation from the environment
        actions: List of possible actions to choose from

    Returns:
        A simulated agent response with an action
    """
    # In a real scenario, you would send the observation to an LLM and get a
    # response
    # Here we just select the first legal action mentioned in the observation

    # Extract legal actions from the observation
    legal_actions_line = ""
    for line in observation.question.split("\n"):
        if "Legal actions:" in line:
            legal_actions_line = line.split("Legal actions:")[1].strip()
            break

    # Choose the first legal action
    chosen_action = (
        legal_actions_line.split(", ")[0] if legal_actions_line else actions[0]
    )

    # Simulate a response with the chosen action
    return f"I choose to {chosen_action}. <Action> {chosen_action}"


async def play_blackjack():
    """
    Example of playing a Blackjack game with a simulated agent.
    """
    print("\n=== Playing Blackjack ===\n")

    # Create the Blackjack environment
    env = BlackjackEnv(max_steps=10)

    # Set up the environment
    await env.setup()

    # Reset the environment to start a new game
    observation = await env.reset()
    print("Initial observation:")
    print(observation.question)

    # Game loop
    done = False
    total_reward = 0
    step = 0

    while not done:
        step += 1
        print(f"\nStep {step}:")

        # Get agent's action (simulated)
        agent_response = await simulate_agent_response(
            observation, ["hit", "stand"]
        )
        print(f"Agent response: {agent_response}")

        # Take a step in the environment
        observation, reward, done, info = await env.step(
            Action(llm_response=agent_response)
        )
        total_reward += reward

        print(f"Reward: {reward}")
        print("New observation:")
        print(observation.question)

    print(f"\nGame over! Total reward: {total_reward}")

    # Clean up
    await env.close()


async def play_leduc_holdem():
    """
    Example of playing a Leduc Hold'em game with a simulated agent.
    """
    print("\n=== Playing Leduc Hold'em ===\n")

    # Create the Leduc Hold'em environment
    env = LeducHoldemEnv(max_steps=20)

    # Set up the environment
    await env.setup()

    # Reset the environment to start a new game
    observation = await env.reset()
    print("Initial observation:")
    print(observation.question)

    # Game loop
    done = False
    total_reward = 0
    step = 0

    while not done:
        step += 1
        print(f"\nStep {step}:")

        # Get agent's action (simulated)
        agent_response = await simulate_agent_response(
            observation, ["fold", "check", "call", "raise"]
        )
        print(f"Agent response: {agent_response}")

        # Take a step in the environment
        observation, reward, done, info = await env.step(
            Action(llm_response=agent_response)
        )
        total_reward += reward

        print(f"Reward: {reward}")
        print("New observation:")
        print(observation.question)

    print(f"\nGame over! Total reward: {total_reward}")

    # Clean up
    await env.close()


async def main():
    """
    Run examples of both Blackjack and Leduc Hold'em environments.
    """
    try:
        # Play a game of Blackjack
        await play_blackjack()

        # Play a game of Leduc Hold'em
        await play_leduc_holdem()

    except ImportError as e:
        print(f"Error: {e}")
        print("Please install RLCard with: pip install rlcard")


if __name__ == "__main__":
    asyncio.run(main())
