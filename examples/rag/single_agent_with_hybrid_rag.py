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
"""
This example demonstrates how to build a single-agent RAG (Retrieval-Augmented
Generation) pipeline using CAMEL's HybridRetriever, which combines dense
vector search with BM25 sparse retrieval for improved context relevance.

Usage:
    Run this script directly to query a Wikipedia article using hybrid RAG:
        $ python examples/rag/single_agent_with_hybrid_rag.py
"""

from camel.agents import ChatAgent
from camel.retrievers import HybridRetriever


def single_agent(query: str) -> str:
    """Answer a query using a hybrid RAG pipeline and a CAMEL ChatAgent.

    This function:
    1. Initialises a HybridRetriever that combines vector (dense) search
       and BM25 (sparse) search.
    2. Ingests content from a URL into the retriever's index.
    3. Retrieves the top-k most relevant chunks for the given query.
    4. Passes the retrieved context to a ChatAgent for answer generation.

    Args:
        query (str): The natural-language question to answer.

    Returns:
        str: The assistant's answer grounded in the retrieved context.
    """
    # System prompt instructs the agent to answer strictly from retrieved context
    assistant_sys_msg = """You are a helpful assistant to answer question,
         I will give you the Original Query and Retrieved Context,
        answer the Original Query based on the Retrieved Context,
        if you can't answer the question just say I don't know."""

    # Initialise the hybrid retriever (vector + BM25)
    hybrid_retriever = HybridRetriever()

    # Ingest content from the target URL into the retriever index
    hybrid_retriever.process(
        content_input_path="https://en.wikipedia.org/wiki/King_Abdullah_University_of_Science_and_Technology"
    )

    # Retrieve the most relevant chunks using both retrieval strategies
    retrieved_info = hybrid_retriever.query(
        query=query,
        top_k=5,              # final number of chunks returned after re-ranking
        vector_retriever_top_k=10,  # candidates from dense vector search
        bm25_retriever_top_k=10,    # candidates from BM25 sparse search
    )

    # Build the user message from retrieved context and run the agent
    user_msg = str(retrieved_info)
    agent = ChatAgent(assistant_sys_msg)

    # Get response from the agent
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