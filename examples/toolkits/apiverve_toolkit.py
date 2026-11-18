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
from camel.toolkits import APIVerveToolkit
from camel.types import ModelPlatformType, ModelType


def main():
    # Requires APIVERVE_API_KEY in the environment. A free key is available
    # at https://dashboard.apiverve.com.
    apiverve_toolkit = APIVerveToolkit()

    # Example 1: Find an API, then call it directly
    print(apiverve_toolkit.search_apis("vat rates", max_results=1))
    print(apiverve_toolkit.call_api("vatrates", {"country": "DE"}))

    # Example 2: Let an agent pick and call the APIs
    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    agent = ChatAgent(
        system_message="You check facts with APIVerve. Use search_apis to "
        "find the right API and its parameters, then call_api to run it. "
        "Base your answer only on what the APIs return.",
        model=model,
        tools=apiverve_toolkit.get_tools(),
    )

    response = agent.step(
        "A user signed up with the email support@apiverve.com from the IP "
        "address 8.8.8.8. Is the email deliverable, and where is the IP?"
    )
    print(response.msgs[0].content)
    print(str(response.info['tool_calls'])[:1000])


if __name__ == "__main__":
    main()
