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
from camel.toolkits import DarkmoonToolkit
from camel.types import ModelPlatformType, ModelType


def main():
    # Requires a self-hosted Darkmoon instance with its Dashboard API
    # (Pro edition) and these environment variables:
    #   DARKMOON_BASE_URL, DARKMOON_USERNAME, DARKMOON_PASSWORD
    # Only point the agent at systems you are authorised to test.
    darkmoon_toolkit = DarkmoonToolkit()

    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    agent = ChatAgent(
        system_message="You are a security assistant. Use the "
        "DarkmoonToolkit to list Darkmoon campaigns and read their "
        "findings. Only start a pentest against targets the user states "
        "they are authorised to test, and remind the user that findings "
        "may contain false positives and need human review.",
        model=model,
        tools=darkmoon_toolkit.get_tools(),
    )

    response = agent.step(
        "List my Darkmoon campaigns and summarise the findings of the "
        "most recent one by severity."
    )
    print(response.msgs[0].content)


if __name__ == "__main__":
    main()
