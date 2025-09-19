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
import json
import os
from typing import Any, Dict, List, Optional

import requests

from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.utils import MCPServer


@MCPServer()
class JinaRerankerToolkit(BaseToolkit):
    r"""A class representing a toolkit for reranking documents
    using Jina Reranker.

    This class provides methods for reranking documents (text or images)
    based on their relevance to a given query using the Jina Reranker model.
    """

    def __init__(
        self,
        timeout: Optional[float] = None,
        model_name: str = "jinaai/jina-reranker-m0",
        device: Optional[str] = None,
        use_api: bool = True,
    ) -> None:
        r"""Initializes a new instance of the JinaRerankerToolkit class.

        Args:
            timeout (Optional[float]): The timeout value for API requests
                in seconds. If None, no timeout is applied.
                (default: :obj:`None`)
            model_name (str): The reranker model name.
                (default: :obj:`"jinaai/jina-reranker-m0"`)
            device (Optional[str]): Device to load the model on. If None,
                will use CUDA if available, otherwise CPU.
                Only effective when use_api=False.
                (default: :obj:`None`)
            use_api (bool): A flag to switch between local model and API.
                (default: :obj:`True`)
        """

        super().__init__(timeout=timeout)

        self.use_api = use_api
        self.model_name = model_name

        if self.use_api:
            self.model = None
            self._api_key = os.environ.get("JINA_API_KEY", "None")
            if self._api_key == "None":
                raise ValueError(
                    "Missing or empty required API keys in "
                    "environment variables\n"
                    "You can obtain the API key from https://jina.ai/reranker/"
                )
            self.url = 'https://api.jina.ai/v1/rerank'
            self.headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': f'Bearer {self._api_key}',
            }
        else:
            import torch
            from transformers import AutoModel

            self.model = AutoModel.from_pretrained(
                self.model_name,
                torch_dtype="auto",
                trust_remote_code=True,
            )
            self.device = (
                device
                if device is not None
                else ("cuda" if torch.cuda.is_available() else "cpu")
            )
            self.model.to(self.device)
            self.model.eval()

    def _sort_documents(
        self, documents: List[str], scores: List[float]
    ) -> List[Dict[str, object]]:
        r"""Sort documents by their scores in descending order.

        Args:
            documents (List[str]): List of documents to sort.
            scores (List[float]): Corresponding scores for each document.

        Returns:
            List[Dict[str, object]]: Sorted list of (document, score) pairs.

        Raises:
            ValueError: If documents and scores have different lengths.
        """
        if len(documents) != len(scores):
            raise ValueError("Number of documents must match number of scores")
        doc_score_pairs = list(zip(documents, scores))
        doc_score_pairs.sort(key=lambda x: x[1], reverse=True)

        results = [
            {'document': {'text': doc}, 'relevance_score': score}
            for doc, score in doc_score_pairs
        ]

        return results

    def _call_jina_api(self, data: Dict[str, Any]) -> List[Dict[str, object]]:
        r"""Makes a call to the JINA API for reranking.

        Args:
            data (Dict[str]): The data to be passed into the api body.

        Returns:
            List[Dict[str, object]]: A list of dictionary containing
                the reranked documents and their relevance scores.
        """
        try:
            response = requests.post(
                self.url,
                headers=self.headers,
                data=json.dumps(data),
                timeout=self.timeout,
            )
            response.raise_for_status()
            results = [
                {key: value for key, value in _res.items() if key != 'index'}
                for _res in response.json()['results']
            ]
            return results
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to get response from Jina AI: {e}")

    def rerank_text_documents(
        self,
        query: str,
        documents: List[str],
        max_length: int = 1024,
    ) -> List[Dict[str, object]]:
        r"""Reranks text documents based on their relevance to a text query.

        Args:
            query (str): The text query for reranking.
            documents (List[str]): List of text documents to be reranked.
            max_length (int): Maximum token length for processing.
                (default: :obj:`1024`)

        Returns:
            List[Dict[str, object]]: A list of dictionary containing
                the reranked documents and their relevance scores.
        """

        data = {
            'model': self.model_name,
            'query': query,
            'top_n': len(documents),
            'documents': documents,
            'return_documents': True,
        }

        if self.use_api:
            return self._call_jina_api(data)

        else:
            import torch

            if self.model is None:
                raise ValueError(
                    "Model has not been initialized or failed to initialize."
                )

            with torch.inference_mode():
                text_pairs = [[query, doc] for doc in documents]
                scores = self.model.compute_score(
                    text_pairs, max_length=max_length, doc_type="text"
                )

        return self._sort_documents(documents, scores)

    def rerank_image_documents(
        self,
        query: str,
        documents: List[str],
        max_length: int = 2048,
    ) -> List[Dict[str, object]]:
        r"""Reranks image documents based on their relevance to a text query.

        Args:
            query (str): The text query for reranking.
            documents (List[str]): List of image URLs or paths to be reranked.
            max_length (int): Maximum token length for processing.
                (default: :obj:`2048`)

        Returns:
            List[Dict[str, object]]: A list of dictionary containing
                the reranked image URLs/paths and their relevance scores.
        """
        data = {
            'model': self.model_name,
            'query': query,
            'top_n': len(documents),
            'documents': documents,
            'return_documents': True,
        }

        if self.use_api:
            return self._call_jina_api(data)

        else:
            import torch

            if self.model is None:
                raise ValueError(
                    "Model has not been initialized or failed to initialize."
                )

            with torch.inference_mode():
                image_pairs = [[query, doc] for doc in documents]
                scores = self.model.compute_score(
                    image_pairs, max_length=max_length, doc_type="image"
                )

        return self._sort_documents(documents, scores)

    def image_query_text_documents(
        self,
        image_query: str,
        documents: List[str],
        max_length: int = 2048,
    ) -> List[Dict[str, object]]:
        r"""Reranks text documents based on their relevance to an image query.

        Args:
            image_query (str): The image URL or path used as query.
            documents (List[str]): List of text documents to be reranked.
            max_length (int): Maximum token length for processing.
                (default: :obj:`2048`)

        Returns:
            List[Dict[str, object]]: A list of dictionary containing
                the reranked documents and their relevance scores.
        """
        data = {
            'model': self.model_name,
            'query': image_query,
            'top_n': len(documents),
            'documents': documents,
            'return_documents': True,
        }

        if self.use_api:
            return self._call_jina_api(data)

        else:
            import torch

            if self.model is None:
                raise ValueError(
                    "Model has not been initialized or failed to initialize."
                )

            with torch.inference_mode():
                image_pairs = [[image_query, doc] for doc in documents]
                scores = self.model.compute_score(
                    image_pairs,
                    max_length=max_length,
                    query_type="image",
                    doc_type="text",
                )

            return self._sort_documents(documents, scores)

    def image_query_image_documents(
        self,
        image_query: str,
        documents: List[str],
        max_length: int = 2048,
    ) -> List[Dict[str, object]]:
        r"""Reranks image documents based on their relevance to an image query.

        Args:
            image_query (str): The image URL or path used as query.
            documents (List[str]): List of image URLs or paths to be reranked.
            max_length (int): Maximum token length for processing.
                (default: :obj:`2048`)

        Returns:
            List[Dict[str, object]]: A list of dictionary containing
                the reranked image URLs/paths and their relevance scores.
        """
        data = {
            'model': self.model_name,
            'query': image_query,
            'top_n': len(documents),
            'documents': documents,
            'return_documents': True,
        }

        if self.use_api:
            return self._call_jina_api(data)

        else:
            import torch

            if self.model is None:
                raise ValueError(
                    "Model has not been initialized or failed to initialize."
                )

            with torch.inference_mode():
                image_pairs = [[image_query, doc] for doc in documents]
                scores = self.model.compute_score(
                    image_pairs,
                    max_length=max_length,
                    query_type="image",
                    doc_type="image",
                )

            return self._sort_documents(documents, scores)

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        return [
            FunctionTool(self.rerank_text_documents),
            FunctionTool(self.rerank_image_documents),
            FunctionTool(self.image_query_text_documents),
            FunctionTool(self.image_query_image_documents),
        ]
