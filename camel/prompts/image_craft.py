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


class ImageCraftPromptTemplateDict(TextPromptDict):
    r"""A dictionary containing :obj:`TextPrompt` used in the `ImageCraft`
    task.

    Attributes:
        ASSISTANT_PROMPT (TextPrompt): A prompt for the AI assistant to create
            an original image based on the provided descriptive captions.
    """

    ASSISTANT_PROMPT = TextPrompt(
        """You are tasked with creating an original image based on
        the provided descriptive captions. Use your imagination
        and artistic skills to visualize and draw the images and
        explain your thought process."""
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.update(
            {
                RoleType.ASSISTANT: self.ASSISTANT_PROMPT,
            }
        )
