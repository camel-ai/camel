<a id="camel.environments.rlcards_env"></a>

<a id="camel.environments.rlcards_env.ActionExtractor"></a>

## ActionExtractor

```python
class ActionExtractor(BaseExtractorStrategy):
```

A strategy for extracting RLCard actions from text.

<a id="camel.environments.rlcards_env.ActionExtractor.__init__"></a>

### __init__

```python
def __init__(self, action_pattern: str = '<Action>\\s*(.+)'):
```

Initialize the action extractor with a regex pattern.

**Parameters:**

- **action_pattern** (str): The regex pattern to extract actions. (default: :obj:`"<Action>\\s*(.+)"`).

<a id="camel.environments.rlcards_env.RLCardsEnv"></a>

## RLCardsEnv

```python
class RLCardsEnv(MultiStepEnv):
```

A base environment for RLCard games.

This environment implements a wrapper around RLCard environments for
reinforcement learning with LLMs. It handles the conversion between
RLCard states and actions and the CAMEL environment interface.

<a id="camel.environments.rlcards_env.RLCardsEnv.__init__"></a>

### __init__

```python
def __init__(
    self,
    game_name: str,
    extractor: Optional[BaseExtractor] = None,
    max_steps: Optional[int] = None,
    num_players: int = 2,
    **kwargs
):
```

Initialize the RLCard environment.

**Parameters:**

- **game_name** (str): The name of the RLCard game to play.
- **extractor** (Optional[BaseExtractor]): Extractor to process LLM responses. If None, a default extractor with ActionExtractor will be used. (default: :obj:`None`)
- **max_steps** (Optional[int]): Maximum steps per episode. (default: :obj:`None`)
- **num_players** (int): Number of players in the game. (default: :obj:`2`) **kwargs: Additional environment parameters.

<a id="camel.environments.rlcards_env.RLCardsEnv._get_initial_state"></a>

### _get_initial_state

```python
def _get_initial_state(self):
```

**Returns:**

  Dict[str, Any]: A dictionary containing the initial state with
game state, player info, and game status flags.

<a id="camel.environments.rlcards_env.RLCardsEnv._get_next_observation"></a>

### _get_next_observation

```python
def _get_next_observation(self):
```

**Returns:**

  Observation: An Observation object containing the game state
description.

<a id="camel.environments.rlcards_env.RLCardsEnv._get_terminal_observation"></a>

### _get_terminal_observation

```python
def _get_terminal_observation(self):
```

**Returns:**

  Observation: An Observation object containing the final game state
description.

<a id="camel.environments.rlcards_env.RLCardsEnv._is_done"></a>

### _is_done

```python
def _is_done(self):
```

**Returns:**

  bool: True if the game is over, False otherwise.

<a id="camel.environments.rlcards_env.RLCardsEnv._convert_to_rlcard_action"></a>

### _convert_to_rlcard_action

```python
def _convert_to_rlcard_action(self, action_str: str):
```

Convert a string action to the format expected by RLCard.

This method must be implemented by subclasses to handle the specific
action format of each game.

**Parameters:**

- **action_str** (str): The string representation of the action.

**Returns:**

  Any: The action in the format expected by the RLCard environment.

<a id="camel.environments.rlcards_env.RLCardsEnv._format_state_for_observation"></a>

### _format_state_for_observation

```python
def _format_state_for_observation(self, state: Dict[str, Any]):
```

Format the RLCard state for human-readable observation.

This method must be implemented by subclasses to create a
human-readable representation of the game state.

**Parameters:**

- **state** (Dict[str, Any]): The RLCard state dictionary.

**Returns:**

  str: A human-readable representation of the state.

<a id="camel.environments.rlcards_env.RLCardsEnv._format_legal_actions"></a>

### _format_legal_actions

```python
def _format_legal_actions(self, legal_actions: List[Any]):
```

Format the legal actions for human-readable observation.

This method must be implemented by subclasses to create a
human-readable representation of the legal actions.

**Parameters:**

- **legal_actions** (List[Any]): The list of legal actions.

**Returns:**

  str: A human-readable representation of the legal actions.

<a id="camel.environments.rlcards_env.BlackjackEnv"></a>

## BlackjackEnv

```python
class BlackjackEnv(RLCardsEnv):
```

A Blackjack environment for reinforcement learning with LLMs.

This environment implements a standard Blackjack game where the LLM agent
plays against a dealer.

<a id="camel.environments.rlcards_env.BlackjackEnv.__init__"></a>

### __init__

```python
def __init__(
    self,
    extractor: Optional[BaseExtractor] = None,
    max_steps: Optional[int] = None,
    **kwargs
):
```

Initialize the Blackjack environment.

**Parameters:**

- **extractor** (Optional[BaseExtractor]): Extractor to process LLM responses. If None, a default extractor will be used. (default: :obj:`None`)
- **max_steps** (Optional[int]): Maximum steps per episode. (default: :obj:`None`) **kwargs: Additional environment parameters.

<a id="camel.environments.rlcards_env.BlackjackEnv._convert_to_rlcard_action"></a>

### _convert_to_rlcard_action

```python
def _convert_to_rlcard_action(self, action_str: str):
```

Convert a string action to the format expected by RLCard Blackjack.

**Parameters:**

- **action_str** (str): The string representation of the action. Expected to be 'hit' or 'stand'.

**Returns:**

  int: 0 for 'hit', 1 for 'stand'.

<a id="camel.environments.rlcards_env.BlackjackEnv._format_state_for_observation"></a>

### _format_state_for_observation

```python
def _format_state_for_observation(self, state: Dict[str, Any]):
```

Format the Blackjack state for human-readable observation.

**Parameters:**

- **state** (Dict[str, Any]): The RLCard state dictionary.

**Returns:**

  str: A human-readable representation of the state.

<a id="camel.environments.rlcards_env.BlackjackEnv._format_legal_actions"></a>

### _format_legal_actions

```python
def _format_legal_actions(self, legal_actions: List[int]):
```

Format the legal actions for Blackjack.

**Parameters:**

- **legal_actions** (List[int]): The list of legal actions.

**Returns:**

  str: A human-readable representation of the legal actions.

<a id="camel.environments.rlcards_env.BlackjackEnv._format_cards"></a>

### _format_cards

```python
def _format_cards(self, cards: List[str]):
```

Format a list of cards for display.

**Parameters:**

- **cards** (List[str]): List of card strings.

**Returns:**

  str: Formatted card string.

<a id="camel.environments.rlcards_env.BlackjackEnv._calculate_hand_value"></a>

### _calculate_hand_value

```python
def _calculate_hand_value(self, cards: List[str]):
```

Calculate the value of a hand in Blackjack.

**Parameters:**

- **cards** (List[str]): List of card strings.

**Returns:**

  int: The value of the hand.

<a id="camel.environments.rlcards_env.LeducHoldemEnv"></a>

## LeducHoldemEnv

```python
class LeducHoldemEnv(RLCardsEnv):
```

A Leduc Hold'em environment for reinforcement learning with LLMs.

This environment implements a Leduc Hold'em poker game where the LLM agent
plays against one or more opponents.

<a id="camel.environments.rlcards_env.LeducHoldemEnv.__init__"></a>

### __init__

```python
def __init__(
    self,
    extractor: Optional[BaseExtractor] = None,
    max_steps: Optional[int] = None,
    num_players: int = 2,
    **kwargs
):
```

Initialize the Leduc Hold'em environment.

**Parameters:**

- **extractor** (Optional[BaseExtractor]): Extractor to process LLM responses. If None, a default extractor will be used. (default: :obj:`None`)
- **max_steps** (Optional[int]): Maximum steps per episode. (default: :obj:`None`)
- **num_players** (int): Number of players in the game. (default: :obj:`2`) **kwargs: Additional environment parameters.

<a id="camel.environments.rlcards_env.LeducHoldemEnv._convert_to_rlcard_action"></a>

### _convert_to_rlcard_action

```python
def _convert_to_rlcard_action(self, action_str: str):
```

Convert a string action to the format expected by RLCard
Leduc Hold'em.

**Parameters:**

- **action_str** (str): The string representation of the action. Expected to be 'fold', 'check', 'call', or 'raise'.

**Returns:**

  int: 0 for 'fold', 1 for 'check/call', 2 for 'raise'.

<a id="camel.environments.rlcards_env.LeducHoldemEnv._format_state_for_observation"></a>

### _format_state_for_observation

```python
def _format_state_for_observation(self, state: Dict[str, Any]):
```

Format the Leduc Hold'em state for human-readable observation.

**Parameters:**

- **state** (Dict[str, Any]): The RLCard state dictionary.

**Returns:**

  str: A human-readable representation of the state.

<a id="camel.environments.rlcards_env.LeducHoldemEnv._format_legal_actions"></a>

### _format_legal_actions

```python
def _format_legal_actions(self, legal_actions: List[int]):
```

Format the legal actions for Leduc Hold'em.

**Parameters:**

- **legal_actions** (List[int]): The list of legal actions.

**Returns:**

  str: A human-readable representation of the legal actions.

<a id="camel.environments.rlcards_env.DoudizhuEnv"></a>

## DoudizhuEnv

```python
class DoudizhuEnv(RLCardsEnv):
```

A Doudizhu environment for reinforcement learning with LLMs.

This environment implements a standard Doudizhu game where the LLM agent
plays against two AI opponents.

<a id="camel.environments.rlcards_env.DoudizhuEnv.__init__"></a>

### __init__

```python
def __init__(
    self,
    extractor: Optional[BaseExtractor] = None,
    max_steps: Optional[int] = None,
    **kwargs
):
```

Initialize the Doudizhu environment.

**Parameters:**

- **extractor** (Optional[BaseExtractor]): Extractor to process LLM responses. If None, a default extractor will be used. (default: :obj:`None`)
- **max_steps** (Optional[int]): Maximum steps per episode. (default: :obj:`None`) **kwargs: Additional environment parameters.

<a id="camel.environments.rlcards_env.DoudizhuEnv._convert_to_rlcard_action"></a>

### _convert_to_rlcard_action

```python
def _convert_to_rlcard_action(self, action_str: str):
```

Convert a string action to the format expected by RLCard Doudizhu.

**Parameters:**

- **action_str** (str): The string representation of the action. Expected to be a card combination or 'pass'.

**Returns:**

  str: The action string in the format expected by RLCard.

<a id="camel.environments.rlcards_env.DoudizhuEnv._format_state_for_observation"></a>

### _format_state_for_observation

```python
def _format_state_for_observation(self, state: Dict[str, Any]):
```

Format the Doudizhu state for human-readable observation.

**Parameters:**

- **state** (Dict[str, Any]): The RLCard state dictionary.

**Returns:**

  str: A human-readable representation of the state.

<a id="camel.environments.rlcards_env.DoudizhuEnv._format_legal_actions"></a>

### _format_legal_actions

```python
def _format_legal_actions(self, legal_actions: List[str]):
```

Format the legal actions for Doudizhu.

**Parameters:**

- **legal_actions** (List[str]): The list of legal actions.

**Returns:**

  str: A human-readable representation of the legal actions.

<a id="camel.environments.rlcards_env.DoudizhuEnv._format_cards"></a>

### _format_cards

```python
def _format_cards(self, cards: List[str]):
```

Format a list of cards for display.

**Parameters:**

- **cards** (List[str]): List of card strings.

**Returns:**

  str: Formatted card string.
