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
from typing import List, Optional, Tuple

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
        device: Optional[str] = None,
    ) -> None:
        r"""Initializes a new instance of the JinaRerankerToolkit class.

        Args:
            timeout (Optional[float]): The timeout value for API requests
                in seconds. If None, no timeout is applied.
                (default: :obj:`None`)
            device (Optional[str]): Device to load the model on. If None,
                will use CUDA if available, otherwise CPU.
                (default: :obj:`None`)
        """
        import torch
        from transformers import AutoModel

        super().__init__(timeout=timeout)

        self.model = AutoModel.from_pretrained(
            'jinaai/jina-reranker-m0',
            torch_dtype="auto",
            trust_remote_code=True,
        )
        DEVICE = (
            device
            if device is not None
            else ("cuda" if torch.cuda.is_available() else "cpu")
        )
        self.model.to(DEVICE)
        self.model.eval()

    def _sort_documents(
        self, documents: List[str], scores: List[float]
    ) -> List[Tuple[str, float]]:
        r"""Sort documents by their scores in descending order.

        Args:
            documents (List[str]): List of documents to sort.
            scores (List[float]): Corresponding scores for each document.

        Returns:
            List[Tuple[str, float]]: Sorted list of (document, score) pairs.

        Raises:
            ValueError: If documents and scores have different lengths.
        """
        if len(documents) != len(scores):
            raise ValueError("Number of documents must match number of scores")
        doc_score_pairs = list(zip(documents, scores))
        doc_score_pairs.sort(key=lambda x: x[1], reverse=True)

        return doc_score_pairs

    def rerank_text_documents(
        self,
        query: str,
        documents: List[str],
        max_length: int = 1024,
    ) -> List[Tuple[str, float]]:
        r"""Reranks text documents based on their relevance to a text query.

        Args:
            query (str): The text query for reranking.
            documents (List[str]): List of text documents to be reranked.
            max_length (int): Maximum token length for processing.
                (default: :obj:`1024`)

        Returns:
            List[Tuple[str, float]]: A list of tuples containing
                the reranked documents and their relevance scores.
        """
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
    ) -> List[Tuple[str, float]]:
        r"""Reranks image documents based on their relevance to a text query.

        Args:
            query (str): The text query for reranking.
            documents (List[str]): List of image URLs or paths to be reranked.
            max_length (int): Maximum token length for processing.
                (default: :obj:`2048`)

        Returns:
            List[Tuple[str, float]]: A list of tuples containing
                the reranked image URLs/paths and their relevance scores.
        """
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
    ) -> List[Tuple[str, float]]:
        r"""Reranks text documents based on their relevance to an image query.

        Args:
            image_query (str): The image URL or path used as query.
            documents (List[str]): List of text documents to be reranked.
            max_length (int): Maximum token length for processing.
                (default: :obj:`2048`)

        Returns:
            List[Tuple[str, float]]: A list of tuples containing
                the reranked documents and their relevance scores.
        """
        import torch

        if self.model is None:
            raise ValueError("Model has not been initialized.")
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
    ) -> List[Tuple[str, float]]:
        r"""Reranks image documents based on their relevance to an image query.

        Args:
            image_query (str): The image URL or path used as query.
            documents (List[str]): List of image URLs or paths to be reranked.
            max_length (int): Maximum token length for processing.
                (default: :obj:`2048`)

        Returns:
            List[Tuple[str, float]]: A list of tuples containing
                the reranked image URLs/paths and their relevance scores.
        """
        import torch

        if self.model is None:
            raise ValueError("Model has not been initialized.")

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
