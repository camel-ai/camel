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


from typing import Dict, List, Literal, Optional

import numpy as np
from pydantic import BaseModel
from sklearn.metrics.pairwise import cosine_similarity

from camel.embeddings.base import BaseEmbedding


class DeduplicationResult(BaseModel):
    """
    The result of deduplication.

    Attributes:
        original_texts (List[str]): The original texts.
        unique_ids (List[int]): A list of ids that are unique (not duplicates).
        unique_embeddings_dict (Dict[int, List[float]]):
            A mapping from the index of each unique text to its embedding.
        duplicate_to_target_map (Dict[int, int]):
            A mapping from the index of the duplicate text to the index
            of the text it is considered a duplicate of.
    """

    original_texts: List[str]
    unique_ids: List[int]
    unique_embeddings_dict: Dict[int, List[float]]
    duplicate_to_target_map: Dict[int, int]


def deduplicate_internally(
    texts: List[str],
    threshold: float = 0.65,
    embedding_instance: Optional[BaseEmbedding[str]] = None,
    embeddings: Optional[List[List[float]]] = None,
    strategy: Literal["top1", "llm-supervise"] = "top1",
) -> DeduplicationResult:
    """
    Deduplicate a list of strings based on their cosine similarity.

    You can either:
    1) Provide a Camel `BaseEmbedding` instance via `embedding_instance` to let
        this function handle the embedding internally, OR
    2) Directly pass a list of pre-computed embeddings to `embeddings`.

    If both `embedding_instance` and `embeddings` are provided, the function
    will raise a ValueError to avoid ambiguous usage.

    strategy is used to specify different strategies, where 'top1' selects the
    one with highest similarity, and 'llm-supervise' uses LLM to determine if
    texts are duplicates (not yet implemented).

    Args:
        texts (List[str]): The list of texts to be deduplicated.
        threshold (float, optional): The similarity threshold for considering
            two texts as duplicates. Default is 0.65.
        embedding_instance (Optional[BaseEmbedding[str]], optional):
            A Camel embedding instance for automatic embedding. Defaults to
            None.
        embeddings (Optional[List[List[float]]], optional):
            Pre-computed embeddings of `texts`. Each element in the list
            corresponds to the embedding of the text in the same index of
            `texts`. Defaults to None.
        strategy (Literal["top1", "llm-supervise"], optional):
            The strategy to use for deduplication. Defaults to "top1".

    Returns:
        DeduplicationResult: An object that contains:
            - `original_texts`: The original texts.
            - `unique_ids`: The unique ids after deduplication.
            - `unique_embeddings_dict`: A dict mapping from (unique) text id
              to its embedding.
            - `duplicate_to_target_map`: A dict mapping from the id of a
              duplicate text to the id of the text it is considered a duplicate
              of.

    Raises:
        NotImplementedError: If the strategy is not "top1".
        ValueError: If neither embeddings nor embedding_instance is provided,
                    or if both are provided at the same time.
        ValueError: If the length of `embeddings` does not match the length of
            `texts`.

    Example:
        >>> from camel.embeddings.openai_embedding import OpenAIEmbedding
        >>> # Suppose we have 5 texts, some of which may be duplicates
        >>> texts = [
        ...     "What is AI?",
        ...     "Artificial Intelligence is about machines",
        ...     "What is AI?",
        ...     "Deep Learning is a subset of AI",
        ...     "What is artificial intelligence?"
        ... ]
        >>> # or any other BaseEmbedding instance
        >>> embedding_model = OpenAIEmbedding()
        >>> result = deduplicate_internally(
        ...     texts=texts,
        ...     threshold=0.7,
        ...     embedding_instance=embedding_model
        ... )
        >>> print("Unique ids:")
        >>> for uid in result.unique_ids:
        ...     print(texts[uid])
        Unique ids:
        What is AI?
        Artificial Intelligence is about machines
        Deep Learning is a subset of AI
        What is artificial intelligence?

        >>> print("Duplicate map:")
        >>> print(result.duplicate_to_target_map)
        {2: 0}
        # This indicates the text at index 2 is considered
        # a duplicate of index 0.
    """
    if strategy == "llm-supervise":
        # TODO: Implement LLM-supervise deduplication.
        raise NotImplementedError(
            "LLM-supervise deduplication is not yet implemented."
        )

    # Check if the parameters are valid.
    if embedding_instance is None and embeddings is None:
        raise ValueError(
            "Either 'embedding_instance' or 'embeddings' must be provided."
        )
    if embedding_instance is not None and embeddings is not None:
        raise ValueError(
            "Cannot provide both 'embedding_instance' and 'embeddings'. "
            "Please choose only one way to supply embeddings."
        )

    if embedding_instance is not None:
        # Use Camel's embedding_instance to vectorize.
        embeddings = embedding_instance.embed_list(texts)
    else:
        # Use pre-supplied embeddings.
        if len(embeddings) != len(texts):
            raise ValueError(
                "The length of 'embeddings' does not match the length "
                "of 'texts'."
            )

    # Calculate cosine similarity.
    similarity_matrix = cosine_similarity(embeddings)
    n = len(texts)

    # Use the lower triangle to avoid redundant comparisons
    # (or self-comparisons).
    tril_mask = np.tril(np.ones((n, n)), k=-1)
    similarity_matrix = similarity_matrix * tril_mask

    # For each row, find the column with the highest similarity
    # that exceeds the threshold. If no similarity exceeds the threshold,
    # set the column index to -1.
    masked_similarities = np.where(
        similarity_matrix > threshold, similarity_matrix, -1
    )
    max_indices = masked_similarities.argmax(axis=1)

    duplicate_to_target_map: Dict[int, int] = {}
    above_threshold = similarity_matrix[np.arange(n), max_indices] > threshold

    # Construct the "duplicate->target" mapping.
    for i in range(n):
        if above_threshold[i]:
            duplicate_to_target_map[i] = max_indices[i]

    # Get the actual unique ids and embeddings.
    unique_ids = []
    unique_embeddings_dict = {}

    for i, (_, emb) in enumerate(zip(texts, embeddings)):
        if i not in duplicate_to_target_map:
            unique_ids.append(i)
            unique_embeddings_dict[i] = emb

    return DeduplicationResult(
        original_texts=texts,
        unique_ids=unique_ids,
        unique_embeddings_dict=unique_embeddings_dict,
        duplicate_to_target_map=duplicate_to_target_map,
    )
