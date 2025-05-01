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

import re
from typing import Any, Dict, List, Optional, Tuple, Union

from camel.environments.models import Action, Observation
from camel.environments.rlcards_env import RLCardsEnv
from camel.extractors import BaseExtractor
from camel.logger import get_logger

logger = get_logger(__name__)


class DoudizhuEnv(RLCardsEnv):
    r"""A Doudizhu environment for reinforcement learning with LLMs.

    This environment implements a standard Doudizhu game where the LLM agent
    plays against two AI opponents.
    """

    def __init__(
        self,
        extractor: Optional[BaseExtractor] = None,
        max_steps: Optional[int] = None,
        **kwargs,
    ) -> None:
        r"""Initialize the Doudizhu environment.

        Args:
            extractor (Optional[BaseExtractor]): Extractor to process LLM
                responses. If None, a default extractor will be used.
                (default: :obj:`None`)
            max_steps (Optional[int]): Maximum steps per episode.
                (default: :obj:`None`)
            **kwargs: Additional environment parameters.
        """
        super().__init__("doudizhu", extractor, max_steps, num_players=3, **kwargs)

    def _convert_to_rlcard_action(self, action_str: str) -> str:
        r"""Convert a string action to the format expected by RLCard Doudizhu.

        Args:
            action_str (str): The string representation of the action.
                Expected to be a card combination or 'pass'.

        Returns:
            str: The action string in the format expected by RLCard.
        """
        action_str = action_str.lower().strip()
        if action_str == "pass":
            return "pass"
        
        # For card combinations, we need to convert them to the RLCard format
        # This is a simplified implementation and might need to be adjusted
        # based on the exact format expected by RLCard
        
        # Remove spaces and convert to uppercase for consistency
        action_str = action_str.replace(" ", "").upper()
        
        # Check if the action is in the legal actions
        if action_str in self._state["legal_actions"]:
            return action_str
        
        return None

    def _format_state_for_observation(self, state: Dict[str, Any]) -> str:
        r"""Format the Doudizhu state for human-readable observation.

        Args:
            state (Dict[str, Any]): The RLCard state dictionary.

        Returns:
            str: A human-readable representation of the state.
        """
        if state is None:
            return "Game not started yet."

        # Extract state information
        raw_obs = state['raw_obs']
        current_hand = raw_obs['current_hand']
        played_cards = raw_obs['played_cards']
        landlord = raw_obs['landlord']
        landlord_up_played_cards = raw_obs['landlord_up_played_cards']
        landlord_down_played_cards = raw_obs['landlord_down_played_cards']
        landlord_played_cards = raw_obs['landlord_played_cards']
        bomb_num = raw_obs['bomb_num']
        
        # Format the observation
        obs_text = ""
        
        # Player role
        if landlord == 0:
            obs_text += "You are the Landlord.\n"
        else:
            obs_text += f"You are a Peasant. Player {landlord} is the Landlord.\n"
        
        # Current hand
        obs_text += f"Your hand: {self._format_cards(current_hand)}\n"
        
        # Last played cards by each player
        obs_text += "Last played cards:\n"
        if landlord == 0:
            obs_text += f"  You (Landlord): {self._format_cards(landlord_played_cards)}\n"
            obs_text += f"  Peasant 1: {self._format_cards(landlord_up_played_cards)}\n"
            obs_text += f"  Peasant 2: {self._format_cards(landlord_down_played_cards)}\n"
        elif landlord == 1:
            obs_text += f"  You: {self._format_cards(landlord_down_played_cards if landlord == 2 else landlord_up_played_cards)}\n"
            obs_text += f"  Landlord: {self._format_cards(landlord_played_cards)}\n"
            obs_text += f"  Other Peasant: {self._format_cards(landlord_up_played_cards if landlord == 2 else landlord_down_played_cards)}\n"
        else:  # landlord == 2
            obs_text += f"  You: {self._format_cards(landlord_up_played_cards if landlord == 1 else landlord_down_played_cards)}\n"
            obs_text += f"  Landlord: {self._format_cards(landlord_played_cards)}\n"
            obs_text += f"  Other Peasant: {self._format_cards(landlord_down_played_cards if landlord == 1 else landlord_up_played_cards)}\n"
        
        # Bomb count
        obs_text += f"Number of bombs played: {bomb_num}\n"
        
        return obs_text

    def _format_legal_actions(self, legal_actions: List[str]) -> str:
        r"""Format the legal actions for Doudizhu.

        Args:
            legal_actions (List[str]): The list of legal actions.

        Returns:
            str: A human-readable representation of the legal actions.
        """
        # For simplicity, we'll just list the first few legal actions if there are many
        if len(legal_actions) > 10:
            action_str = ", ".join(legal_actions[:10]) + f" and {len(legal_actions) - 10} more options"
        else:
            action_str = ", ".join(legal_actions)
        
        return action_str

    def _format_cards(self, cards: List[str]) -> str:
        r"""Format a list of cards for display.

        Args:
            cards (List[str]): List of card strings.

        Returns:
            str: Formatted card string.
        """
        if not cards:
            return "None"
        return " ".join(cards)