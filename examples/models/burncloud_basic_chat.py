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
"""Minimal BurnCloud chat example.

Before running:

```bash
export BURNCLOUD_API_KEY="your_burncloud_api_key"
# Optional: export BURNCLOUD_API_BASE_URL="https://ai.burncloud.com/v1"
```
"""

from camel.agents import ChatAgent
from camel.configs import BurnCloudConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType


def main() -> None:
    """Create a BurnCloud model and send a single chat request."""

    model = ModelFactory.create(
        model_platform=ModelPlatformType.BURNCLOUD,
        # BurnCloud is OpenAI-compatible, so we can reuse CAMEL enums
        # or pass raw strings such as "claude-3.5-sonnet".
        model_type=ModelType.GPT_4O,
        model_config_dict=BurnCloudConfig(temperature=0.2).as_dict(),
    )

    agent = ChatAgent(
        system_message="You are a CAMEL-AI savvy technical consultant.",
        model=model,
    )

    user_msg = (
        "Summarize CAMEL-AI's core capabilities in three sentences and "
        "highlight its multi-agent collaboration strengths."
    )

    response = agent.step(user_msg)
    print("User:\n", user_msg)
    print("\nAssistant:\n", response.msgs[0].content)


if __name__ == "__main__":
    main()
