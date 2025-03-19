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
import re
from typing import Any, ClassVar, Dict, List, Optional, Tuple

from camel.environments.models import Action, Observation
from camel.environments.multi_step import MultiStepEnv
from camel.extractors import BaseExtractor, BaseExtractorStrategy


class ActionParser(BaseExtractorStrategy):
    async def extract(self, text: str) -> Optional[str]:
        match = re.search(r"<Action>(\d)", text)
        if match:
            return match.group(1)
        return None


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

    async def _setup(self) -> None:
        if self._is_setup:
            return
        await self.extractor.setup()

    async def _close(self) -> None:
        await self.extractor.cleanup()

    def _get_initial_state(self) -> Dict[str, Any]:
        # State includes the board (9 cells), game_over flag, and winner info.
        return {
            "board": [" " for _ in range(9)],
            "game_over": False,
            "winner": None,
        }

    # TODO: simplify, give feedback if fails
    async def _update_state(self, action: Action) -> None:
        board = self._state["board"]

        # Attempt to parse the agent's chosen move
        extraction_result = await self.extractor.extract(action.llm_response)
        if not extraction_result:
            raise ValueError(
                f"Couldn't extract anything from {action.llm_response}"
            )

        try:
            move = int(extraction_result)
        except ValueError:
            raise ValueError(
                f"Extraction result '{extraction_result}' is not a valid move"
            )

        # Convert 1-indexed move to 0-indexed board position.
        index = move - 1
        if index < 0 or index > 8 or board[index] != " ":
            # Illegal move: losing condition.
            # TODO: give feedback instead of autoloss
            self._state["game_over"] = True
            self._state["winner"] = "O"
            return

        # Agent (X) makes the move.
        board[index] = "X"

        # Check if agent wins (or draw) right after its move.
        winner = self.check_winner(board)
        if winner is not None:
            self._state["game_over"] = True
            self._state["winner"] = winner
            return

        # Opponent (O) plays optimally.
        opponent_move = self.get_opponent_move(board)
        if opponent_move is not None:
            board[opponent_move] = "O"

        # Check if the game ended after opponent's move.
        winner = self.check_winner(board)
        if winner is not None:
            self._state["game_over"] = True
            self._state["winner"] = winner

    def _get_next_observation(self) -> Observation:
        board = self._state["board"]
        obs = (
            "You are playing Tic Tac Toe with standard rules."
            "You are the player with X."
            "Choose a number between 1 and 9 to place an X.\n"
            "This is the current state of the board:\n"
            f"{self.render_board(board)}"
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
        if not self._state["game_over"]:
            return 0.0, {"ongoing": 0.0}
        else:
            if self._state["winner"] == "X":
                return 1.0, {"win": 1.0}
            elif self._state["winner"] == "O":
                return -1.0, {"loss": -1.0}
            else:
                return 0.0, {"draw": 0.0}

    def _is_done(self) -> bool:
        return self._state["game_over"]

    def render_board(self, board: List[str]) -> str:
        # Create a nice formatted board.
        def cell_value(i: int) -> str:
            return board[i] if board[i] != " " else str(i + 1)

        rows = []
        for i in range(0, 9, 3):
            row = " | ".join(cell_value(j) for j in range(i, i + 3))
            rows.append(row)
        return "\n---------\n".join(rows)

    def check_winner(self, board: List[str]) -> Optional[str]:
        # Check all win combinations.
        for a, b, c in self.WIN_COMBINATIONS:
            if board[a] != " " and board[a] == board[b] == board[c]:
                return board[a]
        # Check for draw.
        if all(cell != " " for cell in board):
            return "draw"
        return None

    def available_moves(self, board: List[str]) -> List[int]:
        # Return list of indices that are free.
        return [i for i, cell in enumerate(board) if cell == " "]

    def get_opponent_move(self, board: List[str]) -> Optional[int]:
        moves = self.available_moves(board)
        if not moves:
            return None
        # Use minimax to choose the optimal move for O.
        _, move = self.minimax(board, is_maximizing=True)
        return move

    def minimax(
        self, board: List[str], is_maximizing: bool
    ) -> Tuple[float, Optional[int]]:
        winner = self.check_winner(board)
        if winner == "O":
            return (1, None)
        elif winner == "X":
            return (-1, None)
        elif winner == "draw":
            return (0, None)

        moves = self.available_moves(board)
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
