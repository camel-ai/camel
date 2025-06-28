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

from typing import List, Optional


class ToolResult:
    r"""Special result type for tools that can return images along with text.

    This class is used by ChatAgent to detect when a tool returns visual
    content that should be included in the conversation context.
    """

    def __init__(self, text: str, images: Optional[List[str]] = None):
        r"""Initialize a tool result.

        Args:
            text (str): The text description or result of the tool operation.
            images (Optional[List[str]]): List of base64-encoded images to
                include in the conversation context. Images should be encoded
                as "data:image/{format};base64,{data}" format.
        """
        self.text = text
        self.images = images or []

    def __str__(self) -> str:
        r"""Return the text representation of the result."""
        return self.text

    def __repr__(self) -> str:
        r"""Return a detailed representation of the result."""
        img_count = len(self.images) if self.images else 0
        return f"ToolResult(text='{self.text[:50]}...', images={img_count})"
