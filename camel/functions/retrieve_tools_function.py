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
import torch
from transformers import AutoModel, AutoTokenizer

from camel.functions.openai_function import OpenAIFunction


def embed_text(text: str, model: AutoModel, tokenizer: AutoTokenizer):
    r"""
    Embed text using chosen model and tokenizer.
    """
    inputs = tokenizer(text, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)

    return outputs.last_hidden_state.mean(dim=1).squeeze().cpu().numpy()


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    if np.linalg.norm(vec1) * np.linalg.norm(vec2) == 0:
        return 0
    else:
        return np.dot(vec1, vec2) / (
            np.linalg.norm(vec1) * np.linalg.norm(vec2)
        )


def retrieve_tools(
    query: str, tools: List[OpenAIFunction], k: int = 3
) -> Optional[List[OpenAIFunction]]:
    r"""Using semantic search to retrieve relevent tools
    OpenAI / Open source Embedding models to embed the query and the schemas / docstring of `OpenAIFunction`
    Find the most relevent ones based on their embedding vectors

    Args:
        query (str): input question
        tools (List): The tools to be searched.
        k (int): how many answers the user wants to get.

    Returns:
        retrieved_tools (List): List of retrieved (most relevant) tools.
    """
    # Check if k is greater than 0
    assert k > 0, "k must be greater than 0"

    # Check if tools is not empty
    assert tools, "tools is empty"

    # Check not all descriptions are None
    assert any(
        func.func.__doc__ is not None for func in tools
    ), "All docstrings are None"

    tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
    model = AutoModel.from_pretrained("bert-base-uncased")

    query_embedding = embed_text(query, model, tokenizer)

    similarities = []
    for func in tools:
        text = func.func.__doc__ if func.func.__doc__ else ""
        func_embedding = embed_text(text, model, tokenizer)
        similarity = cosine_similarity(query_embedding, func_embedding)
        similarities.append((similarity, func))

    similarities.sort(key=lambda x: x[0], reverse=True)
    if similarities[0][0] < 0.4:
        return None
    else:
        retrieved_tools = [func for _, func in similarities[:k]]
        return retrieved_tools


# An example:
# Input: [get_weather_data, search_google_and_summarize, create_tweet, add]
# retrieved_tools = retrieve_tools(
#     'how is the weather today',
#     tools=[*SEARCH_FUNCS, *WEATHER_FUNCS],
#     k=2,
# )
# print(retrieved_tools)
# get_weather_data, search_google_and_summarize


# RETRIEVE_TOOLS_FUNCS: List[OpenAIFunction] = [
#     OpenAIFunction(func)  # type: ignore[arg-type]
#     for func in [retrieve_tools]
# ]
