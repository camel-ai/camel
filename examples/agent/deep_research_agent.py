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




from camel.agents import ChatAgent, DeepResearchAgent
from camel.responses import ChatAgentResponse
from camel.messages import BaseMessage
from camel.types import OpenAIBackendRole
from camel.toolkits.search_toolkit import SearchToolkit
from camel.types.agents import ToolCallingRecord
from camel.toolkits import (
    SearchToolkit,
    # MathToolkit,
    # GoogleMapsToolkit,
    # TwitterToolkit,
    # WeatherToolkit,
    # RetrievalToolkit,
    # TwitterToolkit,
    # SlackToolkit,
    # LinkedInToolkit,
    # RedditToolkit,
)
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from typing import Optional, List
from camel.toolkits import FunctionTool

tools_list = [
    # *MathToolkit().get_tools(),
    SearchToolkit().search_duckduckgo,
]

if __name__ == "__main__":
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O_MINI
    )
    query = "搞笑问题：巩汉林喝了一杯太后大酒楼的宫廷玉液酒，又请黄大锤用大锤掏壁橱，一共花多少钱？"
    agent = DeepResearchAgent(model = model,tools = tools_list)
    print(agent.step(query,output_language="Chinese"))