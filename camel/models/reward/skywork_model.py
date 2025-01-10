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
from typing import Dict, List, Optional, Union

import torch

from camel.models.reward import BaseRewardModel
from camel.types import ModelType


class SkyworkRewardModel(BaseRewardModel):
    r"""Reward model based on the transformers, it will download the model
    from huggingface.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created.
        api_key (Optional[str], optional): Not used. (default: :obj:`None`)
        url (Optional[str], optional): Not used. (default: :obj:`None`)
        device_map (Optional[str], optional): choose the device map.
            (default: :obj:`auto`)
        attn_implementation (Optional[str], optional): choose the attention
            implementation. (default: :obj:`flash_attention_2`)
        offload_folder (Optional[str], optional): choose the offload folder.
            (default: :obj:`offload`)
    """

    def __init__(
        self,
        model_type: Union[ModelType, str],
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        device_map: Optional[str] = "auto",
        attn_implementation: Optional[str] = "flash_attention_2",
        offload_folder: Optional[str] = "offload",
    ) -> None:
        from transformers import (
            AutoModelForSequenceClassification,
            AutoTokenizer,
        )

        super().__init__(model_type, api_key, url)
        self._client = AutoModelForSequenceClassification.from_pretrained(
            model_type,
            torch_dtype=torch.bfloat16,
            device_map=device_map,
            attn_implementation=attn_implementation,
            offload_folder=offload_folder,
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
            return {"Score": score}

    def get_scores_types(self) -> List[str]:
        r"""get the scores types

        Returns:
            List[str]: list of scores types
        """
        return ["Score"]
