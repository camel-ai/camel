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
from typing import Any

from camel.prompts.base import TextPrompt, TextPromptDict
from camel.types import RoleType


# flake8: noqa :E501
class ObjectRecognitionPromptTemplateDict(TextPromptDict):
    ASSISTANT_PROMPT = TextPrompt(
        """You have been assigned an object recognition task.
Your mission is to list all detected objects in following image.
Your output should always be a list of strings starting with `1.`, `2.` etc.
Do not explain yourself or output anything else."""
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.update(
            {
                RoleType.ASSISTANT: self.ASSISTANT_PROMPT,
            }
        )
