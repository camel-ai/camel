# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
"""Example: user profile injection and sensitive data scrubbing middleware."""

import re
from copy import deepcopy
from dataclasses import dataclass, field
from typing import List

from camel.agents import ChatAgent
from camel.agents._middleware import (
    MessageMiddleware,
    MiddlewareContext,
)
from camel.messages import OpenAIMessage
from camel.models import ModelFactory
from camel.types import ChatCompletion, ModelPlatformType, ModelType


@dataclass
class UserProfile:
    r"""Represents an operations engineer's profile."""

    user_id: str
    user_name: str
    devices: List[str]
    region: str
    sensitive_fields: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.sensitive_fields = [self.user_id]

    def to_prompt(self) -> str:
        r"""Render the profile as a system-level prompt fragment."""
        devices_str = ", ".join(self.devices)
        return (
            "【User Profile (visible only for this invocation)】\n"
            f"- User ID: {self.user_id}\n"
            f"- User Name: {self.user_name}\n"
            f"- Devices under responsibility: [{devices_str}]\n"
            f"- Region: {self.region}\n"
            "Use this profile when interpreting queries related to "
            "'my devices'. Do not reference devices outside this scope."
        )


class UserProfileInjectionMiddleware(MessageMiddleware):
    r"""Injects the user's profile as a system message before each LLM call.

    The injected message is only present in the transient message list
    passed to the model backend; it is **not** persisted in the agent's
    memory, so it will not appear in conversation history or logs.
    """

    def __init__(self, profile: UserProfile) -> None:
        self.profile = profile

    def process_request(
        self,
        messages: List[OpenAIMessage],
        context: MiddlewareContext,
    ) -> List[OpenAIMessage]:
        profile_message: OpenAIMessage = {
            "role": "system",
            "content": self.profile.to_prompt(),
        }
        # Insert the profile right after the first system message so the
        # model sees it early but the original system prompt stays first.
        insert_idx = 1 if messages and messages[0]["role"] == "system" else 0
        return (
            messages[:insert_idx] + [profile_message] + messages[insert_idx:]
        )


class SensitiveDataScrubMiddleware(MessageMiddleware):
    r"""Scrubs sensitive field values from the assistant's response.

    Even though the profile is transient, the LLM might accidentally echo
    back internal identifiers (e.g. ``u_12345``). This middleware replaces
    any occurrence with ``[REDACTED]``.
    """

    def __init__(self, profile: UserProfile) -> None:
        self.profile = profile

    def process_response(
        self,
        response: ChatCompletion,
        context: MiddlewareContext,
    ) -> ChatCompletion:
        if not self.profile.sensitive_fields:
            return response

        pattern = "|".join(re.escape(v) for v in self.profile.sensitive_fields)
        modified = deepcopy(response)
        for choice in modified.choices:
            if choice.message.content:
                choice.message.content = re.sub(
                    pattern, "[REDACTED]", choice.message.content
                )
        return modified


# Simulate the current logged-in user's profile (normally fetched from
# an identity service or database).
current_user = UserProfile(
    user_id="u_12345",
    user_name="John Doe",
    devices=["DEV-001", "DEV-002", "DEV-005"],
    region="Beijing Core Data Center",
)

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_5_MINI,
)

agent = ChatAgent(
    system_message=(
        "You are an intelligent support assistant for operations "
        "engineers. You must answer queries strictly based on the "
        "user's authorized device scope."
    ),
    model=model,
    middlewares=[
        UserProfileInjectionMiddleware(current_user),
        SensitiveDataScrubMiddleware(current_user),
    ],
)

response = agent.step(
    "Show the health report of the devices I'm responsible for."
)

print(response.msg.content)
# flake8: noqa: E501
"""
===============================================================================
Sure. Here is the recent 7-day health summary for your responsible devices:

- DEV-001: CPU usage stable around 35%, no major alerts.
- DEV-002: Two short packet-loss alerts in the last 24 hours, automatically recovered.
- DEV-005: Disk usage at 82%; consider planning for expansion this week.

Let me know if you want detailed trends for any specific device.
===============================================================================
"""

# Verify: the agent's memory should NOT contain the injected profile.
memory_messages, _token_count = agent.memory.get_context()
for msg in memory_messages:
    content = str(msg.get("content", ""))
    assert "User Profile" not in content, "Profile should NOT be in memory!"

print("\nNo user profile found in memory - sensitive data stays private.")
