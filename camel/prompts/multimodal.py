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
from typing import Any, Callable, Dict, List, Union

from camel.prompts import TextPrompt

MODALITIES = ["CAMEL_IMAGE"]


def default_to_model_format(text_prompt,modalities_dict:Dict) -> Dict:
    r"""
    The default format is return the text and multimodal information in dict.
    This function should be implemented in the multimodal prompt class.

    Returns:
        dict: The input format that the multimodal model can understand.
    """

    return {"text": text_prompt, "multimodal_information": modalities_dict}

class MultiModalPrompt:
    r"""
    To enable information transfer between multimodal agents, we need a multimodal prompt class.
    It contains a text prompt and multimodal information.
    """

    def __init__(self,text_prompt:TextPrompt, modalities: Union[List, Dict]):
        r"""
        Initializes the multimodal prompt.

        Args:
            text_prompt (TextPrompt): The text prompt.
            multimodal_info (dict): The supported modalities list or modality information dict.
        """
        # check if multimodal_info is valid
        for modality in modalities:
            assert modality in MODALITIES, f"modality {modality} not supported."

        self.text_prompt = text_prompt
        self.modalities = modalities
    
    def format(self, *args: Any, **kwargs: Any) -> 'MultiModalPrompt':
        r"""
        Formats the text prompt and the multimodal information at the same time.
        if the keyword argument is in MODALITIES, then pop it and add it to multimodal_info, otherwise, apply it to text_prompt.

        Args:
            *args (Any): Variable length argument list.
            **kwargs (Any): Arbitrary keyword arguments.

        Returns:    
            MultiModalPrompt: The formatted multimodal prompt.
        """

        # pop the kwargs that is in MODALITIES
        multimodal_info = {}
        for modality in self.modalities:
            multimodal_info[modality] = kwargs.pop(modality)

        text_prompt = self.text_prompt.format(*args, **kwargs)
        return MultiModalPrompt(text_prompt, multimodal_info)
    
    def to_model_format(self, method:Callable = default_to_model_format) -> Any:
        r"""
        Converts the prompt to the input format that the multimodal model can understand. Different multimodal models have different input formats.
        The default format is return the text and multimodal information in dict.
        This function should be implemented in the multimodal prompt class.

        Returns:
            dict: The input format that the multimodal model can understand.
        """

        return method(self.text_prompt, self.modalities)
    


        



# TODO: MultiModalPromptDict