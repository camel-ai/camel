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
Semantic Cache Example
======================

This example demonstrates how to use the SemanticCache to cache LLM responses
and retrieve them based on semantic similarity of queries.

The semantic cache uses vector embeddings to find similar queries, allowing
cache hits even when the exact wording differs from the original query.

This example supports both:
    1. OpenAI (requires OPENAI_API_KEY environment variable)
    2. Sentence Transformers (fully local, no API key required)

Prerequisites:
    - faiss-cpu or faiss-gpu installed for vector storage
    - sentence-transformers (optional, for local embeddings)

Usage:
    python examples/caches/semantic_cache_example.py
"""

import os
import time

from camel.caches import SemanticCache
from camel.embeddings import OpenAIEmbedding, SentenceTransformerEncoder
from camel.storages import FaissStorage
from camel.types import VectorDistance


def main():
    """Demonstrate semantic cache functionality."""

    print("=" * 60)
    print("Semantic Cache Example")
    print("=" * 60)

    # Step 1: Initialize the embedding model
    # Prefer local Sentence Transformers if no API key is found
    print("\n1. Initializing embedding model...")
    if os.environ.get("OPENAI_API_KEY"):
        print("   Using OpenAIEmbedding (requires internet)")
        embedding_model = OpenAIEmbedding()
    else:
        print("   OPENAI_API_KEY not found. Using local SentenceTransformer.")
        embedding_model = SentenceTransformerEncoder(
            model_name="all-MiniLM-L6-v2"
        )

    vector_dim = embedding_model.get_output_dim()
    print(f"   Embedding dimension: {vector_dim}")

    # Step 2: Initialize vector storage (in-memory FAISS)
    print("\n2. Initializing vector storage...")
    vector_storage = FaissStorage(
        vector_dim=vector_dim,
        distance=VectorDistance.COSINE,
    )
    print("   Using FAISS with cosine similarity")

    # Step 3: Create the semantic cache
    print("\n3. Creating semantic cache...")
    cache = SemanticCache(
        embedding_model=embedding_model,
        vector_storage=vector_storage,
        similarity_threshold=0.85,  # 85% similarity required for cache hit
    )
    print(f"   Similarity threshold: {cache.similarity_threshold}")

    # Step 4: Populate the cache with some responses
    print("\n4. Populating cache with sample responses...")

    sample_data = [
        {
            "query": "What is the capital of France?",
            "response": (
                "The capital of France is Paris. Paris is known for "
                "landmarks like the Eiffel Tower and the Louvre Museum."
            ),
        },
        {
            "query": "Explain machine learning in simple terms.",
            "response": (
                "Machine learning is a type of artificial intelligence "
                "that enables computers to learn from data and improve "
                "their performance without being explicitly programmed."
            ),
        },
        {
            "query": "What is Python programming language?",
            "response": (
                "Python is a high-level, interpreted programming language "
                "known for its clear syntax and readability. It's widely "
                "used for web development, data science, and automation."
            ),
        },
    ]

    for item in sample_data:
        cache_id = cache.set(
            query=item["query"],
            response=item["response"],
            metadata={"source": "example"},
        )
        print(f"   Cached: '{item['query'][:40]}...' (id: {cache_id[:8]}...)")

    print(f"   Cache size: {cache.size} entries")

    # Step 5: Test cache lookups with similar queries
    print("\n5. Testing cache lookups with similar queries...")

    test_queries = [
        # Should hit - semantically similar
        "What's the capital city of France?",
        "Tell me about machine learning",
        "What is the Python programming language used for?",
        # Should miss - different topics
        "What is the weather like today?",
        "How do I cook pasta?",
    ]

    print("\n" + "-" * 60)
    for query in test_queries:
        start_time = time.time()
        result = cache.get_with_score(query)
        lookup_time = (time.time() - start_time) * 1000  # ms

        if result:
            response, similarity, record = result
            print(f"   Query: '{query}'")
            print(f"   ✓ CACHE HIT (similarity: {similarity:.2%})")
            print(f"   Response: '{response[:60]}...'")
            print(f"   Lookup time: {lookup_time:.2f}ms\n")
        else:
            print(f"   Query: '{query}'")
            print("   ✗ CACHE MISS")
            print(f"   Lookup time: {lookup_time:.2f}ms\n")
    print("-" * 60)

    # Step 6: Demonstrate deduplication (Replacement)
    print("\n6. Demonstrating deduplication (automatic replacement)...")
    print(f"   Current cache size: {cache.size}")

    updated_query = "What is Python?"
    updated_response = "Python is a versatile and popular scripting language!"
    print(f"   Setting updated response for similar query: '{updated_query}'")

    cache.set(updated_query, updated_response)
    print(f"   Cache size after update: {cache.size} (should still be 3)")

    # Verify the update
    res = cache.get(updated_query)
    print(f"   Verified response: '{res}'")

    # Step 7: Show cache statistics
    print("\n7. Cache Statistics:")
    stats = cache.stats
    print(f"   Total entries: {stats['size']}")
    print(f"   Cache hits: {stats['hits']}")
    print(f"   Cache misses: {stats['misses']}")
    print(f"   Hit rate: {stats['hit_rate']:.2%}")

    # Step 8: Demonstrate find_similar
    print("\n8. Finding similar cached queries (threshold-agnostic)...")
    query = "How does ML work?"
    similar = cache.find_similar(query, top_k=3)
    print(f"   Query: '{query}'")
    for i, (record, similarity) in enumerate(similar, 1):
        print(
            f"   {i}. '{record.query[:50]}...' (similarity: {similarity:.2%})"
        )

    # Step 9: Demonstrate cache management
    print("\n9. Cache management operations...")

    # Disable cache
    cache.enabled = False
    print(
        f"   Cache disabled. Lookup for 'What is Python?': "
        f"{cache.get('What is Python?')}"
    )

    # Clear cache
    cache.clear()
    print(f"   Cache cleared. Size: {cache.size}")

    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
