from typing import Dict, List


class Machine:
    r"""A state machine allowing transitions between different states based on
    triggers.

    Args:
        states (List[str]): A list of states in the machine.
        transitions (List[dict]): A list of transitions, where each transition
            is represented as a dictionary containing 'trigger', 'source', and
            'dest'.
        initial (str): The initial state of the machine.

    Attributes:
        states (List[str]): List of states within the state machine.
        transitions (List[dict]): List of state transitions.
        initial_state (str): The initial state.
        current_state (str): The current active state of the machine.
        transition_map (Dict[str, Dict[str, str]]): Mapping of triggers to
            source-destination state pairs.
    """

    def __init__(
        self, states: List[str], transitions: List[dict], initial: str
    ):
        self.states = states
        self.transitions = transitions
        self.initial_state = initial
        self.current_state = initial

        if self.initial_state not in self.states:
            raise ValueError(
                f"Initial state '{self.initial_state}' must be in the states."
            )

        self.transition_map = self._build_transition_map()

    def _build_transition_map(self) -> Dict[str, Dict[str, str]]:
        r"""Constructs a mapping from triggers to state transitions.

        Returns:
            Dict[str, Dict[str, str]]: A nested dictionary where each key is a
                trigger, mapping to another dictionary of source-destination
                state pairs.
        """
        transition_map: Dict[str, Dict[str, str]] = {}
        for transition in self.transitions:
            trigger = transition['trigger']
            source = transition['source']
            dest = transition['dest']

            if trigger not in transition_map:
                transition_map[trigger] = {}

            transition_map[trigger][source] = dest

        return transition_map

    def add_state(self, state: str):
        r"""Adds a new state to the machine if it doesn't already exist.

        Args:
            state (str): The state to be added.
        """
        if state not in self.states:
            self.states.append(state)

    def add_transition(self, trigger: str, source: str, dest: str):
        r"""Adds a new transition between states based on a trigger.

        Args:
            trigger (str): The trigger for the transition.
            source (str): The source state.
            dest (str): The destination state.

        Raises:
            ValueError: If either the source or destination state is invalid.
        """
        if source not in self.states or dest not in self.states:
            raise ValueError(
                f"Both source '{source}' and destination '{dest}' must be "
                + "valid states."
            )

        if trigger not in self.transition_map:
            self.transition_map[trigger] = {}

        self.transition_map[trigger][source] = dest

    def trigger(self, trigger: str):
        r"""Executes a state transition based on a given trigger.

        Args:
            trigger (str): The trigger to initiate the state transition.

        Raises:
            ValueError: If there is no valid transition for the given trigger
                from the current state.
        """
        if (
            trigger in self.transition_map
            and self.current_state in self.transition_map[trigger]
        ):
            new_state = self.transition_map[trigger][self.current_state]
            self.current_state = new_state
        else:
            print(
                f"No valid transition for trigger '{trigger}' from state '"
                + f"{self.current_state}'."
            )

    def reset(self):
        r"""Resets the machine to its initial state."""
        self.current_state = self.initial_state

    def get_current_state(self) -> str:
        r"""Gets the current active state of the machine.

        Returns:
            str: The current state.
        """
        return self.current_state

    def get_available_triggers(self) -> List[str]:
        r"""Lists triggers available from the current state.

        Returns:
            List[str]: List of available triggers.
        """
        return [
            trigger
            for trigger, transitions in self.transition_map.items()
            if self.current_state in transitions
        ]

    def remove_state(self, state: str):
        r"""Removes a state from the machine and any transitions involving it.

        Args:
            state (str): The state to be removed.
        """
        if state in self.states:
            self.states.remove(state)
            # Remove transitions associated with the state
            self.transition_map = {
                trigger: {
                    src: dst
                    for src, dst in transitions.items()
                    if src != state and dst != state
                }
                for trigger, transitions in self.transition_map.items()
            }

    def remove_transition(self, trigger: str, source: str):
        r"""Removes a specific transition from a given source state based on a
        trigger.

        Args:
            trigger (str): The trigger associated with the transition.
            source (str): The source state.
        """
        if (
            trigger in self.transition_map
            and source in self.transition_map[trigger]
        ):
            del self.transition_map[trigger][source]
