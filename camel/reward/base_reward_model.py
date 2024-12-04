from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from openai import OpenAI

from camel.messages import OpenAIMessage
from camel.models import BaseModelBackend
from camel.types import ChatCompletion, ModelType
from camel.utils import BaseTokenCounter
class BaseRewardModel(ABC):
    r"""
    Abstract base class for reward models. Reward models are used to evaluate
    messages and return scores based on different criteria.

    subclasses should implement the 'evaluate' and 'get_scores_types' methods.
    """
    def __init__(self,
                model_type: Union[ModelType, str], 
                api_key: Optional[str] = None, 
                url: Optional[str] = None
                ) -> None:
        self.model_type = model_type
        self.api_key = api_key
        self.url = url

    @abstractmethod
    def evaluate(self, messages: List[OpenAIMessage]) -> ChatCompletion:
        r"""
        Evaluate the messages and return scores based on different criteria.

        Args:
            messages (List[Dict[str, str]]): A list of messages where each
                message is a dictionary with 'role' and 'content'.

        Returns:
            Dict[str, float]: A dictionary mapping score types to their values.
        """
        pass

    @abstractmethod
    def get_scores_types(self) -> List[str]:
        r"""
        Get the list of score types that the reward model can return.

        Returns:
            List[str]: A list of score types that the reward model can return.
        """
        pass
