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

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import JinaRerankerToolkit
from camel.types import ModelPlatformType, ModelType

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)

reranker_toolkit = JinaRerankerToolkit()
reranker_tool = reranker_toolkit.get_tools()

agent = ChatAgent(model=model, tools=reranker_tool)

documents = [
    "We present ReaderLM-v2, a compact 1.5 billion parameter",
    "数据提取么 为什么不用正则啊 你用正则不就全解决了么",
    "During the California Gold Rush, some merchants made more money",
    "Die wichtigsten Beiträge unserer Arbeit sind zweifach",
]

query = "slm markdown"

response = agent.step(
    f"Can you rerank these documents {documents} against the query {query}"
)
print(str(response.info['tool_calls'])[:1000])
""""
===========================================================================
[ToolCallingRecord(tool_name='rerank_text_documents', 
args={'query': 'slm markdown', 'documents': ['We present ReaderLM-v2, a 
compact 1.5 billion parameter 
数据提取么 为什么不用正则啊 你用正则不就全解决了么', 
'During the California Gold Rush, some merchants made more money',
'Die wichtigsten Beiträge unserer Arbeit sind zweifach'], '
max_length': 1024}
===========================================================================
"""
