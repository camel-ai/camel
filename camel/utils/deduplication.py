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

from pydantic import BaseModel

from camel.embeddings.base import BaseEmbedding


class DeduplicationResult(BaseModel):
    r"""The result of deduplication.

    Attributes:
        original_texts (List[str]): The original texts.
        unique_ids (List[int]): A list of ids that are unique (not duplicates).
        unique_embeddings_dict (Dict[int, List[float]]): A mapping from the
            index of each unique text to its embedding.
        duplicate_to_target_map (Dict[int, int]): A mapping from the index of
            the duplicate text to the index of the text it is considered a
            duplicate of.
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
    batch_size: int = 1000,
) -> DeduplicationResult:
    r"""Deduplicate a list of strings based on their cosine similarity.

    You can either:
    1) Provide a CAMEL `BaseEmbedding` instance via `embedding_instance` to let
        this function handle the embedding internally, OR
    2) Directly pass a list of pre-computed embeddings to `embeddings`.

    If both `embedding_instance` and `embeddings` are provided, the function
    will raise a ValueError to avoid ambiguous usage.

    strategy is used to specify different strategies, where 'top1' selects the
    one with highest similarity, and 'llm-supervise' uses LLM to determine if
    texts are duplicates.

    Args:
        texts (List[str]): The list of texts to be deduplicated.
        threshold (float, optional): The similarity threshold for considering
            two texts as duplicates. (default: :obj:`0.65`)
        embedding_instance (Optional[BaseEmbedding[str]], optional):
            A CAMEL embedding instance for automatic embedding. (default:
            :obj:`None`)
        embeddings (Optional[List[List[float]]], optional):
            Pre-computed embeddings of `texts`. Each element in the list
            corresponds to the embedding of the text in the same index of
            `texts`. (default: :obj:`None`)
        strategy (Literal["top1", "llm-supervise"], optional):
            The strategy to use for deduplication. (default: :obj:`"top1"`)
        batch_size (int, optional): The size of the batch to use for
            calculating cosine similarities. (default: :obj:`1000`)

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
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity

    if len(texts) == 0:
        return DeduplicationResult(
            original_texts=[],
            unique_ids=[],
            unique_embeddings_dict={},
            duplicate_to_target_map={},
        )

    if len(texts) == 1:
        return DeduplicationResult(
            original_texts=texts,
            unique_ids=[0],
            unique_embeddings_dict={
                0: embeddings[0]
                if embeddings
                else embedding_instance.embed_list(texts)[0] if embedding_instance else [0.0]  # type: ignore[union-attr]
            },
            duplicate_to_target_map={},
        )

    # Check if the parameters are valid.
    if not 0 <= threshold <= 1:
        raise ValueError("Threshold must be between 0 and 1")

    if embedding_instance is None and embeddings is None:
        raise ValueError(
            "Either 'embedding_instance' or 'embeddings' must be provided."
        )
    if embedding_instance is not None and embeddings is not None:
        raise ValueError(
            "Cannot provide both 'embedding_instance' and 'embeddings'. "
            "Please choose only one way to supply embeddings."
        )

    if strategy == "llm-supervise":
        return _deduplicate_with_llm_supervision(
            texts=texts,
            threshold=threshold,
            embedding_instance=embedding_instance,
            embeddings=embeddings,
            batch_size=batch_size,
        )

    if embedding_instance is not None:
        # Use Camel's embedding_instance to vectorize.
        embeddings = embedding_instance.embed_list(texts)
    else:
        # Use pre-supplied embeddings.
        if embeddings and len(embeddings) != len(texts):
            raise ValueError(
                "The length of 'embeddings' does not match the length "
                "of 'texts'."
            )

    # Convert embeddings to numpy array for efficient computation
    embeddings_array = np.array(embeddings)
    n = len(texts)
    duplicate_to_target_map: Dict[int, int] = {}

    # Process in batches to reduce memory usage
    for i in range(0, n, batch_size):
        batch_end = min(i + batch_size, n)
        # Calculate cosine similarity for current batch
        batch_similarities = cosine_similarity(
            embeddings_array[i:batch_end], embeddings_array[:batch_end]
        )

        # Create mask for lower triangle (avoid self-comparison and redundant
        # checks)
        tril_mask = np.tril(np.ones_like(batch_similarities), k=-1)
        batch_similarities = batch_similarities * tril_mask

        # Find duplicates in current batch
        masked_similarities = np.where(
            batch_similarities > threshold, batch_similarities, -1
        )
        max_indices = masked_similarities.argmax(axis=1)
        above_threshold = (
            batch_similarities[np.arange(batch_end - i), max_indices]
            > threshold
        )

        # Update duplicate map
        for j, is_duplicate in enumerate(above_threshold):
            if is_duplicate:
                duplicate_to_target_map[i + j] = max_indices[j]

    # Get the actual unique ids and embeddings.
    unique_ids = []
    unique_embeddings_dict = {}

    assert embeddings, "embeddings must be valid"

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


def _deduplicate_with_llm_supervision(
    texts: List[str],
    threshold: float,
    embedding_instance: Optional[BaseEmbedding[str]],
    embeddings: Optional[List[List[float]]],
    batch_size: int,
) -> DeduplicationResult:
    r"""Deduplicate texts using LLM supervision.
    
    This function uses embeddings to find potential duplicates, then uses an LLM
    to determine if they are actually duplicates.
    
    Args:
        texts: List of texts to deduplicate
        threshold: Similarity threshold for initial filtering
        embedding_instance: Embedding instance for computing embeddings
        embeddings: Pre-computed embeddings
        batch_size: Batch size for processing
        
    Returns:
        DeduplicationResult with LLM-supervised deduplication results
    """
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity
    
    # First, get embeddings if not provided
    if embedding_instance is not None:
        embeddings = embedding_instance.embed_list(texts)
    elif embeddings is None:
        raise ValueError(
            "Either 'embedding_instance' or 'embeddings' must be provided."
        )
    
    if len(embeddings) != len(texts):
        raise ValueError(
            "The length of 'embeddings' does not match the length of 'texts'."
        )
    
    # Convert embeddings to numpy array
    embeddings_array = np.array(embeddings)
    n = len(texts)
    duplicate_to_target_map: Dict[int, int] = {}
    
    # Find potential duplicates using cosine similarity
    potential_duplicates = []
    
    for i in range(0, n, batch_size):
        batch_end = min(i + batch_size, n)
        batch_similarities = cosine_similarity(
            embeddings_array[i:batch_end], embeddings_array[:batch_end]
        )
        
        # Create mask for lower triangle
        tril_mask = np.tril(np.ones_like(batch_similarities), k=-1)
        batch_similarities = batch_similarities * tril_mask
        
        # Find pairs above threshold
        for j in range(batch_end - i):
            for k in range(j):
                if batch_similarities[j, k] > threshold:
                    potential_duplicates.append((i + j, k))
    
    # Use LLM to determine actual duplicates
    if potential_duplicates:
        duplicate_pairs = _llm_judge_duplicates(texts, potential_duplicates)
        
        # Build duplicate map
        for duplicate_idx, target_idx in duplicate_pairs:
            duplicate_to_target_map[duplicate_idx] = target_idx
    
    # Get unique ids and embeddings
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


def _llm_judge_duplicates(
    texts: List[str], 
    potential_duplicates: List[tuple[int, int]]
) -> List[tuple[int, int]]:
    r"""Use LLM to judge if potential duplicate pairs are actually duplicates.
    
    Args:
        texts: List of all texts
        potential_duplicates: List of (duplicate_idx, target_idx) pairs
        
    Returns:
        List of (duplicate_idx, target_idx) pairs that LLM judged as duplicates
    """
    try:
        # Import here to avoid circular import issues
        from camel.models import ModelFactory
        from camel.types import ModelPlatformType
        from camel.types.enums import ModelType
        
        # Create a simple LLM model for judgment
        # Using a lightweight model for efficiency
        llm_model = ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.GPT_3_5_TURBO,
        )
        
        actual_duplicates = []
        
        for duplicate_idx, target_idx in potential_duplicates:
            text1 = texts[duplicate_idx]
            text2 = texts[target_idx]
            
            # Create prompt for LLM judgment
            prompt = f"""You are a text deduplication expert. Your task is to determine if two texts are duplicates or near-duplicates.

Text 1: "{text1}"
Text 2: "{text2}"

Are these texts duplicates or near-duplicates? Consider:
- Semantic similarity
- Information overlap
- Whether they convey the same meaning

Respond with only "YES" if they are duplicates, or "NO" if they are not duplicates."""

            try:
                # Get LLM response
                response = llm_model.run([{"role": "user", "content": prompt}])
                judgment = response.choices[0].message.content.strip().upper()
                
                if judgment == "YES":
                    actual_duplicates.append((duplicate_idx, target_idx))
                    
            except Exception as e:
                # If LLM fails, default to keeping both texts (no deduplication)
                print(f"LLM judgment failed for pair {duplicate_idx}-{target_idx}: {e}")
                continue
                
        return actual_duplicates
        
    except Exception as e:
        print(f"Failed to initialize LLM for deduplication: {e}")
        # Fallback: return empty list (no deduplication)
        return []
