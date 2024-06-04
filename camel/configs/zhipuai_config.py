# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
from __future__ import annotations
from dataclasses import asdict, dataclass
from camel.configs.base_config import BaseConfig
from typing import List, Optional


@dataclass(frozen=True)
class ZhipuaiConfig(BaseConfig):
    r"""
    Defines the configuration parameters for the ZhipuAI API.

    Args:
        model (str): **Required**. The model encoding to be used for the API call.
            This specifies the model version or type that the API will utilize.
        messages (List[Dict[str, Any]]): **Required**. A list of messages that 
            contain the conversation history to be used as context for the AI's response.
            Each message is a dictionary with "role" and "content" keys, where "role"
            can be "system", "user", "assistant", or "tool", and "content" is the text of the message.
            - request_id (str, optional): A unique identifier for the request, which 
            is useful for tracking and should be unique for each call. If not provided,
            the platform will generate one by default.
        do_sample (bool, optional): Determines whether to use sampling strategy 
            when generating the response. If set to false, the temperature and top_p 
            parameters will not affect the sampling process. Defaults to True.
        stream (bool, optional): If set to true, the model will return its 
            generated content in chunks via an Event Stream. This is useful for 
            receiving partial results before the full response is complete. 
            Defaults to False, meaning the response will be returned all at once.
        temperature (float, optional): Controls the randomness of the output. A 
            value between 0.0 and 1.0, where higher values result in more randomness 
            and lower values result in more focused responses. Defaults to 0.95.
        top_p (float, optional): Another sampling method known as nucleus sampling,
            where the model considers the tokens with the highest probabilities. 
            A value between 0.0 and 1.0, but not 0 or 1. The default is 0.7.
        max_tokens (int, optional): The maximum number of tokens to generate 
            in the response. The total length of input and generated text is 
            constrained by the model's context length. Defaults to 1024.
        stop (List[str], optional): A list of stop words that, when encountered, 
            will cause the model to stop generating further tokens. Currently, only 
            a single stop word is supported.
        tools (List[str], optional): A list of tools that the model can utilize 
            to assist in generating the response. The default tool is "web_search".
        tool_choice (str, optional): Controls how the model selects which function 
            to call when using tools. The default is "auto", which allows the model 
            to decide.
        user_id (str, optional): A unique identifier for the end user, which 
            assists the platform in monitoring and intervening in cases of abuse or 
            generation of inappropriate content. The ID should be between 6 and 128 
            characters in length.
    """

    request_id: Optional[str] = None
    do_sample: Optional[bool] = True
    stream: Optional[bool] = False
    temperature: Optional[float] = 0.95
    top_p: Optional[float] = 0.7
    max_tokens: Optional[int] = 8192
    stop: Optional[List[str]] = None
    tools: Optional[List[str]] = None
    tool_choice: Optional[str] = "auto"

ZHIPU_API_PARAMS = {param for param in asdict(ZhipuaiConfig()).keys()}