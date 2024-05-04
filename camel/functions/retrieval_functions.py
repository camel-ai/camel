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

def information_retrieval(query: str, content_input_paths: Union[str, List[str]]) -> str:
    r"""Performs an auto retrieal for information. Given a query,
    this function will retrieve the information from the remote vector storage,
    and return the retrieved information back. It is useful for information
    retrieve.

    Args:
        query (string): Question you want to be answered.
        content_input_paths (Union[str, List[str]]): Paths to local
            files or remote URLs.

    Returns:
        str: Aggregated information retrieved in response to the query.

    Example:
        information_retrieval(query = "what is camel?",content_input_paths=["https://lablab.ai/t/camel-tutorial-building-communicative-agents-for-large-scale-language-model-exploration", "https://www.camel-ai.org/"])
    """
    auto_retriever = AutoRetriever(
            url_and_api_key=("Your Milvus URI","Your Milvus Token"),
            storage_type=StorageType.MILVUS)

    retrieved_info = auto_retriever.run_vector_retriever(
        query=query,
        content_input_paths=content_input_paths,
        top_k=3
    )
    return retrieved_info

# add the function to OpenAIFunction list
RETRIEVAL_FUNCS: List[OpenAIFunction] = [
    OpenAIFunction(func)
    for func in [
        information_retrieval,
    ]
]