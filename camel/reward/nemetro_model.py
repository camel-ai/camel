
import os
from typing import List, Optional, Union, Dict
from camel.types import ChatCompletion, ModelType
from camel.reward.base_reward_model import BaseRewardModel
from camel.utils import api_keys_required
from camel.messages import OpenAIMessage

from openai import OpenAI

class NemotroModel(BaseRewardModel):
    r"""
    Reward model based on the Nemetro model with OpenAI compatibility.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created.
        api_key (Optional[str], optional): The API key for authenticating
            with the model service. (default: :obj:`None`)
        url (Optional[str], optional): The url to the model service.
    
    Note:
        The Nemetro model does not support model config.
    """

    def __init__(
        self,
        model_type: Union[ModelType, str],
        api_key: Optional[str] = None,
        url: Optional[str] = None,
    ) -> None:
        url = url or os.environ.get("NVIDIA_API_BASE_URL", 
                                    "https://integrate.api.nvidia.com/v1")
        api_key = api_key or os.environ.get("NVIDIA_API_KEY")
        super().__init__(model_type, api_key, url)
        self._client = OpenAI(
            timeout=60,
            max_retries=3,
            base_url=self.url,
            api_key=self.api_key,
            )
    
    @api_keys_required("NVIDIA_API_KEY")
    def evaluate(self, messages: List[OpenAIMessage]) -> Dict[str, float]:
        r"""
        Evaluate the messages using the Nemetro model.

        Args:
            messages (List[OpenAIMessage]): A list of messages where each
                message is an OpenAIMessage object.

        Returns:
            ChatCompletion: A ChatCompletion object with the scores.
        """
        response = self._client.chat_completion.create(
            messages=messages,
            model=self.model_type,
        )
        scores = self._parse_scores(response)
        return scores
    
    def get_scores_types(self) -> List[str]:
        r"""
        Get the list of score types that the reward model can return.

        Returns:
            List[str]: A list of score types that the reward model can return.
        """
        return ["helpfulness",
                "correctness",
                "coherence",
                "complexity",
                "verbosity",]
    
    def _parse_scores(self, response: ChatCompletion) -> Dict[str, float]:
        r"""
        Parse the scores from the response.

        Args:
            response (ChatCompletion): A ChatCompletion object with the scores.

        Returns:
            Dict[str, float]: A dictionary mapping score types to their values.
        """
        try:
            logprobs = response["choices"][0]["logprobs"]["content"]
            scores = {entry["token"]: entry["logprob"] for entry in logprobs}
            return scores
        except (KeyError, IndexError) as e:
            return {"error": 0.0}
