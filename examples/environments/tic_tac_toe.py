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
import asyncio
import random

from camel.environments import TicTacToeEnv
from camel.environments.models import Action


async def run_game():
    env = TicTacToeEnv()
    # Initialize and set up the environment
    await env.setup()

    # Reset environment and get initial observation
    observation = await env.reset()
    print("Initial Observation:\n")
    print(observation.question)

    while not env.is_done():
        available_moves = [
            move + 1
            for move in TicTacToeEnv.available_moves(env._state["board"])
        ]

        action = Action(
            llm_response=f"<Action> {random.choice(available_moves)}"
        )
        result = await env.step(action)

        observation, reward, done, info = result

        print("\nAgent Move:", action)
        print("Observation:")
        print(observation.question)
        print("Reward:", reward)
        print("Done:", done)
        print("Info:", info)

    print("\n___________\n\nBoard at the end:\n")
    print(env.render_board(env._state["board"]), "\n")
    await env._close()


if __name__ == "__main__":
    asyncio.run(run_game())
