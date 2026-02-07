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
import os
from typing import Any, Dict, List, Union

import requests

from camel.retrievers import BaseRetriever
from camel.types.enums import JinaRerankerModelType

DEFAULT_TOP_K_RESULTS = 1
JINA_RERANK_API_URL = "https://api.jina.ai/v1/rerank"


class JinaRerankRetriever(BaseRetriever):
    r"""An implementation of the `BaseRetriever` using the `Jina AI Reranker`
    model.

    This retriever uses Jina AI's reranking API to re-order retrieved documents
    based on their relevance to the query. It supports multilingual retrieval
    across 100+ languages.

    Attributes:
        model_name (Union[JinaRerankerModelType, str]): The model name to use
            for re-ranking.
        api_key (str, optional): The API key for authenticating with the
            Jina AI service.

    References:
        https://jina.ai/reranker/
    """

    def __init__(
        self,
        model_name: Union[JinaRerankerModelType, str] = (
            JinaRerankerModelType.JINA_RERANKER_V2_BASE_MULTILINGUAL
        ),
        api_key: str | None = None,
    ) -> None:
        r"""Initializes an instance of the JinaRerankRetriever. This
        constructor sets up the API key for interacting with the Jina AI
        Reranker API.

        Args:
            model_name (Union[JinaRerankerModelType, str]): The name of the
                model to be used for re-ranking. Can be a JinaRerankerModelType
                enum value or a string. Defaults to
                `JinaRerankerModelType.JINA_RERANKER_V2_BASE_MULTILINGUAL`.
            api_key (Optional[str]): The API key for authenticating requests
                to the Jina AI API. If not provided, the method will attempt to
                retrieve the key from the environment variable 'JINA_API_KEY'.

        Raises:
            ValueError: If the API key is neither passed as an argument nor
                set in the environment variable.
        """
        self.api_key = api_key or os.environ.get("JINA_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Must pass in Jina API key or specify via JINA_API_KEY"
                " environment variable."
            )
        # Handle both enum and string values for model_name
        if isinstance(model_name, JinaRerankerModelType):
            self.model_name = model_name.value
        else:
            self.model_name = model_name

    def query(
        self,
        query: str,
        retrieved_result: list[dict[str, Any]],
        top_k: int = DEFAULT_TOP_K_RESULTS,
    ) -> List[Dict[str, Any]]:
        r"""Queries and compiles results using the Jina AI re-ranking model.

        Args:
            query (str): Query string for information retriever.
            retrieved_result (List[Dict[str, Any]]): The content to be
                re-ranked, should be the output from `BaseRetriever` like
                `VectorRetriever`. Each dict should have a 'text' key
                containing the document text.
            top_k (int, optional): The number of top results to return during
                retrieval. Must be a positive integer. Defaults to
                `DEFAULT_TOP_K_RESULTS`.

        Returns:
            List[Dict[str, Any]]: Concatenated list of the query results,
                each containing the original data plus a 'similarity score'.

        Raises:
            requests.exceptions.RequestException: If the API request fails.
        """
        # Extract text content for reranking
        documents = []
        for item in retrieved_result:
            if isinstance(item, dict):
                # Try common keys for text content
                text = item.get('text') or item.get('content') or str(item)
            else:
                text = str(item)
            documents.append(text)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model_name,
            "query": query,
            "documents": documents,
            "top_n": top_k,
        }

        response = requests.post(
            JINA_RERANK_API_URL,
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()

        rerank_response = response.json()

        formatted_results = []
        for result in rerank_response.get("results", []):
            index = result.get("index", 0)
            relevance_score = result.get("relevance_score", 0.0)

            selected_chunk = retrieved_result[index].copy()
            selected_chunk['similarity score'] = relevance_score
            formatted_results.append(selected_chunk)

        return formatted_results
