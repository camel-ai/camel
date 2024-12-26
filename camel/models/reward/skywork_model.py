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
from camel.models.reward import BaseRewardModel
from typing import Union, Optional, List, Dict
from camel.messages import OpenAIMessage
from camel.types import ModelType
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

class SkyworkRewardModel(BaseRewardModel):
    r"""Reward model based on the transformers, it will download the model
    from huggingface.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created.
        api_key (Optional[str], optional): Not used.
        url (Optional[str], optional): Not used.
    """

    def __init__(
        self,
        model_type: Union[ModelType, str],
        api_key: Optional[str] = None,
        url: Optional[str] = None,
    ) -> None:
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        super().__init__(model_type, api_key, url)
        self._client = AutoModelForSequenceClassification.from_pretrained(
            model_type,
            torch_dtype=torch.bfloat16,
            device_map=device,
            attn_implementation="flash_attention_2",
            num_labels=1,
            )
        self._tokenizer = AutoTokenizer.from_pretrained(model_type)

    def evaluate(self, messages: List[Dict[str, str]]) -> Dict[str, float]:
        r"""Evaluate the messages using the Skywork model.

        Args:
            messages (List[Dict[str, str]]): A list of messages.

        Returns:
            ChatCompletion: A ChatCompletion object with the scores.
        """
        inputs = self._tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            return_tensors="pt",
        )
        with torch.no_grad():
            score = self._client(inputs).logits[0][0].item()
            return {"score": score}

    def get_scores_types(self) -> List[str]:
        """get the scores types
        Returns:
            List[str]: list of scores types
        """
        return ["score"]
