import asyncio
import random

from camel.environments.models import Action
from camel.environments.envs import TicTacToeEnv


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
        
        action = Action(problem_statement="", llm_response="<Action>" + str(chosen_move), metadata={})  
                
        # Update the game state with the chosen move.
        await env._update_state(action)
        
        # Print the board after the move. If the game ended, print terminal observation.
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
