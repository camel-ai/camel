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
import math
import random
import re
from typing import Any, ClassVar, Dict, List, Literal, Optional, Tuple

from camel.environments.models import Action, Observation
from camel.environments.multi_step import MultiStepEnv
from camel.extractors import BaseExtractor, BaseExtractorStrategy


class MoveExtractor(BaseExtractorStrategy):
    r"""A strategy for extracting Tic Tac Toe actions from text."""

    async def extract(self, text: str) -> Optional[str]:
        r"""Extract a valid Tic Tac Toe move from text.

        Looks for a pattern '<Action> n' where n is a digit between 1 and 9.

        Args:
            text (str): The text to extract the action from.

        Returns:
            Optional[str]: The extracted move as a string, or None if no valid
                move is found.
        """
        match = re.search(r"<Action>\s*(\d+)", text)
        if match:
            move = match.group(1)
            # Validate that the move is in range 1-9
            if move.isdigit() and 1 <= int(move) <= 9:
                return move
        return None


class Opponent:
    r"""AI opponent for the Tic Tac Toe game.

    This class implements different playing strategies for the AI opponent,
    including an optimal strategy using the minimax algorithm with alpha-beta
    pruning, and a random strategy.
    """

    def __init__(
        self, play_style: Literal["optimal", "random"] = "optimal"
    ) -> None:
        r"""Initialize the opponent with a specific play style.

        Args:
            play_style (Literal["optimal", "random"]): The strategy to use,
                either "optimal" or "random". (default: :obj:`"optimal"`)
        """
        self.play_style = play_style

    def select_move(self, board: List[str]) -> Optional[int]:
        r"""Select a move based on the opponent's play style.

        Args:
            board (List[str]): The current game board as a list of strings.

        Returns:
            Optional[int]: The index of the selected move, or None if no move
                is available.
        """
        if self.play_style == "optimal":
            return self.get_optimal_move(board)
        elif self.play_style == "random":
            moves = TicTacToeEnv.available_moves(board)
            if not moves:
                return None  # Consistent with optimal strategy
            return random.choice(moves)

    def get_optimal_move(self, board: List[str]) -> Optional[int]:
        r"""Get the optimal move using the minimax algorithm.

        Args:
            board (List[str]): The current game board as a list of strings.

        Returns:
            Optional[int]: The index of the optimal move, or None if no move
                is available.
        """
        _, move = self.minimax(board, is_maximizing=True)
        return move

    def minimax(
        self,
        board: List[str],
        is_maximizing: bool,
        depth: int = 0,
        alpha: float = -math.inf,
        beta: float = math.inf,
    ) -> Tuple[float, Optional[int]]:
        r"""Minimax algorithm with alpha-beta pruning for optimal move
        selection.

        Recursively evaluates all possible moves to find the best one.
        Uses alpha-beta pruning to reduce the search space.

        Args:
            board (List[str]): The current game board as a list of strings.
            is_maximizing (bool): True if maximizing player (O), False if
                minimizing (X).
            depth (int): Current depth in the search tree. (default: :obj:`0`)
            alpha (float): Alpha value for pruning. (default: :obj:`-math.inf`)
            beta (float): Beta value for pruning. (default: :obj:`math.inf`)

        Returns:
            Tuple[float, Optional[int]]: A tuple containing:
                - float: The score of the best move (1 for O win, -1 for X
                    win, 0 for draw)
                - Optional[int]: The index of the best move, or None if
                    terminal state
        """
        winner = TicTacToeEnv.check_winner(board)
        if winner == "O":
            return (1, None)
        elif winner == "X":
            return (-1, None)
        elif winner == "draw":
            return (0, None)

        moves = TicTacToeEnv.available_moves(board)
        # Add depth limit to prevent stack overflow (9 is max depth for
        # tic-tac-toe)
        if depth >= 9:
            # Evaluate current position
            return (0, None)

        if is_maximizing:
            best_score = -math.inf
            best_move = None
            for move in moves:
                board[move] = "O"
                score, _ = self.minimax(
                    board,
                    is_maximizing=False,
                    depth=depth + 1,
                    alpha=alpha,
                    beta=beta,
                )
                board[move] = " "
                if score > best_score:
                    best_score = score
                    best_move = move
                alpha = max(alpha, best_score)
                if beta <= alpha:
                    break  # Beta cutoff
            return best_score, best_move
        else:
            best_score = math.inf
            best_move = None
            for move in moves:
                board[move] = "X"
                score, _ = self.minimax(
                    board,
                    is_maximizing=True,
                    depth=depth + 1,
                    alpha=alpha,
                    beta=beta,
                )
                board[move] = " "
                if score < best_score:
                    best_score = score
                    best_move = move
                beta = min(beta, best_score)
                if beta <= alpha:
                    break  # Alpha cutoff
            return best_score, best_move


class TicTacToeEnv(MultiStepEnv):
    r"""A Tic Tac Toe environment for reinforcement learning with LLMs.

    This environment implements a standard Tic Tac Toe game where the LLM agent
    plays as 'X' against an AI opponent that plays as 'O'. The opponent can use
    either an optimal strategy (minimax with alpha-beta pruning) or a random
    strategy.
    """

    WIN_COMBINATIONS: ClassVar = [
        (0, 1, 2),  # Top row
        (3, 4, 5),  # Middle row
        (6, 7, 8),  # Bottom row
        (0, 3, 6),  # Left column
        (1, 4, 7),  # Middle column
        (2, 5, 8),  # Right column
        (0, 4, 8),  # Diagonal from top-left
        (2, 4, 6),  # Diagonal from top-right
    ]

    def __init__(
        self,
        extractor: Optional[BaseExtractor] = None,
        max_steps: Optional[int] = None,
        play_style: Literal["optimal", "random"] = "optimal",
        **kwargs,
    ) -> None:
        r"""Initialize the Tic Tac Toe environment.

        Args:
            extractor (Optional[BaseExtractor]): Extractor to process LLM
                responses. If None, a default extractor with
                MoveExtractor will be used. (default: :obj:`None`)
            max_steps (Optional[int]): Maximum steps per episode.
                (default: :obj:`None`)
            play_style (Literal["optimal", "random"]): The strategy for the
                opponent to use, either "optimal" or "random". (default:
                :obj:`"optimal"`)
            **kwargs: Additional environment parameters.
        """
        if extractor is None:
            extractor = BaseExtractor(pipeline=[[MoveExtractor()]])
        super().__init__(extractor, max_steps, **kwargs)
        self.opponent = Opponent(play_style=play_style)

    def _get_initial_state(self) -> Dict[str, Any]:
        r"""Get the initial state of the environment.

        Returns:
            Dict[str, Any]: A dictionary containing the initial state with an
                empty board, game status flags, and move history.
        """
        # State includes the board (9 cells), game_over flag, and winner info.
        return {
            "board": [" " for _ in range(9)],
            "game_over": False,
            "winner": None,
            "last_move_illegal": False,
            "last_move": None,
        }

    async def _update_state(self, action: Action) -> None:
        r"""Update the environment state based on the agent's action.

        This method processes the agent's move, updates the board, checks for
        a winner, and if the game is not over, makes a move for the opponent.

        Args:
            action (Action): The action containing the LLM's response with the
                chosen move.

        Returns:
            None
        """
        board = self._state["board"]

        # Attempt to parse the agent's chosen move
        extraction_result = await self.extractor.extract(action.llm_response)
        if not extraction_result:
            # Handle extraction failure gracefully
            self._state["last_move_illegal"] = True
            self._state["last_move"] = None
            self._state["extraction_error"] = "Could not extract a valid move"
            return

        try:
            move = int(extraction_result)
            self._state["last_move"] = move
            self._state["extraction_error"] = None
        except ValueError:
            # Handle invalid move format gracefully
            self._state["last_move_illegal"] = True
            self._state["last_move"] = extraction_result
            self._state["extraction_error"] = (
                f"'{extraction_result}' is not a valid number"
            )
            return

        # Convert 1-indexed move to 0-indexed board position.
        index = move - 1
        if index < 0 or index > 8 or board[index] != " ":
            self._state["last_move_illegal"] = True
            self._state["extraction_error"] = (
                f"Position {move} is not a valid or available move"
            )
            return

        # Reset the flag
        self._state["last_move_illegal"] = False

        # Agent (X) makes the move.
        board[index] = "X"

        # Check if agent wins (or draw) right after its move.
        winner = self.check_winner(board)
        if winner is not None:
            self._state["game_over"] = True
            self._state["winner"] = winner
            return

        # Opponent (O) plays using the opponent class.
        opponent_move = self.opponent.select_move(board)
        if opponent_move is not None:
            board[opponent_move] = "O"

        # Check if the game ended after opponent's move.
        winner = self.check_winner(board)
        if winner is not None:
            self._state["game_over"] = True
            self._state["winner"] = winner

    def _get_next_observation(self) -> Observation:
        r"""Get the next observation based on the current state.

        This method generates a text observation describing the current state
        of the game board and prompting the agent to make a move.

        Returns:
            Observation: An Observation object containing the game state
                description.
        """
        board = self._state["board"]
        if self._state["last_move_illegal"]:
            obs = (
                "You are playing Tic Tac Toe with standard rules.\n"
                "You are the player with X.\n"
                "Your last move was illegal.\n"
                f"You chose the move {self._state['last_move']}."
                "Choose another number between 1 and 9 to place an X.\n"
                "The field must still be available.\n"
                "This is the current state of the board:\n"
                f"{self.render_board(board)}\n"
                "Each number that you can see is still an empty field "
                "that you can place your 'X' in. Please end your response "
                "with <Action> [a number from 1 to 9]"
            )
        else:
            obs = (
                "You are playing Tic Tac Toe with standard rules.\n"
                "You are the player with X.\n"
                "Choose a number between 1 and 9 to place an X.\n"
                "This is the current state of the board:\n"
                f"{self.render_board(board)}\n"
                "Each number that you can see is still an empty field "
                "that you can place your 'X' in. Please end your response "
                "with <Action> [a number from 1 to 9]"
            )

        return Observation(question=obs, context={}, metadata={})

    def _get_terminal_observation(self) -> Observation:
        r"""Get the final observation when the game is over.

        This method generates a text observation describing the final state
        of the game board and the game result (win, loss, or draw).

        Returns:
            Observation: An Observation object containing the final game state
                description.
        """
        board = self._state["board"]
        result_message = ""
        if self._state["winner"] == "X":
            result_message = "Congratulations, you won!"
        elif self._state["winner"] == "O":
            result_message = "Sorry, you lost!"
        else:
            result_message = "It's a draw!"

        obs = f"{self.render_board(board)}\nGame Over. {result_message}"

        return Observation(question=obs, context={}, metadata={})

    async def compute_reward(self) -> Tuple[float, Dict[str, float]]:
        r"""Compute the reward for the current state.

        Returns:
            Tuple[float, Dict[str, float]]: A tuple containing the total
                reward and a dictionary of reward components:
                - 1.0 for a win
                - 0.0 for a loss or illegal move
                - 0.5 for a draw
                - For ongoing games, returns an evaluation of the position
        """
        # Simple reward: 1 for win, 0 for loss, 0.5 for draw or ongoing.
        if self._state["game_over"]:
            if self._state["winner"] == "X":
                return 1.0, {"win": 1.0}
            elif self._state["winner"] == "O":
                return 0.0, {"loss": 0.0}
            else:
                return 0.5, {"draw": 0.5}

        elif self._state["last_move_illegal"]:
            return 0.0, {"illegal_move": 0.0}

        else:
            board = self._state["board"]
            value = TicTacToeEnv.evaluate_position_for_x(board, is_x_turn=True)
            return value, {"x_non_loss_value": value}

    @staticmethod
    def evaluate_position_for_x(
        board: List[str], is_x_turn: bool, depth: int = 0, max_depth: int = 10
    ) -> float:
        r"""Evaluate the current board position from X's perspective.

        Uses minimax to determine the value of the position.

        Args:
            board (List[str]): The current game board as a list of strings.
            is_x_turn (bool): True if it's X's turn to move, False otherwise.

        Returns:
            float: A float value representing the position evaluation:
                - 1.0 if X has a winning position
                - 0.0 if O has a winning position
                - 0.5 for a draw
                - For ongoing positions, returns the expected outcome with
                    perfect play
        """
        winner = TicTacToeEnv.check_winner(board)
        if winner == "X":
            return 1.0  # X wins
        elif winner == "O":
            return 0.0  # X loses
        elif winner == "draw":
            return 0.5  # draw

        # Add depth limit to prevent potential stack overflow
        if depth >= max_depth:
            return 0.5  # Return draw evaluation at max depth

        moves = TicTacToeEnv.available_moves(board)
        values = []
        # Create a copy of the board to avoid side effects
        for move in moves:
            board_copy = board.copy()
            board_copy[move] = "X" if is_x_turn else "O"
            value = TicTacToeEnv.evaluate_position_for_x(
                board_copy, not is_x_turn, depth + 1, max_depth
            )
            values.append(value)

        return max(values) if is_x_turn else min(values)

    def _is_done(self) -> bool:
        r"""Check if the episode is done.

        Returns:
            True if the game is over, False otherwise.
        """
        return self._state["game_over"]

    @staticmethod
    def available_moves(board: List[str]) -> List[int]:
        r"""Get all available moves on the board.

        Args:
            board (List[str]): The current game board as a list of strings.

        Returns:
            List[int]: A list of indices representing empty cells on the board.
        """
        # Return list of indices that are free.
        return [i for i, cell in enumerate(board) if cell == " "]

    @staticmethod
    def check_winner(board: List[str]) -> Optional[Literal["X", "O", "draw"]]:
        r"""Check if there is a winner or a draw on the board.

        Args:
            board (List[str]): The current game board as a list of strings.

        Returns:
            Optional[Literal["X", "O", "draw"]]: "X" if X has won, "O" if O
                has won, "draw" if the game is a draw, or None if the game is
                still ongoing.
        """
        # Check all win combinations.
        for a, b, c in TicTacToeEnv.WIN_COMBINATIONS:
            if board[a] != " " and board[a] == board[b] == board[c]:
                return board[a]
        # Check for draw.
        if all(cell != " " for cell in board):
            return "draw"
        return None

    def render_board(self, board: List[str]) -> str:
        r"""Render the board as a string for display.

        Args:
            board (List[str]): The current game board as a list of strings.

        Returns:
            str: A formatted string representation of the board.
        """

        # Create a nice formatted board.
        def cell_value(i: int) -> str:
            r"""Get the display value for a cell.

            Args:
                i (int): The index of the cell.

            Returns:
                str: The cell content ("X" or "O") or the cell number if empty.
            """
            return board[i] if board[i] != " " else str(i + 1)

        rows = []
        for i in range(0, 9, 3):
            row = " | ".join(cell_value(j) for j in range(i, i + 3))
            rows.append(row)
        return "\n---------\n".join(rows)
