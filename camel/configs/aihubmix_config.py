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
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class AihubmixConfig(BaseModel):
    r"""Defines the parameters for generating chat responses from the Aihubmix
    models.
    
    Args:
        temperature (Optional[float], optional): Sampling temperature to use,
            between :obj:`0` and :obj:`2`. Higher values make the output more
            random, while lower values make it more focused and deterministic.
            (default: :obj:`0.2`)
        top_p (Optional[float], optional): An alternative to sampling with
            temperature, called nucleus sampling, where the model considers the
            results of the tokens with top_p probability mass.
            (default: :obj:`1.0`)
        n (Optional[int], optional): How many completions to generate for each
            prompt. (default: :obj:`1`)
        stream (bool, optional): If True, partial message deltas will be sent
            as data-only server-sent events as they become available.
            (default: :obj:`False`)
        stop (Optional[Union[str, List[str]]], optional): Up to 4 sequences
            where the API will stop generating further tokens.
            (default: :obj:`None`)
        max_tokens (Optional[int], optional): The maximum number of tokens to
            generate in the chat completion. (default: :obj:`None`)
        presence_penalty (Optional[float], optional): Number between -2.0 and
            2.0. Positive values penalize new tokens based on whether they
            appear in the text so far. (default: :obj:`0.0`)
        frequency_penalty (Optional[float], optional): Number between -2.0 and
            2.0. Positive values penalize new tokens based on their existing
            frequency in the text so far. (default: :obj:`0.0`)
        logit_bias (Optional[Dict[str, float]], optional): Modify the
            likelihood of specified tokens appearing in the completion.
            (default: :obj:`None`)
        user (Optional[str], optional): A unique identifier representing your
            end-user. (default: :obj:`None`)
        response_format (Optional[Dict[str, str]], optional): An object
            specifying the format that the model must output.
            (default: :obj:`None`)
    """
    temperature: Optional[float] = 0.2
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1
    stream: bool = False
    stop: Optional[Union[str, List[str]]] = None
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = 0.0
    frequency_penalty: Optional[float] = 0.0
    logit_bias: Optional[Dict[str, float]] = None
    user: Optional[str] = None
    response_format: Optional[Dict[str, str]] = None

    def as_dict(self) -> Dict[str, Any]:
        r"""Convert the config to a dictionary.

        Returns:
            Dict[str, Any]: The configuration as a dictionary.
        """
        return self.model_dump(exclude_none=True)


AIHUBMIX_API_PARAMS = {param for param in AihubmixConfig.model_fields.keys()}