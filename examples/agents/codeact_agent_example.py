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
from camel.agents import CodeActAgent
from camel.loaders import UnstructuredIO
from camel.models import ModelFactory
from camel.toolkits import FunctionTool, MathToolkit, SearchToolkit
from camel.types import ModelPlatformType, ModelType

uio = UnstructuredIO()


def extract_link_content(link):
    r"""extract the content of the link.

    Args:
        link (str): The link to be extracted.

    Returns:
        str: The content of the link.
    """

    elements = uio.parse_file_or_url(link)
    elements_str = "\n".join(str(element) for element in elements)

    return elements_str


tool_list = [
    *MathToolkit().get_tools(),
    FunctionTool(SearchToolkit().search_google),
    FunctionTool(extract_link_content),
]

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)

agent = CodeActAgent(
    model=model,
    tools=tool_list,
    sandbox="default",
    verbose=True,
)

purchase_task = (
    "I want to buy a iphone16 pro max with RMB "
    "and see which country is the cheapest: China, the USA, Japan, or Germany."
)

response = agent.step(purchase_task)
print(response)
