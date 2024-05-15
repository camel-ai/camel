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
from typing import List, Union

from camel.functions import OpenAIFunction
from camel.retrievers import AutoRetriever
from camel.types import StorageType


def information_retrieval(
    query: str, content_input_paths: Union[str, List[str]]
) -> str:
    r"""Retrieves information from a local vector storage based on the
    specified query. This function connects to a local vector storage system
    and retrieves relevant information by processing the input query. It is
    essential to use this function when the answer to a question requires
    external knowledge sources.

    Args:
        query (str): The question or query for which an answer is required.
        content_input_paths (Union[str, List[str]]): Paths to local
            files or remote URLs.

    Returns:
        str: The information retrieved in response to the query, aggregated
            and formatted as a string.

    Example:
        # Retrieve information about CAMEL AI.
        information_retrieval(query = "what is CAMEL AI?",
                            content_input_paths="https://www.camel-ai.org/")
    """
    auto_retriever = AutoRetriever(
        vector_storage_local_path="camel/temp_storage",
        storage_type=StorageType.QDRANT,
    )

    retrieved_info = auto_retriever.run_vector_retriever(
        query=query, content_input_paths=content_input_paths, top_k=3
    )
    return retrieved_info


# add the function to OpenAIFunction list
RETRIEVAL_FUNCS: List[OpenAIFunction] = [
    OpenAIFunction(func)
    for func in [
        information_retrieval,
    ]
]
