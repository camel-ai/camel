# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
from typing import List, Optional

import numpy as np

from camel.embeddings.sentence_transformers_embeddings import (
    SentenceTransformerEncoder,
)
from camel.functions.openai_function import OpenAIFunction


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    r"""Compute the cosine similarity between two sentence embedding vectors.

    Args:
        vec1 (List): the first sentence embedding vector.
        vec2 (List): the second sentence embedding vector.
    """
    if np.linalg.norm(vec1) * np.linalg.norm(vec2) == 0.0:
        return 0
    else:
        return np.dot(vec1, vec2) / (
            np.linalg.norm(vec1) * np.linalg.norm(vec2)
        )


def retrieve_tools(
    query: str, tools: List[OpenAIFunction], k: int = 3, sim_thres: float = 0.71
) -> Optional[List[OpenAIFunction]]:
    r"""Using semantic search to retrieve relevent tools. OpenAI / Open source
    Embedding models to embed the query and the schemas / docstring of
    `OpenAIFunction`. Find the most relevent ones based on their embedding vectors.

    Args:
        query (str): input question.
        tools (List): The tools to be searched.
        k (int): how many answers the user wants to get.
        sim_thres (int): 0.4 # The threshold above which we want to accept a tool.

    Returns:
        retrieved_tools (List): List of retrieved (most relevant) tools.
    """
    # Check if k is greater than 0
    if k <= 0:
        print("Illegal input, k must be greater than 0")
        # Set k to default value
        k = 3

    # Check if tools is not empty
    if not tools:
        print("Illegal input, tools is empty")
        return []

    # Check not all descriptions are None
    if not any(func.func.__doc__ is not None for func in tools):
        print("Warning: All docstrings are None")

    # Check if sim_thres is between 0 and 1
    if sim_thres <= 0 or sim_thres > 1:
        print("Illegal input, sim_thres must be between 0 and 1")
        # Set sim_thres to default value
        sim_thres = 0.71

    encoder = SentenceTransformerEncoder()

    query_embedding = encoder.embed(query)

    similarities = []
    for func in tools:
        text = func.func.__doc__ if func.func.__doc__ else ""
        func_embedding = encoder.embed(func.func.__name__ + ': ' + text)

        similarity = cosine_similarity(query_embedding, func_embedding)
        similarities.append((similarity, func))

    similarities.sort(key=lambda x: x[0], reverse=True)

    if similarities[0][0] < sim_thres:
        return []
    else:
        retrieved_tools = [func for _, func in similarities[:k]]
        return retrieved_tools
