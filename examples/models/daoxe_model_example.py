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

r"""Example of using DaoXE models in CAMEL.

Please set the following environment variable:
export DAOXE_API_KEY="your_daoxe_api_key_here"

DaoXE is an OpenAI-compatible multi-model gateway
(base URL: https://daoxe.com/v1). Model ids are account-scoped — pass the
model id string available on your DaoXE account.

Note: DaoXE is not available in mainland China.
"""

import os

from camel.agents import ChatAgent
from camel.configs import DaoXEConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType


def main() -> None:
    api_key = os.environ.get("DAOXE_API_KEY")
    if not api_key:
        print("Skipping DaoXE example - DAOXE_API_KEY not set")
        return

    # Example 1: Basic usage with a free-form model id
    print("=== Example 1: Basic DaoXE Usage ===")

    model = ModelFactory.create(
        model_platform=ModelPlatformType.DAOXE,
        model_type="gpt-4o-mini",  # any model id from your DaoXE account
        model_config_dict=DaoXEConfig(temperature=0.2).as_dict(),
        api_key=api_key,
    )

    agent = ChatAgent(
        system_message="You are a helpful assistant.",
        model=model,
    )

    user_msg = (
        "Say hi to CAMEL AI, an open-source community dedicated to the "
        "study of autonomous and communicative agents."
    )
    response = agent.step(user_msg)
    print(response.msgs[0].content)

    print("\n" + "=" * 80 + "\n")

    # Example 2: Custom configuration with another model id
    print("=== Example 2: Custom Configuration ===")

    model_2 = ModelFactory.create(
        model_platform=ModelPlatformType.DAOXE,
        model_type="claude-sonnet-4-20250514",
        model_config_dict=DaoXEConfig(
            temperature=0.7,
            max_tokens=500,
            top_p=0.9,
        ).as_dict(),
        api_key=api_key,
    )

    agent_2 = ChatAgent(
        system_message="You are a concise technical assistant.",
        model=model_2,
    )
    response_2 = agent_2.step("In one sentence, what is a multi-agent system?")
    print(response_2.msgs[0].content)


if __name__ == "__main__":
    main()
