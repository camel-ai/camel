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
from camel.retrievers import HybridRetriever


def single_agent(query: str) -> str:
    # Set agent role
    assistant_sys_msg = """You are a helpful assistant to answer question,
         I will give you the Original Query and Retrieved Context,
        answer the Original Query based on the Retrieved Context,
        if you can't answer the question just say I don't know."""

    hybrid_retriever = HybridRetriever()
    hybrid_retriever.process(
        content_input_path="https://en.wikipedia.org/wiki/King_Abdullah_University_of_Science_and_Technology"
    )

    retrieved_info = hybrid_retriever.query(
        query=query,
        top_k=5,
        vector_retriever_top_k=10,
        bm25_retriever_top_k=10,
    )

    # Pass the retrieved information to agent
    user_msg = str(retrieved_info)
    agent = ChatAgent(assistant_sys_msg)

    # Get response
    assistant_response = agent.step(user_msg)
    return assistant_response.msg.content


print(single_agent("What is it like to be a visiting student at KAUST?"))
'''
===============================================================================
Being a visiting student at KAUST involves participating in the Visiting
Student Program (VS), which is designed for 3rd or 4th year undergraduate
or master's students. This program allows students to work directly with KAUST
faculty members for a duration that can range from a few days to several
months. Accepted students typically receive a monthly stipend, and their
accommodation, health insurance, and travel costs are covered. This support
makes the experience financially manageable and allows students to focus on
their research and learning during their time at KAUST.
===============================================================================
'''
