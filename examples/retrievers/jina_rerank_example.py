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
Example demonstrating the use of JinaRerankRetriever for re-ranking
retrieved documents using Jina AI's reranker model.

Prerequisites:
    - Set `JINA_API_KEY` environment variable or pass it directly
    - Get your API key from https://jina.ai/

Usage:
    python examples/retrievers/jina_rerank_example.py
"""

from camel.retrievers import JinaRerankRetriever


def main():
    # Sample documents to demonstrate reranking
    sample_documents = [
        {
            'text': """CAMEL is an open-source library for building
            communicative AI agents. It enables multi-agent collaboration
            through role-playing and task decomposition.""",
            'metadata': {'source': 'camel_docs', 'page': 1},
        },
        {
            'text': """The weather forecast shows sunny skies with
            temperatures reaching 75°F. A perfect day for outdoor
            activities and picnics.""",
            'metadata': {'source': 'weather', 'page': 1},
        },
        {
            'text': """AI alignment research focuses on ensuring that
            artificial intelligence systems behave in accordance with
            human values and intentions. This is crucial for safe AI
            development.""",
            'metadata': {'source': 'ai_safety', 'page': 1},
        },
        {
            'text': """Large language models have revolutionized natural
            language processing. They can understand and generate
            human-like text across many domains.""",
            'metadata': {'source': 'llm_overview', 'page': 1},
        },
        {
            'text': """Multi-agent systems allow multiple AI entities to
            work together on complex tasks. CAMEL provides tools for
            building such collaborative agent frameworks.""",
            'metadata': {'source': 'multi_agent', 'page': 1},
        },
    ]

    # Initialize the Jina Reranker
    # API key will be read from JINA_API_KEY environment variable
    jina_reranker = JinaRerankRetriever(
        model_name="jina-reranker-v2-base-multilingual"
    )

    # Query to search for
    query = "How do AI agents collaborate in CAMEL framework?"

    print(f"Query: {query}\n")
    print("=" * 60)

    # Before reranking - show original order
    print("\nOriginal document order (by initial retrieval):")
    for i, doc in enumerate(sample_documents):
        print(f"  {i + 1}. {doc['text'][:80]}...")

    # Rerank the documents using Jina AI
    print("\n" + "=" * 60)
    print("\nReranked results (by Jina AI relevance):")

    reranked_results = jina_reranker.query(
        query=query,
        retrieved_result=sample_documents,
        top_k=3,  # Return top 3 most relevant
    )

    for i, result in enumerate(reranked_results):
        print(f"\n  Rank {i + 1} (Score: {result['similarity score']:.4f}):")
        print(f"    Source: {result['metadata']['source']}")
        print(f"    Text: {result['text'][:100]}...")

    print("\n" + "=" * 60)
    print("\nThe reranker has reordered documents by relevance to the query.")
    print(
        "Notice how documents about CAMEL and multi-agent"
        "systems are ranked higher."
    )


if __name__ == "__main__":
    main()
