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

from typing import List

import pytest

from camel.embeddings.base import BaseEmbedding
from camel.utils import DeduplicationResult, deduplicate_internally


class MockEmbedding(BaseEmbedding[str]):
    r"""A mock embedding class that always returns the same embedding vector
    for any input text. Useful for testing deduplication logic.
    """

    def embed(self, obj: str, **kwargs) -> List[float]:
        return [0.5, 0.5, 0.5]

    def embed_list(self, objs: List[str], **kwargs) -> List[List[float]]:
        return [[0.5, 0.5, 0.5] for _ in objs]

    def get_output_dim(self) -> int:
        return 3


def test_deduplicate_internally_empty_list():
    mock_embedding_instance = MockEmbedding()
    result = deduplicate_internally(
        texts=[],
        threshold=0.9,
        embedding_instance=mock_embedding_instance,
        strategy="top1",
    )
    assert len(result.original_texts) == 0
    assert len(result.unique_ids) == 0
    assert len(result.unique_embeddings_dict) == 0
    assert len(result.duplicate_to_target_map) == 0


def test_deduplicate_internally_single_item():
    mock_embedding_instance = MockEmbedding()
    texts = ["Hello world!"]
    result = deduplicate_internally(
        texts=texts,
        threshold=0.9,
        embedding_instance=mock_embedding_instance,
        strategy="top1",
    )
    assert result.original_texts == texts
    assert result.unique_ids == [0]
    assert len(result.unique_embeddings_dict) == 1
    assert 0 in result.unique_embeddings_dict
    assert len(result.duplicate_to_target_map) == 0


def test_deduplicate_internally_with_mock_embedding():
    texts = ["Hello world!", "Hello world!", "HELLO WORLD!", "Something else"]
    mock_embedding_instance = MockEmbedding()

    result: DeduplicationResult = deduplicate_internally(
        texts=texts,
        threshold=0.9,
        embedding_instance=mock_embedding_instance,
        strategy="top1",
    )

    # Since all embeddings are the same, the first two texts
    # should be considered duplicates with very high similarity,
    # likewise with the third text. So we expect only 1 unique ID
    # if threshold is 0.9.
    assert result.original_texts[0] == "Hello world!"
    assert (
        len(result.unique_ids) == 1
    ), f"Expected 1 unique id, got {len(result.unique_ids)}"

    # Check the mapping. Indices 1 and 2 should map to 0,
    # as duplicates. 3 is a special case here: the embedding is also identical,
    # so it should be a duplicate as well.
    # So total texts = 4, unique = [0], duplicates = [1->0, 2->0, 3->0].
    expected_duplicate_map = {1: 0, 2: 0, 3: 0}
    assert result.duplicate_to_target_map == expected_duplicate_map, (
        f"Expected duplicate map {expected_duplicate_map}, "
        f"got {result.duplicate_to_target_map}"
    )

    # Also verify the returned embeddings
    assert len(result.unique_embeddings_dict) == 1
    assert list(result.unique_embeddings_dict.keys()) == [0]
    assert result.unique_embeddings_dict[0] == [0.5, 0.5, 0.5]


def test_deduplicate_internally_with_precomputed_embeddings():
    texts = ["Text A", "Text B", "Text B (similar)", "Text C"]
    # Embeddings:
    # - index 0 -> [1, 0, 0]
    # - index 1 -> [0, 1, 0]
    # - index 2 -> [0, 0.99, 0] (nearly the same as index 1)
    # - index 3 -> [0, 0, 1]
    embeddings = [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.99, 0.0],
        [0.0, 0.0, 1.0],
    ]

    result: DeduplicationResult = deduplicate_internally(
        texts=texts,
        threshold=0.95,
        embeddings=embeddings,
        # Not providing embedding_instance, so it will use precomputed.
        strategy="top1",
    )

    # We expect "Text B" (index=1) and "Text B (similar)" (index=2) to be
    # duplicates, since their embeddings have high cosine similarity (> 0.95).
    # The others are distinct enough.
    assert (
        len(result.unique_ids) == 3
    ), f"Expected 3 unique ids, got {len(result.unique_ids)}"
    # The duplicates map should reflect that index 2 is mapped to 1
    assert result.duplicate_to_target_map == {
        2: 1
    }, f"Expected {{2: 1}}, got {result.duplicate_to_target_map}"

    # Check correctness of embeddings dictionary
    # We have 3 unique IDs: e.g. [0, 1, 3]
    # (the actual order might vary if threshold leads to a different mapping,
    # but we expect to see them in the unique_embeddings_dict).
    for uid in result.unique_ids:
        assert (
            uid in result.unique_embeddings_dict
        ), f"Missing embedding for unique id {uid}"


def test_deduplicate_internally_chain_scenario():
    r"""Test scenario:
      - A <-> B similarity > threshold
      - B <-> C similarity > threshold
      - C <-> D similarity > threshold
      But A <-> C, B <-> D, A <-> D are all < threshold.
    According to the 'top1' strategy, each new text that is similar to
    a previously seen text will be mapped to the closest one. This creates
    a chain-like mapping where B -> A, C -> B, D -> C. In the end, only
    A is considered truly unique, because every subsequent text maps
    transitively back to A.
    """

    texts = ["A", "B", "C", "D"]
    # Note: We rely on sklearn's cosine_similarity, which normalizes by
    # vector norms. These 2D vectors are chosen so that consecutive pairs
    # (A-B, B-C, C-D) have a cosine similarity > 0.8, while non-consecutive
    # pairs remain < 0.8.
    embeddings = [
        [1.0, 0.0],  # A
        [0.87, 0.5],  # B
        [0.50, 0.87],  # C
        [0.0, 1.0],  # D
    ]

    result: DeduplicationResult = deduplicate_internally(
        texts=texts,
        threshold=0.8,
        embeddings=embeddings,
        strategy="top1",
    )

    # We expect only index 0 ("A") to be truly unique.
    # B (index=1) -> A, C (index=2) -> B, D (index=3) -> C
    # which in the final data structure looks like:
    # duplicate_to_target_map = {1: 0, 2: 1, 3: 2}

    assert (
        len(result.unique_ids) == 1
    ), f"Expected exactly 1 unique id, got {len(result.unique_ids)}"
    assert (
        result.unique_ids[0] == 0
    ), "Expected the only unique id to be index 0"

    expected_map = {1: 0, 2: 1, 3: 2}
    assert result.duplicate_to_target_map == expected_map, (
        f"Expected chain map {expected_map}, "
        f"but got {result.duplicate_to_target_map}"
    )

    # Also check embeddings
    assert len(result.unique_embeddings_dict) == 1, (
        "Expected 1 unique embedding, got "
        f"{len(result.unique_embeddings_dict)}"
    )
    assert (
        0 in result.unique_embeddings_dict
    ), "Missing embedding for the unique text A."
    # Optionally verify the embedding
    assert result.unique_embeddings_dict[0] == [
        1.0,
        0.0,
    ], "Expected 'A' to have embedding [1.0, 0.0]."


def test_deduplicate_internally_with_llm_supervision():
    with pytest.raises(NotImplementedError):
        deduplicate_internally(
            texts=["A", "B", "C"],
            threshold=0.8,
            embedding_instance=MockEmbedding(),
            strategy="llm-supervise",
        )


def test_deduplicate_internally_with_inconsistent_embeddings():
    with pytest.raises(ValueError):
        deduplicate_internally(
            texts=["A", "B", "C"],
            threshold=0.8,
            embeddings=[[1.0, 0.0], [0.0, 1.0]],  # The length of texts is 3,
            # but the length of embeddings is 2.
            strategy="top1",
        )
