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
import pytest
import re
from unittest.mock import AsyncMock, MagicMock
from camel.environments.tic_tac_toe import TicTacToeEnv
from camel.environments.models import Action, Observation

# --- Setup and Initialization Tests ---

@pytest.mark.asyncio
async def test_setup_and_reset():
    """Test setup idempotency and reset functionality."""
    mock_extractor = MagicMock()
    mock_extractor.setup = AsyncMock()
    mock_extractor.cleanup = AsyncMock()
    env = TicTacToeEnv()
    await env.setup()
    assert env._is_setup is True
    await env.setup()  # Idempotent check
    assert env._is_setup is True
    observation = await env.reset()
    state = env._state
    assert state["board"] == [" " for _ in range(9)]
    assert state["game_over"] is False
    assert state["winner"] is None
    assert state["last_move_illegal"] is False
    assert "You are playing Tic Tac Toe" in observation.question
    assert "Choose a number between 1 and 9" in observation.question
    assert env._current_step == 0
    await env.close()

# --- Step Tests: Moves ---

@pytest.mark.asyncio
@pytest.mark.parametrize("move, expected_behavior", [
    ("5", "valid"),
    ("10", "invalid_move"),
    ("-1", "invalid_input"),
])
async def test_moves(move, expected_behavior):
    env = TicTacToeEnv()
    await env.setup()
    await env.reset()
    action = Action(llm_response=f"<Action>{move}</Action>")
    
    if expected_behavior == "invalid_input":
        with pytest.raises(ValueError):
            await env.step(action)
    else:
        step_result = await env.step(action)
        state = env._state
        if expected_behavior == "invalid_move":
            assert state["board"] == [" " for _ in range(9)]
            assert state["last_move_illegal"] is True
        else:
            move_index = int(move) - 1
            assert state["board"][move_index] == "X"
            assert state["board"].count("X") == 1
            assert state["board"].count("O") == 1
            assert state["last_move_illegal"] is False
        assert step_result.reward == 0.0
        assert step_result.done is False
    await env.close()

@pytest.mark.asyncio
async def test_move_occupied():
    """Test moving to an occupied position."""
    env = TicTacToeEnv()
    await env.setup()
    await env.reset()
    await env.step(Action(llm_response="<Action>1</Action>"))
    step_result = await env.step(Action(llm_response="<Action>1</Action>"))
    state = env._state
    assert state["last_move_illegal"] is True
    assert state["board"][0] == "X"
    assert step_result.reward == 0.0
    assert step_result.done is False
    assert "Your last move was illegal" in step_result.observation.question
    await env.close()

# --- Step Tests: Invalid Inputs ---

@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_input", ["<Action>abc</Action>", "5", "<Action></Action>"])
async def test_invalid_inputs(invalid_input):
    """Test invalid action inputs."""
    env = TicTacToeEnv()
    await env.setup()
    await env.reset()
    action = Action(llm_response=invalid_input)
    with pytest.raises(ValueError):
        await env.step(action)
    await env.close()

# --- Game End Tests ---

@pytest.mark.asyncio
async def test_agent_wins():
    """Test agent winning."""
    env = TicTacToeEnv()
    await env.setup()
    await env.reset()
    env._state["board"] = ["X", "X", " ", "O", "O", " ", " ", " ", " "]
    step_result = await env.step(Action(llm_response="<Action>3</Action>"))
    state = env._state
    assert state["board"] == ["X", "X", "X", "O", "O", " ", " ", " ", " "]
    assert state["game_over"] is True
    assert state["winner"] == "X"
    assert step_result.reward == 1.0
    assert step_result.done is True
    assert "Congratulations, you won!" in step_result.observation.question
    await env.close()

@pytest.mark.asyncio
async def test_opponent_wins():
    """Test opponent winning after agent's move."""
    env = TicTacToeEnv()
    await env.setup()
    await env.reset()
    env._state["board"] = ["O", " ", "O", "X", "X", " ", " ", " ", " "]
    step_result = await env.step(Action(llm_response="<Action>7</Action>"))
    state = env._state
    assert state["board"][1] == "O"  # Opponent places 'O' to win
    assert state["game_over"] is True
    assert state["winner"] == "O"
    assert step_result.reward == -1.0
    assert step_result.done is True
    assert "Sorry, you lost!" in step_result.observation.question
    await env.close()

@pytest.mark.asyncio
async def test_draw():
    """Test a draw."""
    env = TicTacToeEnv()
    await env.setup()
    await env.reset()
    env._state["board"] = ["X", "O", "X", "O", "O", "X", "X", " ", "O"]
    step_result = await env.step(Action(llm_response="<Action>8</Action>"))
    state = env._state
    assert state["board"] == ["X", "O", "X", "O", "O", "X", "X", "X", "O"]
    assert state["game_over"] is True
    assert state["winner"] == "draw"
    assert step_result.reward == 0.0
    assert step_result.done is True
    assert "It's a draw!" in step_result.observation.question
    await env.close()

# --- Helper Method Tests ---

def test_helper_methods():
    """Test render_board, check_winner, and available_moves."""
    env = TicTacToeEnv()
    # Test render_board
    board = ["X", "O", " ", " ", "X", " ", " ", " ", "O"]
    assert env.render_board(board) == "X | O | 3\n---------\n4 | X | 6\n---------\n7 | 8 | O"
    # Test check_winner
    assert env.check_winner(["X", "X", "X", "O", "O", " ", " ", " ", " "]) == "X"
    assert env.check_winner(["O", " ", " ", "O", " ", " ", "O", " ", " "]) == "O"
    assert env.check_winner(["X", "O", "X", "X", "O", "O", "O", "X", "X"]) == "draw"
    assert env.check_winner(["X", "O", " ", " ", " ", " ", " ", " ", " "]) is None
    # Test available_moves
    assert env.available_moves(board) == [2, 3, 5, 6, 7]

def test_opponent_move_and_minimax():
    """Test opponent move and minimax algorithm."""
    env = TicTacToeEnv()
    board = ["X", "X", " ", " ", "O", " ", " ", " ", " "]
    assert env.get_opponent_move(board) == 2  # Blocks X's win
    score, move = env.minimax(board, is_maximizing=False)
    assert score == -1
    assert move == 2

# --- Error Handling Tests ---

@pytest.mark.asyncio
async def test_step_errors():
    """Test errors for stepping without setup, after done, or without reset."""
    # Without setup
    mock_extractor = MagicMock()
    env = TicTacToeEnv()
    with pytest.raises(RuntimeError, match="Environment not set up"):
        await env.step(Action(llm_response="<Action>5</Action>"))

    # After done
    mock_extractor = MagicMock()
    mock_extractor.setup = AsyncMock()
    mock_extractor.cleanup = AsyncMock()
    env = TicTacToeEnv()
    await env.setup()
    await env.reset()
    env._episode_ended = True
    with pytest.raises(RuntimeError, match="Episode has ended"):
        await env.step(Action(llm_response="<Action>5</Action>"))
    await env.close()

    # Without reset
    mock_extractor = MagicMock()
    mock_extractor.setup = AsyncMock()
    mock_extractor.cleanup = AsyncMock()
    env = TicTacToeEnv()
    await env.setup()
    env._last_observation = None  # Simulate no reset
    with pytest.raises(RuntimeError, match="No current observation"):
        await env.step(Action(llm_response="<Action>5</Action>"))
    await env.close()

# --- Full test ---
@pytest.mark.asyncio
async def test_full_game():
    """Test a full game sequence leading to X win."""
    env = TicTacToeEnv()
    await env.setup()
    await env.reset()

    moves = ["1", "2", "4"]
    for i, move in enumerate(moves):
        step_result = await env.step(Action(llm_response=f"<Action>{move}</Action>"))
        if i < len(moves) - 1:
            assert step_result.done is False
            assert step_result.reward == 0.0
        else:
            assert step_result.done is True
            assert step_result.reward == -1.0
            assert env._state["winner"] == "O"
    await env.close()