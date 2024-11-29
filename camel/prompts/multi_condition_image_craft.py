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
from typing import Any

from camel.prompts import TextPrompt, TextPromptDict
from camel.types import RoleType


class MultiConditionImageCraftPromptTemplateDict(TextPromptDict):
    ASSISTANT_PROMPT = TextPrompt(
        """You are tasked with creating an image based on
        the provided text and images conditions. Please use your
        imagination and artistic capabilities to visualize and
        draw the images and explain what you are thinking about."""
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.update(
            {
                RoleType.ASSISTANT: self.ASSISTANT_PROMPT,
            }
        )
