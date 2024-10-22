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
from typing import List

from pydantic import RootModel, model_validator

from camel.messages.axolotl.sharegpt.sharegpt_message import ShareGPTMessage


class ShareGPTConversation(RootModel):
    """A full conversation in ShareGPT format with validation"""

    root: List[ShareGPTMessage]

    @model_validator(mode='after')
    def validate_conversation_flow(self) -> 'ShareGPTConversation':
        """Validate the conversation follows logical message order"""
        messages = self.root

        if not messages:
            raise ValueError("Conversation cannot be empty")

        if messages[0].from_ not in ("system", "human"):
            raise ValueError(
                "Conversation must start with either system or human message"
            )

        # Validate message sequence
        for i in range(1, len(messages)):
            curr, prev = messages[i], messages[i - 1]

            if curr.from_ == "tool":
                if (
                    prev.from_ != "assistant"
                    or "<tool_call>" not in prev.value
                ):
                    raise ValueError(
                        f"Tool response at position {i} must follow an assistant message with a tool call"
                    )

            if curr.from_ == "assistant" and prev.from_ not in (
                "human",
                "tool",
            ):
                raise ValueError(
                    f"Assistant message at position {i} must follow a human or tool message"
                )

        return self

    def model_dump(self, **kwargs):
        return self.root

    def __iter__(self):
        return iter(self.root)
