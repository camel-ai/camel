from typing import Dict, Any, Tuple, Union
from llfbench.envs.llf_env import LLFWrapper


class GridworldWrapper(LLFWrapper):

    # Basic (b), partial (p), and complete (c)
    INSTRUCTION_TYPES = ('b', 'p', 'c')

    # Feedback type:
    # n: none
    # m: mixed
    # r: reward
    # hn: hindsight negative
    # hp: hindsight positive
    # fn: future negative
    # fp: future positive
    FEEDBACK_TYPES = ('r', 'hn', 'hp', 'fn', 'fp')

    def __init__(self, env, instruction_type, feedback_type):
        super().__init__(env, instruction_type, feedback_type)

        self.env.format = self.format
        self.env.instruction_type = instruction_type
        self.env.feedback_type = feedback_type

    def _reset(self, *, seed: int = None, options: Dict[str, Any] = None)\
            -> Tuple[Union[str, Dict[str, str]], Dict[str, Any]]:
        """ Implement this in the subclass. """

        # Reset the instruction and feedback type of the base environment based on the settings in the wrapper
        self.env.format = self.format
        self.env.instruction_type = self.instruction_type
        self.env.feedback_type = self._feedback_type
        return self.env.reset(seed=seed, options=options)

    def _step(self, action: Any) -> Tuple[Dict[str, Any], float, bool, bool,  Dict[str, Any]]:
        """ Implement this in the subclass.
            Use self._feedback_type to determine the feedback.
        """

        # Reset the instruction and feedback type of the base environment based on the settings in the wrapper
        self.env.format = self.format
        self.env.instruction_type = self.instruction_type
        self.env.feedback_type = self._feedback_type
        return self.env.step(action)
