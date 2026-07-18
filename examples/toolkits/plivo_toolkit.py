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
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import PlivoToolkit
from camel.types import ModelPlatformType, ModelType


def main():
    # Requires PLIVO_AUTH_ID and PLIVO_AUTH_TOKEN in the environment.
    plivo_toolkit = PlivoToolkit()

    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    agent = ChatAgent(
        system_message="You are a communications assistant. Use the "
        "PlivoToolkit to send SMS, place voice calls, send and check OTP "
        "verification codes, and look up phone numbers.",
        model=model,
        tools=plivo_toolkit.get_tools(),
    )

    # Example 1: Send an SMS
    print("=" * 50)
    print("Example 1: Send SMS")
    print("=" * 50)
    response = agent.step(
        "Send an SMS from +14155550100 to +14155550123 saying "
        "'Your CAMEL AI demo is live.'"
    )
    print(response.msg.content)

    # Example 2: Look up a phone number
    print("\n" + "=" * 50)
    print("Example 2: Number Lookup")
    print("=" * 50)
    response = agent.step(
        "Look up the carrier and line type for the number +14155550123."
    )
    print(response.msg.content)

    # Example 3: Send a verification OTP, then check the code
    print("\n" + "=" * 50)
    print("Example 3: OTP Verify")
    print("=" * 50)
    response = agent.step("Send a verification OTP to +14155550123.")
    print(response.msg.content)
    response = agent.step(
        "Verify the code 123456 for that verification session."
    )
    print(response.msg.content)

    # Example 4: Place a voice call
    print("\n" + "=" * 50)
    print("Example 4: Voice Call")
    print("=" * 50)
    response = agent.step(
        "Place a call from +14155550100 to +14155550123 using the answer "
        "URL https://example.com/answer."
    )
    print(response.msg.content)


if __name__ == "__main__":
    main()
