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

reranker_toolkit = JinaRerankerToolkit(device="cpu", use_api=False)
reranker_tool = reranker_toolkit.get_tools()

agent = ChatAgent(model=model, tools=reranker_tool)

documents = [
    "Markdown is a lightweight markup language with plain-text "
    "formatting syntax.",
    "Python is a high-level, interpreted programming language known for "
    "its readability.",
    "SLM (Small Language Models) are compact AI models designed for "
    "specific tasks.",
    "JavaScript is a scripting language primarily used for "
    "creating interactive web pages.",
]

query = "How to use markdown with small language models"

response = agent.step(
    f"Can you rerank these documents {documents} against the query {query}"
)
print(str(response.info['tool_calls'])[:1000])
""""
===========================================================================
[ToolCallingRecord(tool_name='rerank_text_documents', args={'query': 'How to 
use markdown with small language models', 'documents': ['Markdown is a 
lightweight markup language with plain-text formatting syntax.', 'Python is a 
high-level, interpreted programming language known for its readability.', 'SLM 
(Small Language Models) are compact AI models designed for specific tasks.', 
'JavaScript is a scripting language primarily used for creating interactive 
web pages.'], 'max_length': 1024}, result=[('Markdown is a lightweight markup 
language with plain-text formatting syntax.', 0.7915633916854858), ('SLM 
(Small Language Models) are compact AI models designed for specific tasks.', 0.
7915633916854858), ('Python is a high-level, interpreted programming language 
known for its readability.', 0.43936243653297424), ('JavaScript is a scripting 
language primarily used for creating interactive web pages.', 0.
3716837763786316)], tool_call_id='call_JKnuvTO1fUQP7PWhyCSQCK7N')]
===========================================================================
"""
