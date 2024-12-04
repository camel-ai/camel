
from typing import Dict, List
from camel.reward.base_reward_model import BaseRewardModel

class Evaluator:
    r"""
    Evaluator class to evaluate messages using a reward model and filter data
    based on the scores.

    Args:
        reward_model (BaseRewardModel): A reward model to evaluate messages.
    """

    def __init__(self, reward_model: BaseRewardModel):
        self.reward_model = reward_model
    
    def evaluate(self, messages: List[Dict[str, str]]) -> Dict[str, float]:
        r"""
        Evaluate the messages using the reward model.

        Args:
            messages (List[Dict[str, str]]): A list of messages where each
                message is a dictionary with 'role' and 'content'.

        Returns:
            Dict[str, float]: A dictionary mapping score types to their values.
        """
        scores = self.reward_model.evaluate(messages)
        return scores
    
    def filter_data(
            self, messages: List[Dict[str, str]], threshold: Dict[str, float]
    ) -> bool:
        r"""
        Filter messages based on the scores.

        Args:
            messages (List[Dict[str, str]]): A list of messages where each
                message is a dictionary with 'role' and 'content'.
            threshold (Dict[str, float]): A dictionary mapping score types to
                their values.

        Returns:
            bool: A boolean indicating whether the messages pass the filter.
        """
        scores = self.evaluate(messages)
        for score_type, threshold in threshold.items():
            if scores.get(score_type, 0) < threshold:
                return False
        return True