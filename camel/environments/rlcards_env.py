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
from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from rlcard.agents import RandomAgent

from camel.environments.models import Action, Observation
from camel.environments.multi_step import MultiStepEnv
from camel.extractors import BaseExtractor, BaseExtractorStrategy
from camel.logger import get_logger

logger = get_logger(__name__)


class ActionExtractor(BaseExtractorStrategy):
    r"""A strategy for extracting RLCard actions from text."""

    def __init__(self, action_pattern: str = r"<Action>\s*(.+)") -> None:
        r"""Initialize the action extractor with a regex pattern.

        Args:
            action_pattern (str): The regex pattern to extract actions.
                (default: :obj:`"<Action>\\s*(.+)"`).
        """
        self.action_pattern = action_pattern

    async def extract(self, text: str) -> Optional[str]:
        r"""Extract a valid RLCard action from text.

        Looks for a pattern '<Action> action_str' where action_str is the
        string representation of the action.

        Args:
            text (str): The text to extract the action from.

        Returns:
            Optional[str]: The extracted action as a string, or None
                if no valid action is found.
        """
        match = re.search(self.action_pattern, text)
        if match:
            action_str = match.group(1).strip()
            return action_str
        return None


class RLCardsEnv(MultiStepEnv):
    r"""A base environment for RLCard games.

    This environment implements a wrapper around RLCard environments for
    reinforcement learning with LLMs. It handles the conversion between
    RLCard states and actions and the CAMEL environment interface.
    """

    def __init__(
        self,
        game_name: str,
        extractor: Optional[BaseExtractor] = None,
        max_steps: Optional[int] = None,
        num_players: int = 2,
        **kwargs,
    ) -> None:
        r"""Initialize the RLCard environment.

        Args:
            game_name (str): The name of the RLCard game to play.
            extractor (Optional[BaseExtractor]): Extractor to process LLM
                responses. If None, a default extractor with ActionExtractor
                will be used. (default: :obj:`None`)
            max_steps (Optional[int]): Maximum steps per episode.
                (default: :obj:`None`)
            num_players (int): Number of players in the game.
                (default: :obj:`2`)
            **kwargs: Additional environment parameters.
        """
        if extractor is None:
            extractor = BaseExtractor(pipeline=[[ActionExtractor()]])

        super().__init__(extractor, max_steps, **kwargs)

        self.game_name = game_name
        self.num_players = num_players
        self.rlcard_env = None
        self.current_player_id = None
        self.agents: Optional[List[Optional['RandomAgent']]] = None

    async def _setup(self) -> None:
        r"""Set up the RLCard environment.

        This method initializes the RLCard environment with the specified game
        and parameters.
        """
        import rlcard

        try:
            # Create the RLCard environment
            self.rlcard_env = rlcard.make(
                self.game_name,
                config={
                    'game_num_players': self.num_players,
                    'allow_step_back': True,
                    **self._metadata.get('rlcard_config', {}),
                },
            )

            from rlcard.agents import RandomAgent

            # Initialize random agents for opponents
            self.agents = [None] * self.num_players
            assert self.rlcard_env is not None

            for i in range(1, self.num_players):  # Skip player 0 (LLM agent)
                self.agents[i] = RandomAgent(
                    num_actions=self.rlcard_env.num_actions
                )

            logger.info(
                f"RLCard environment for {self.game_name} initialized "
                f"successfully"
            )
        except Exception as e:
            logger.error(f"Failed to initialize RLCard environment: {e}")
            raise

    async def _close(self) -> None:
        r"""Clean up the RLCard environment."""
        self.rlcard_env = None
        self.agents = None

    def _get_initial_state(self) -> Dict[str, Any]:
        r"""Get the initial state of the environment.

        Returns:
            Dict[str, Any]: A dictionary containing the initial state with
                game state, player info, and game status flags.
        """
        return {
            "rlcard_state": None,
            "legal_actions": [],
            "game_over": False,
            "winner": None,
            "payoffs": None,
            "last_action": None,
            "last_action_illegal": False,
            "extraction_error": None,
        }

    async def _update_state(self, action: Action) -> None:
        r"""Update the environment state based on the agent's action.

        This method processes the agent's action, updates the game state,
        and handles opponent moves if necessary.

        Args:
            action (Action): The action containing the LLM's response with the
                chosen move.
        """
        assert self.rlcard_env is not None

        if self._state["game_over"]:
            return

        # Extract action from LLM response
        extraction_result = await self.extractor.extract(action.llm_response)
        if not extraction_result:
            self._state["last_action_illegal"] = True
            self._state["extraction_error"] = (
                "Could not extract a valid action"
            )
            return

        # Convert extracted action to RLCard action format
        rlcard_action = self._convert_to_rlcard_action(extraction_result)
        if (
            rlcard_action is None
            or rlcard_action not in self._state["legal_actions"]
        ):
            self._state["last_action_illegal"] = True
            self._state["extraction_error"] = (
                f"'{extraction_result}' is not a valid action"
            )
            return

        # Reset illegal action flag
        self._state["last_action_illegal"] = False
        self._state["extraction_error"] = None
        self._state["last_action"] = extraction_result

        # Take the action in the environment
        next_state, self.current_player_id = self.rlcard_env.step(
            rlcard_action
        )

        # Update state with new information
        self._state["rlcard_state"] = next_state
        self._state["legal_actions"] = next_state['legal_actions'][
            self.current_player_id
        ]

        # Check if game is over
        if self.rlcard_env.is_over():
            self._state["game_over"] = True
            self._state["payoffs"] = self.rlcard_env.get_payoffs()
            # Determine winner based on payoffs
            payoffs = self._state["payoffs"]
            if payoffs[0] > 0:
                self._state["winner"] = "player"
            elif any(p > 0 for p in payoffs[1:]):
                self._state["winner"] = "opponent"
            else:
                self._state["winner"] = "draw"
            return

        # If next player is not the LLM agent (player 0), let opponents play
        while self.current_player_id != 0 and not self._state["game_over"]:
            # Get action from the corresponding agent
            agent_action = self.agents[self.current_player_id].eval_step(
                next_state
            )
            # Take the action
            next_state, self.current_player_id = self.rlcard_env.step(
                agent_action
            )

            # Update state
            self._state["rlcard_state"] = next_state
            if self.current_player_id == 0:  # Back to LLM agent
                self._state["legal_actions"] = next_state['legal_actions'][0]

            # Check if game is over after opponent's move
            if self.rlcard_env.is_over():
                self._state["game_over"] = True
                self._state["payoffs"] = self.rlcard_env.get_payoffs()
                # Determine winner based on payoffs
                payoffs = self._state["payoffs"]
                if payoffs[0] > 0:
                    self._state["winner"] = "player"
                elif any(p > 0 for p in payoffs[1:]):
                    self._state["winner"] = "opponent"
                else:
                    self._state["winner"] = "draw"

    def _get_next_observation(self) -> Observation:
        r"""Get the next observation based on the current state.

        This method generates a text observation describing the current state
        of the game and prompting the agent to make a move.

        Returns:
            Observation: An Observation object containing the game state
                description.
        """
        assert self.rlcard_env is not None

        if self._state["rlcard_state"] is None:
            # Initial observation before the game starts
            state, self.current_player_id = self.rlcard_env.reset()
            self._state["rlcard_state"] = state
            # Safely get legal actions, default to empty list if key
            # is missing or value is None
            legal_actions_dict = state.get('legal_actions', {})
            player_legal_actions = legal_actions_dict.get(
                self.current_player_id
            )
            self._state["legal_actions"] = (
                player_legal_actions
                if player_legal_actions is not None
                else []
            )

        # Generate observation text
        if self._state["last_action_illegal"]:
            # Safely retrieve last_action to prevent None value
            last_action = self._state.get("last_action", "None")
            error_msg = self._state.get("extraction_error", "Unknown error")

            inter_state_space = self._format_state_for_observation(
                self._state['rlcard_state']
            )
            inter_action_space = self._format_legal_actions(
                self._state['legal_actions']
            )
            obs_text = (
                f"You are playing {self.game_name}.\n"
                f"Your last action '{last_action}' was illegal.\n"
                f"Error: {error_msg}\n"
                f"Current game state:\n"
                f"{inter_state_space}\n"
                f"Legal actions: {inter_action_space}\n"
                f"Please choose an action and end your response with "
                f"<Action> [your action]"
            )
        else:
            inter_state_space = self._format_state_for_observation(
                self._state['rlcard_state']
            )
            inter_action_space = self._format_legal_actions(
                self._state['legal_actions']
            )
            obs_text = (
                f"You are playing {self.game_name}.\n"
                f"Current game state:\n"
                f"{inter_state_space}\n"
                f"Legal actions: {inter_action_space}\n"
                f"Please choose an action and end your response with "
                f"<Action> [your action]"
            )

        return Observation(
            question=obs_text,
            context={
                "game_name": self.game_name,
                "raw_state": self._state["rlcard_state"],
                "legal_actions": self._state["legal_actions"],
            },
            metadata={},
        )

    def _get_terminal_observation(self) -> Observation:
        r"""Get the final observation when the game is over.

        This method generates a text observation describing the final state
        of the game and the game result (win, loss, or draw).

        Returns:
            Observation: An Observation object containing the final game state
                description.
        """
        result_message = ""
        if self._state["winner"] == "player":
            result_message = "Congratulations, you won!"
        elif self._state["winner"] == "opponent":
            result_message = "Sorry, you lost!"
        else:
            result_message = "It's a draw!"

        # Safely handle errors to prevent errors caused by None type
        payoffs = self._state.get("payoffs", [])
        payoffs_str = (
            ", ".join([f"{p:.2f}" for p in payoffs]) if payoffs else "N/A"
        )

        obs_text = (
            f"Game Over. {result_message}\n"
            f"Final game state:\n"
            f"{self._format_state_for_observation(self._state['rlcard_state'])}\n"
            f"Payoffs: [{payoffs_str}]\n"
        )

        return Observation(
            question=obs_text,
            context={
                "game_name": self.game_name,
                "raw_state": self._state["rlcard_state"],
                "payoffs": self._state["payoffs"],
                "winner": self._state["winner"],
            },
            metadata={},
        )

    async def compute_reward(
        self,
    ) -> Tuple[float, Dict[str, float]]:
        r"""Compute the reward for the current state.

        Returns:
            Tuple[float, Dict[str, float]]: A tuple containing the total
                reward and a dictionary of reward components:
                - 1.0 for a win
                - 0.0 for a loss or illegal move
                - 0.5 for a draw
                - For ongoing games, returns a small step penalty
        """
        if self._state["game_over"]:
            if self._state["winner"] == "player":
                return 1.0, {"win": 1.0}
            elif self._state["winner"] == "opponent":
                return 0.0, {"loss": 0.0}
            else:
                return 0.5, {"draw": 0.5}
        elif self._state["last_action_illegal"]:
            return 0.0, {"illegal_move": 0.0}
        else:
            # Small negative reward for each step to encourage efficiency
            step_penalty = -0.01
            return step_penalty, {"step_penalty": step_penalty}

    def _is_done(self) -> bool:
        r"""Check if the episode is done.

        Returns:
            bool: True if the game is over, False otherwise.
        """
        return self._state["game_over"]

    @abstractmethod
    def _convert_to_rlcard_action(self, action_str: str) -> Any:
        r"""Convert a string action to the format expected by RLCard.

        This method must be implemented by subclasses to handle the specific
        action format of each game.

        Args:
            action_str (str): The string representation of the action.

        Returns:
            Any: The action in the format expected by the RLCard environment.
        """
        pass

    @abstractmethod
    def _format_state_for_observation(self, state: Dict[str, Any]) -> str:
        r"""Format the RLCard state for human-readable observation.

        This method must be implemented by subclasses to create a
        human-readable representation of the game state.

        Args:
            state (Dict[str, Any]): The RLCard state dictionary.

        Returns:
            str: A human-readable representation of the state.
        """
        pass

    @abstractmethod
    def _format_legal_actions(self, legal_actions: List[Any]) -> str:
        r"""Format the legal actions for human-readable observation.

        This method must be implemented by subclasses to create a
        human-readable representation of the legal actions.

        Args:
            legal_actions (List[Any]): The list of legal actions.

        Returns:
            str: A human-readable representation of the legal actions.
        """
        pass


class BlackjackEnv(RLCardsEnv):
    r"""A Blackjack environment for reinforcement learning with LLMs.

    This environment implements a standard Blackjack game where the LLM agent
    plays against a dealer.
    """

    def __init__(
        self,
        extractor: Optional[BaseExtractor] = None,
        max_steps: Optional[int] = None,
        **kwargs,
    ) -> None:
        r"""Initialize the Blackjack environment.

        Args:
            extractor (Optional[BaseExtractor]): Extractor to process LLM
                responses. If None, a default extractor will be used.
                (default: :obj:`None`)
            max_steps (Optional[int]): Maximum steps per episode.
                (default: :obj:`None`)
            **kwargs: Additional environment parameters.
        """
        super().__init__(
            "blackjack", extractor, max_steps, num_players=1, **kwargs
        )

    def _convert_to_rlcard_action(self, action_str: str) -> int:
        r"""Convert a string action to the format expected by RLCard Blackjack.

        Args:
            action_str (str): The string representation of the action.
                Expected to be 'hit' or 'stand'.

        Returns:
            int: 0 for 'hit', 1 for 'stand'.
        """
        action_str = action_str.lower().strip()
        if action_str == "hit":
            return 0
        elif action_str == "stand":
            return 1
        raise ValueError()

    def _format_state_for_observation(self, state: Dict[str, Any]) -> str:
        r"""Format the Blackjack state for human-readable observation.

        Args:
            state (Dict[str, Any]): The RLCard state dictionary.

        Returns:
            str: A human-readable representation of the state.
        """
        if state is None:
            return "Game not started yet."

        # Extract state information safely
        raw_obs = state.get('raw_obs', {})
        if raw_obs is None:
            raw_obs = {}
        player_hand = raw_obs.get('player', [])
        dealer_hand = raw_obs.get('dealer', [])

        # 确保player_hand和dealer_hand是列表
        if player_hand is None:
            player_hand = []
        if dealer_hand is None:
            dealer_hand = []

        # Format hands
        player_cards = self._format_cards(player_hand)
        dealer_cards = self._format_cards(dealer_hand)

        # Calculate hand values
        player_value = self._calculate_hand_value(player_hand)
        dealer_value = self._calculate_hand_value(dealer_hand)

        return (
            f"Your hand: {player_cards} (Value: {player_value})\n"
            f"Dealer's hand: {dealer_cards} (Value: {dealer_value})"
        )

    def _format_legal_actions(self, legal_actions: List[int]) -> str:
        r"""Format the legal actions for Blackjack.

        Args:
            legal_actions (List[int]): The list of legal actions.

        Returns:
            str: A human-readable representation of the legal actions.
        """
        if not legal_actions:
            return "No legal actions available"

        action_map = {0: "hit", 1: "stand"}
        return ", ".join([action_map.get(a, str(a)) for a in legal_actions])

    def _format_cards(self, cards: List[str]) -> str:
        r"""Format a list of cards for display.

        Args:
            cards (List[str]): List of card strings.

        Returns:
            str: Formatted card string.
        """
        return ", ".join(cards)

    def _calculate_hand_value(self, cards: List[str]) -> int:
        r"""Calculate the value of a hand in Blackjack.

        Args:
            cards (List[str]): List of card strings.

        Returns:
            int: The value of the hand.
        """
        value = 0
        num_aces = 0

        for card in cards:
            # Extract the rank (first character(s) before the suit)
            rank = card[:1]
            if rank == 'A':
                num_aces += 1
                value += 11
            elif rank in ['J', 'Q', 'K', 'T']:
                value += 10
            else:
                value += int(rank)

        # Adjust for aces if needed
        while value > 21 and num_aces > 0:
            value -= 10  # Change an ace from 11 to 1
            num_aces -= 1

        return value


class LeducHoldemEnv(RLCardsEnv):
    r"""A Leduc Hold'em environment for reinforcement learning with LLMs.

    This environment implements a Leduc Hold'em poker game where the LLM agent
    plays against one or more opponents.
    """

    def __init__(
        self,
        extractor: Optional[BaseExtractor] = None,
        max_steps: Optional[int] = None,
        num_players: int = 2,
        **kwargs,
    ) -> None:
        r"""Initialize the Leduc Hold'em environment.

        Args:
            extractor (Optional[BaseExtractor]): Extractor to process LLM
                responses. If None, a default extractor will be used.
                (default: :obj:`None`)
            max_steps (Optional[int]): Maximum steps per episode.
                (default: :obj:`None`)
            num_players (int): Number of players in the game.
                (default: :obj:`2`)
            **kwargs: Additional environment parameters.
        """
        super().__init__(
            "leduc-holdem",
            extractor,
            max_steps,
            num_players=num_players,
            **kwargs,
        )

    def _convert_to_rlcard_action(self, action_str: str) -> int:
        r"""Convert a string action to the format expected by RLCard
        Leduc Hold'em.

        Args:
            action_str (str): The string representation of the action.
                Expected to be 'fold', 'check', 'call', or 'raise'.

        Returns:
            int: 0 for 'fold', 1 for 'check/call', 2 for 'raise'.
        """
        action_str = action_str.lower().strip()
        if action_str == "fold":
            return 0
        elif action_str in ["check", "call"]:
            return 1
        elif action_str == "raise":
            return 2
        else:
            raise ValueError()

    def _format_state_for_observation(self, state: Dict[str, Any]) -> str:
        r"""Format the Leduc Hold'em state for human-readable observation.

        Args:
            state (Dict[str, Any]): The RLCard state dictionary.

        Returns:
            str: A human-readable representation of the state.
        """
        if state is None:
            return "Game not started yet."

        raw_obs = state.get('raw_obs', {})
        if raw_obs is None:
            raw_obs = {}

        hand = raw_obs.get('hand', [])
        public_card = raw_obs.get('public_card', None)
        all_chips = raw_obs.get('all_chips', [])
        my_chips = all_chips[0] if all_chips else 0
        opponent_chips = all_chips[1:] if len(all_chips) > 1 else []
        stage = raw_obs.get('stage', 0)
        current_round = "pre-flop" if stage == 0 else "flop"

        # Format the observation
        obs_text = f"Round: {current_round}\n"
        obs_text += f"Your hand: {hand}\n"
        if public_card:
            obs_text += f"Public card: {public_card}\n"
        else:
            obs_text += "Public card: None\n"

        obs_text += f"Your chips: {my_chips}\n"
        for i, chips in enumerate(opponent_chips):
            obs_text += f"Opponent {i+1} chips: {chips}\n"

        return obs_text

    def _format_legal_actions(self, legal_actions: List[int]) -> str:
        r"""Format the legal actions for Leduc Hold'em.

        Args:
            legal_actions (List[int]): The list of legal actions.

        Returns:
            str: A human-readable representation of the legal actions.
        """
        action_map = {0: "fold", 1: "check/call", 2: "raise"}
        return ", ".join([action_map[a] for a in legal_actions])


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
        super().__init__(
            "doudizhu", extractor, max_steps, num_players=3, **kwargs
        )

    def _convert_to_rlcard_action(self, action_str: str) -> Any:
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
        # potentially useful for debugging
        # played_cards = raw_obs['played_cards']
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
            obs_text += (
                f"You are a Peasant. Player {landlord} is the Landlord.\n"
            )

        # Current hand
        obs_text += f"Your hand: {self._format_cards(current_hand)}\n"

        # Last played cards by each player
        obs_text += "Last played cards:\n"
        if landlord == 0:
            inter_text = self._format_cards(landlord_played_cards)
            obs_text += f"  You (Landlord): {inter_text}\n"
            inter_text = self._format_cards(landlord_up_played_cards)
            obs_text += f"  Peasant 1: {inter_text}\n"
            inter_text = self._format_cards(landlord_down_played_cards)
            obs_text += f"  Peasant 2: {inter_text}\n"
        elif landlord == 1:
            obs_text += (
                f"  You: {self._format_cards(landlord_up_played_cards)}\n"
            )
            obs_text += (
                f"  Landlord: {self._format_cards(landlord_played_cards)}\n"
            )

            inter_text = self._format_cards(landlord_down_played_cards)
            obs_text += f"  Other Peasant: {inter_text}\n"
        else:  # landlord == 2
            obs_text += (
                f"  You: {self._format_cards(landlord_down_played_cards)}\n"
            )
            obs_text += (
                f"  Landlord: {self._format_cards(landlord_played_cards)}\n"
            )

            inter_text = self._format_cards(landlord_up_played_cards)
            obs_text += f"  Other Peasant: {inter_text}\n"

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
        # For simplicity, we'll just list the first few legal
        # actions if there are many
        if len(legal_actions) > 10:
            action_str = (
                ", ".join(legal_actions[:10])
                + f" and {len(legal_actions) - 10} more options"
            )
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
