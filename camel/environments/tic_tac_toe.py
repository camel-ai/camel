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


class ActionParser(BaseExtractorStrategy):
    async def extract(self, text: str) -> Optional[str]:
        match = re.search(r"<Action>\s*(\d+)", text)
        if match:
            return match.group(1)
        return None


class Opponent:
    def __init__(self, play_style: Literal["optimal", "random"]) -> None:
        self.play_style = play_style

    def select_move(self, board: List[str]) -> Optional[int]:
        if self.play_style == "optimal":
            return self.get_optimal_move(board)
        elif self.play_style == "random":
            moves = TicTacToeEnv.available_moves(board)
            if not moves:
                raise RuntimeError("No valid moves left.")
            return random.choice(moves)

    def get_optimal_move(self, board: List[str]) -> Optional[int]:
        _, move = self.minimax(board, is_maximizing=True)
        return move

    def minimax(
        self, board: List[str], is_maximizing: bool
    ) -> Tuple[float, Optional[int]]:
        winner = TicTacToeEnv.check_winner(board)
        if winner == "O":
            return (1, None)
        elif winner == "X":
            return (-1, None)
        elif winner == "draw":
            return (0, None)

        moves = TicTacToeEnv.available_moves(board)
        if is_maximizing:
            best_score = -math.inf
            best_move = None
            for move in moves:
                board[move] = "O"
                score, _ = self.minimax(board, is_maximizing=False)
                board[move] = " "
                if score > best_score:
                    best_score = score
                    best_move = move
            return best_score, best_move
        else:
            best_score = math.inf
            best_move = None
            for move in moves:
                board[move] = "X"
                score, _ = self.minimax(board, is_maximizing=True)
                board[move] = " "
                if score < best_score:
                    best_score = score
                    best_move = move
            return best_score, best_move


class TicTacToeEnv(MultiStepEnv):
    WIN_COMBINATIONS: ClassVar = [
        (0, 1, 2),
        (3, 4, 5),
        (6, 7, 8),
        (0, 3, 6),
        (1, 4, 7),
        (2, 5, 8),
        (0, 4, 8),
        (2, 4, 6),
    ]

    def __init__(self, **kwargs) -> None:
        extractor = BaseExtractor(pipeline=[[ActionParser()]])
        super().__init__(extractor, None, **kwargs)
        # Add an opponent instance to the environment.
        self.opponent = Opponent(play_style="optimal")

    def _get_initial_state(self) -> Dict[str, Any]:
        # State includes the board (9 cells), game_over flag, and winner info.
        return {
            "board": [" " for _ in range(9)],
            "game_over": False,
            "winner": None,
            "last_move_illegal": False,
        }

    async def _update_state(self, action: Action) -> None:
        board = self._state["board"]

        # Attempt to parse the agent's chosen move
        extraction_result = await self.extractor.extract(action.llm_response)
        if not extraction_result:
            # TODO: we should catch that error and create an observation
            # giving feedback
            raise ValueError(
                f"Couldn't extract anything from {action.llm_response}"
            )

        try:
            move = int(extraction_result)
            self._state["last_move"] = move
        except ValueError:
            # TODO: we should catch that error and create an
            # observation giving feedback
            raise ValueError(
                f"Extraction result '{extraction_result}' is not a valid move"
            )

        # Convert 1-indexed move to 0-indexed board position.
        index = move - 1
        if index < 0 or index > 8 or board[index] != " ":
            self._state["last_move_illegal"] = True
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
                f"{self.render_board(board)}"
                "Each number that you can see is still an empty field"
                "that you can place your 'X' in. Please end your response with"
                "<Action> [a number from 1 to 9]"
            )
        else:
            obs = (
                "You are playing Tic Tac Toe with standard rules.\n"
                "You are the player with X.\n"
                "Choose a number between 1 and 9 to place an X.\n"
                "This is the current state of the board:\n"
                f"{self.render_board(board)}\n"
                "Each number that you can see is still an empty field"
                "that you can place your 'X' in. Please end your response with"
                "<Action> [a number from 1 to 9]"
            )

        return Observation(question=obs, context={}, metadata={})

    def _get_terminal_observation(self) -> Observation:
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
        # Simple reward: 1 for win, -1 for loss, 0 for draw or ongoing.
        if self._state["game_over"]:
            if self._state["winner"] == "X":
                return 1.0, {"win": 1.0}
            elif self._state["winner"] == "O":
                return 0.0, {"loss": 0.0}
            else:
                return 0.5, {"draw": 0.5}
        else:
            # Look ahead: simulate all outcomes from this state
            # with optimal play
            board = self._state["board"]
            x_win_count, total_leaves = self._count_x_winning_paths(
                board, is_x_turn=True
            )

            if total_leaves == 0:
                reward = 0.0
            else:
                reward = x_win_count / total_leaves

            return reward, {
                "x_winning_paths": float(x_win_count),
                "total_paths": float(total_leaves),
                "estimated_win_rate": reward,
            }

    def _count_x_winning_paths(
        self, board: List[str], is_x_turn: bool
    ) -> Tuple[int, int]:
        winner = self.check_winner(board)
        if winner == "X":
            return 1, 1
        elif winner in ("O", "draw"):
            return 0, 1

        moves = TicTacToeEnv.available_moves(board)
        x_wins = 0
        total = 0

        for move in moves:
            board[move] = "X" if is_x_turn else "O"
            wins, paths = self._count_x_winning_paths(board, not is_x_turn)
            board[move] = " "
            total += paths

            # If it's X's turn, accumulate winning futures
            # If it's O's turn, they play optimally, so minimize X's wins
            if is_x_turn:
                x_wins += wins
            else:
                # O will *force* the path with the fewest X wins
                # Only keep the *minimum* winning path seen
                if total == paths:  # first branch
                    x_wins = wins
                else:
                    x_wins = min(x_wins, wins)

        return x_wins, total

    def _is_done(self) -> bool:
        return self._state["game_over"]

    @staticmethod
    def available_moves(board: List[str]) -> List[int]:
        # Return list of indices that are free.
        return [i for i, cell in enumerate(board) if cell == " "]

    @staticmethod
    def check_winner(board: List[str]) -> Optional[str]:
        # Check all win combinations.
        for a, b, c in TicTacToeEnv.WIN_COMBINATIONS:
            if board[a] != " " and board[a] == board[b] == board[c]:
                return board[a]
        # Check for draw.
        if all(cell != " " for cell in board):
            return "draw"
        return None

    def render_board(self, board: List[str]) -> str:
        # Create a nice formatted board.
        def cell_value(i: int) -> str:
            return board[i] if board[i] != " " else str(i + 1)

        rows = []
        for i in range(0, 9, 3):
            row = " | ".join(cell_value(j) for j in range(i, i + 3))
            rows.append(row)
        return "\n---------\n".join(rows)
