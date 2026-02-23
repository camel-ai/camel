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
Semantic Cache Live Test (Fully Local)
======================================

Tests SemanticCache with FAISS + SentenceTransformer.
No API keys required — everything runs locally.

Usage:
    python examples/caches/test_semantic_cache_live.py
"""

import logging
import time

from camel.caches import SemanticCache
from camel.embeddings import SentenceTransformerEncoder
from camel.storages import FaissStorage
from camel.types import VectorDistance

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("camel.caches")
logger.setLevel(logging.DEBUG)


def main():
    print("=" * 60)
    print("  Semantic Cache Live Test (Local)")
    print("  FAISS + SentenceTransformer")
    print("=" * 60)

    # 1. Setup — all local, no API keys
    print("\n[1] Initializing...")
    t0 = time.time()
    embedding = SentenceTransformerEncoder(model_name="all-MiniLM-L6-v2")
    dim = embedding.get_output_dim()
    print(f"    Model: all-MiniLM-L6-v2 (dim={dim})")

    storage = FaissStorage(
        vector_dim=dim,
        distance=VectorDistance.COSINE,
    )

    cache = SemanticCache(
        embedding_model=embedding,
        vector_storage=storage,
        similarity_threshold=0.80,
    )
    print(f"    Threshold: {cache.similarity_threshold}")
    print(f"    Init time: {time.time() - t0:.2f}s")

    # 2. Populate cache
    print("\n[2] Populating cache...")
    entries = [
        (
            "What is the capital of France?",
            "Paris is the capital of France.",
        ),
        (
            "Explain machine learning",
            "ML is a subset of AI that learns from data.",
        ),
        (
            "What is Python?",
            "Python is a high-level programming language.",
        ),
    ]
    entry_ids = []
    for query, response in entries:
        t0 = time.time()
        eid = cache.set(query, response)
        entry_ids.append(eid)
        ms = (time.time() - t0) * 1000
        print(f"    SET '{query[:40]}' " f"-> {eid[:8]}... ({ms:.0f}ms)")

    print(f"    Cache size: {cache.size}")

    # 3. Test cache hits (similar queries)
    print("\n[3] Cache HIT tests (similar queries)...")
    hit_queries = [
        "What's the capital of France?",
        "Tell me about machine learning",
        "What is the Python programming language?",
    ]
    for q in hit_queries:
        t0 = time.time()
        result = cache.get_with_score(q)
        ms = (time.time() - t0) * 1000
        if result:
            resp, score, rec = result
            print(f"    HIT  [{score:.2%}] '{q}'")
            print(f"         -> '{resp[:50]}' ({ms:.0f}ms)")
        else:
            print(f"    MISS '{q}' ({ms:.0f}ms)")

    # 4. Test cache misses (unrelated queries)
    print("\n[4] Cache MISS tests (unrelated queries)...")
    miss_queries = [
        "How do I cook pasta?",
        "What is the weather today?",
        "Explain quantum physics",
    ]
    for q in miss_queries:
        t0 = time.time()
        result = cache.get(q)
        ms = (time.time() - t0) * 1000
        status = "MISS" if result is None else "HIT"
        print(f"    {status} '{q}' ({ms:.0f}ms)")

    # 5. Test deduplication (set replaces existing similar entry)
    print("\n[5] Deduplication test...")
    print(f"    Size BEFORE re-set: {cache.size}")

    new_response = "Python is a versatile scripting language!"
    new_id = cache.set("What is Python?", new_response)
    print(f"    Size AFTER re-set:  {cache.size}")
    print(f"    New entry id: {new_id[:8]}...")

    result = cache.get_with_score("What is Python?")
    if result:
        resp, score, _ = result
        print(f"    Response: '{resp}' [{score:.2%}]")
        if resp == new_response:
            print("    PASS: Got the UPDATED response")
        else:
            print("    FAIL: Got the OLD response")
    else:
        print("    FAIL: No result returned")

    # 6. Stats
    print("\n[6] Cache statistics:")
    stats = cache.stats
    for k, v in stats.items():
        if isinstance(v, float):
            print(f"    {k}: {v:.2%}")
        else:
            print(f"    {k}: {v}")

    # 7. find_similar
    print("\n[7] Find similar entries for 'AI and ML':")
    similar = cache.find_similar("AI and ML", top_k=3)
    for i, (rec, sim) in enumerate(similar, 1):
        print(f"    {i}. [{sim:.2%}] '{rec.query}'")

    print("\n" + "=" * 60)
    print("  All tests complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
