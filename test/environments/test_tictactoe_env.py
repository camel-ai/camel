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

from camel.environments.models import Action
from camel.environments.tic_tac_toe import Opponent, TicTacToeEnv

pytestmark = pytest.mark.heavy_dependency

# --- Setup and Initialization Tests ---


@pytest.mark.asyncio
async def test_setup_and_reset():
    """Test setup idempotency and reset functionality."""
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
@pytest.mark.parametrize(
    "input_move, expected_behavior",
    [
        ("5", "valid"),
        ("10", "invalid_move"),
        ("-1", "invalid_input"),
    ],
)
async def test_moves(input_move, expected_behavior):
    env = TicTacToeEnv()
    await env.setup()
    await env.reset()
    action = Action(llm_response=f"<Action>{input_move}</Action>")

    obs, reward, done, info = await env.step(action)
    state = env._state

    if (
        expected_behavior == "invalid_input"
        or expected_behavior == "invalid_move"
    ):
        assert state["board"] == [" " for _ in range(9)]
        assert state["last_move_illegal"] is True
        assert reward == 0.0
        if expected_behavior == "invalid_input":
            assert state["extraction_error"] is not None
    else:
        move_index = int(input_move) - 1
        assert state["board"][move_index] == "X"
        assert state["board"].count("X") == 1
        assert state["board"].count("O") == 1
        assert state["last_move_illegal"] is False

        expected = TicTacToeEnv.evaluate_position_for_x(
            state["board"], is_x_turn=True
        )
        assert reward == expected

    assert done is False
    await env.close()


@pytest.mark.asyncio
async def test_move_occupied():
    """Test moving to an occupied position."""
    env = TicTacToeEnv()
    await env.setup()
    await env.reset()
    await env.step(Action(llm_response="<Action>1</Action>"))
    obs, reward, done, info = await env.step(
        Action(llm_response="<Action>1</Action>")
    )
    state = env._state
    assert state["last_move_illegal"] is True
    assert state["board"][0] == "X"
    assert reward == 0.0
    assert done is False
    assert "Your last move was illegal" in obs.question
    await env.close()


# --- Step Tests: Invalid Inputs ---


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_input", ["<Action>abc</Action>", "5", "<Action></Action>"]
)
async def test_invalid_inputs(invalid_input):
    """Test invalid action inputs."""
    env = TicTacToeEnv()
    await env.setup()
    await env.reset()
    action = Action(llm_response=invalid_input)

    obs, reward, done, info = await env.step(action)
    state = env._state

    assert state["last_move_illegal"] is True
    assert state["extraction_error"] is not None or invalid_input == "5"
    assert reward == 0.0
    assert done is False

    await env.close()


# --- Game End Tests ---


@pytest.mark.asyncio
async def test_agent_wins():
    """Test agent winning."""
    env = TicTacToeEnv()
    await env.setup()
    await env.reset()
    env._state["board"] = ["X", "X", " ", "O", "O", " ", " ", " ", " "]
    obs, reward, done, info = await env.step(
        Action(llm_response="<Action>3</Action>")
    )
    state = env._state
    assert state["board"] == ["X", "X", "X", "O", "O", " ", " ", " ", " "]
    assert state["game_over"] is True
    assert state["winner"] == "X"
    assert reward == 1.0
    assert done is True
    assert "Congratulations, you won!" in obs.question
    await env.close()


@pytest.mark.asyncio
async def test_opponent_wins():
    """Test opponent winning after agent's move."""
    env = TicTacToeEnv()
    await env.setup()
    await env.reset()
    env._state["board"] = ["O", " ", "O", "X", "X", " ", " ", " ", " "]
    obs, reward, done, info = await env.step(
        Action(llm_response="<Action>7</Action>")
    )
    state = env._state
    # The opponent should play optimally to win.
    assert state["board"][1] == "O"  # Opponent places 'O' to win
    assert state["game_over"] is True
    assert state["winner"] == "O"
    assert reward == 0.0
    assert done is True
    assert "Sorry, you lost!" in obs.question
    await env.close()


@pytest.mark.asyncio
async def test_draw():
    """Test a draw."""
    env = TicTacToeEnv()
    await env.setup()
    await env.reset()
    env._state["board"] = ["X", "O", "X", "O", "O", "X", "X", " ", "O"]
    obs, reward, done, info = await env.step(
        Action(llm_response="<Action>8</Action>")
    )
    state = env._state
    assert state["board"] == ["X", "O", "X", "O", "O", "X", "X", "X", "O"]
    assert state["game_over"] is True
    assert state["winner"] == "draw"
    assert reward == 0.5
    assert done is True
    assert "It's a draw!" in obs.question
    await env.close()


# --- Helper Method Tests ---


def test_helper_methods():
    """Test render_board, check_winner, and available_moves."""
    env = TicTacToeEnv()
    # Test render_board
    board = ["X", "O", " ", " ", "X", " ", " ", " ", "O"]
    expected_board = "X | O | 3\n---------\n4 | X | 6\n---------\n7 | 8 | O"
    assert env.render_board(board) == expected_board
    # Test check_winner
    assert (
        TicTacToeEnv.check_winner(
            ["X", "X", "X", "O", "O", " ", " ", " ", " "]
        )
        == "X"
    )
    assert (
        TicTacToeEnv.check_winner(
            ["O", " ", " ", "O", " ", " ", "O", " ", " "]
        )
        == "O"
    )
    assert (
        TicTacToeEnv.check_winner(
            ["X", "O", "X", "X", "O", "O", "O", "X", "X"]
        )
        == "draw"
    )
    assert (
        TicTacToeEnv.check_winner(
            ["X", "O", " ", " ", " ", " ", " ", " ", " "]
        )
        is None
    )
    # Test available_moves
    assert TicTacToeEnv.available_moves(board) == [2, 3, 5, 6, 7]


# --- Opponent Class Tests ---


def test_opponent_move_and_minimax():
    """Test opponent move and minimax algorithm directly
    from Opponent class."""
    opponent = Opponent(play_style="optimal")
    board = ["X", "X", " ", " ", "O", " ", " ", " ", " "]
    # The optimal move should be index 2 (blocking X's win).
    assert opponent.select_move(board) == 2
    score, move = opponent.minimax(board, is_maximizing=False)
    assert score == -1
    assert move == 2


def test_opponent_random_move():
    """Test that a random opponent move is within the available moves."""
    opponent = Opponent(play_style="random")
    board = ["X", "O", " ", " ", "X", " ", " ", " ", " "]
    available = TicTacToeEnv.available_moves(board)
    move = opponent.select_move(board)
    assert move in available


def test_opponent_no_moves():
    """Test that when no moves are available, the opponent returns None."""
    opponent = Opponent(play_style="optimal")
    board = ["X", "O", "X", "X", "O", "O", "O", "X", "X"]
    move = opponent.select_move(board)
    assert move is None


def test_opponent_optimal_winning_move():
    """Test that the optimal opponent identifies and makes a winning move,
    if available."""
    opponent = Opponent(play_style="optimal")
    # Set up a board where O can win immediately (row 0: two O's and an empty).
    board = ["O", "O", " ", "X", "X", " ", " ", " ", " "]
    move = opponent.select_move(board)
    # The winning move is index 2.
    assert move == 2


def test_minimax_draw_scenario():
    """Test that minimax returns a draw score for a board leading to a draw."""
    opponent = Opponent(play_style="optimal")
    # A nearly complete board with one move left that results in a draw.
    board = ["X", "O", "X", "X", "O", "O", "O", "X", " "]
    score, move = opponent.minimax(board, is_maximizing=True)
    # Only one move is available; playing it leads to a draw.
    assert score == 0
    # The only available move should be index 8.
    assert move == 8


# --- Error Handling Tests ---


@pytest.mark.asyncio
async def test_step_errors():
    """Test errors for stepping without setup, after done, or without reset."""
    # Without setup
    env = TicTacToeEnv()
    with pytest.raises(RuntimeError, match="Environment not set up"):
        await env.step(Action(llm_response="<Action>5</Action>"))

    env = TicTacToeEnv()
    await env.setup()
    await env.reset()
    env._episode_ended = True
    with pytest.raises(RuntimeError, match="Episode has ended"):
        await env.step(Action(llm_response="<Action>5</Action>"))
    await env.close()

    env = TicTacToeEnv()
    await env.setup()
    env._last_observation = None  # Simulate no reset
    with pytest.raises(RuntimeError, match="No current observation"):
        await env.step(Action(llm_response="<Action>5</Action>"))
    await env.close()


# --- Full test ---
@pytest.mark.asyncio
async def test_full_game():
    """Test a full game sequence with intermediate reward shaping."""
    env = TicTacToeEnv()
    await env.setup()
    await env.reset()

    moves = ["1", "2", "4"]
    for move in moves:
        obs, reward, done, info = await env.step(
            Action(llm_response=f"<Action>{move}</Action>")
        )
        if done:
            winner = env._state["winner"]
            if winner == "X":
                assert reward == 1.0
            elif winner == "O":
                assert reward == 0.0
            elif winner == "draw":
                assert reward == 0.5
        else:
            # NEW: Validate reward matches optimal X evaluation
            expected = TicTacToeEnv.evaluate_position_for_x(
                env._state["board"], is_x_turn=True
            )
            assert reward == expected
            assert 0.0 <= reward <= 1.0
            assert done is False

    await env.close()
