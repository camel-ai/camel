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

    # Setup the environment (if needed)
    await env._setup()

    # Initialize the game state
    env._state = env._get_initial_state()
    observation = env._get_next_observation()
    print(observation.question)

    while not env._is_done():
        board = env._state["board"]

        available = env.available_moves(board)
        if not available:
            break

        chosen_move = random.choice(available) + 1
        print(f"\nPlayer (X) selects move: {chosen_move}")

        action = Action(
            problem_statement="",
            llm_response="<Action>" + str(chosen_move),
            metadata={},
        )

        # Update the game state with the chosen move.
        await env._update_state(action)

        # Print the board after the move.
        # If the game ended, print terminal observation.
        if env._is_done():
            observation = env._get_terminal_observation()
        else:
            observation = env._get_next_observation()
        print(observation.question)

    # Compute and display the reward for the game outcome.
    reward, info = await env.compute_reward()
    print(f"\nGame over with reward: {reward} and info: {info}")

    # Close the environment (if needed)
    await env._close()


if __name__ == "__main__":
    asyncio.run(run_game())
