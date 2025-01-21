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
from typing import Any, Dict, List, Optional

import numpy as np

from camel.loaders import UnstructuredIO
from camel.retrievers import BaseRetriever
from camel.utils import dependencies_required

DEFAULT_TOP_K_RESULTS = 1


class ElasticRetriever(BaseRetriever):
    r"""An Elasticsearch retriever for retrieving relevant information using a
    query-based approach.
    Default similarity model is BM25.
    
    Attributes:
        host (str): The host URL of the Elasticsearch server.
        index_name (str): The name of the index in Elasticsearch.
        index_kwargs (Dict[str, Any]): Optional index settings and mappings.
        es (Elasticsearch): An instance of the Elasticsearch client.
        unstructured_modules (UnstructuredIO): A module for parsing files and
            URLs and chunking content based on specified parameters.
    
    """

    @dependencies_required("elasticsearch")
    def __init__(
        self,
        host: str,
        index_name: str,
        auth_kwargs: Dict[str, Any],
        create_index: bool = True,
        index_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        r"""Initializes the ElasticRetriever.
        
        Args:
            host (str): The host URL of the Elasticsearch server.
            index_name (str): The name of the index in Elasticsearch.
            auth_kwargs (Dict[str, Any]): Authentication parameters for
                Elasticsearch.
            create_index (bool, optional): Whether to create an index in
                Elasticsearch. Defaults to True.
            index_kwargs (Dict[str, Any], optional): Optional index settings
                and mappings. Defaults to None.
                
        Raises:
            ValueError: If the connection to Elasticsearch fails.
        """

        from elasticsearch import Elasticsearch

        self.host = host
        self.index_name = index_name
        self.index_kwargs = index_kwargs

        self.es = Elasticsearch(self.host, **auth_kwargs)
        if not self.es.ping():
            raise ValueError("Connection to Elasticsearch failed.")
        if create_index:
            self.create_index()

        self.unstructured_modules: UnstructuredIO = UnstructuredIO()

    def create_index(self) -> None:
        r"""Creates an index in Elasticsearch."""
        if self.es.indices.exists(index=self.index_name):
            raise ValueError(f"Index {self.index_name} already exists.")
        if not self.index_kwargs:
            self.index_kwargs = {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "similarity": {"default": {"type": "BM25"}},
                },
                "mappings": {
                    "properties": {
                        "text": {"type": "text"},
                        "metadata": {"type": "object"},
                    }
                },
            }
        self.es.indices.create(index=self.index_name, body=self.index_kwargs)

    def process(
        self,
        content_input_path: str,
        chunk_type: str = "chunk_by_title",
        meta_data: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        r"""Processes content from a file or URL, divides it into chunks by
        using `Unstructured IO`,then stored internally. This method must be
        called before executing queries with the retriever.

        Args:
            content_input_path (str): File path or URL of the content to be
                processed.
            chunk_type (str): Type of chunking going to apply. Defaults to
                "chunk_by_title".
            meta_data (Dict[str, Any], optional): Additional metadata to be
                stored with the content. Defaults to None.
            **kwargs (Any): Additional keyword arguments for content parsing.
        """
        from elasticsearch.helpers import bulk

        # Load and preprocess documents
        elements = self.unstructured_modules.parse_file_or_url(
            content_input_path, **kwargs
        )
        if elements:
            chunks = self.unstructured_modules.chunk_elements(
                chunk_type=chunk_type, elements=elements
            )

            datas = [
                {"text": str(chunk), "metadata": meta_data or {}}
                for chunk in chunks
            ]
            actions = [
                {"_index": self.index_name, "_source": data} for data in datas
            ]
            bulk(self.es, actions)


    def query(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K_RESULTS,
    ) -> List[Dict[str, Any]]:
        r"""Executes a query and compiles the results.

        Args:
            query (str): Query string for information retriever.
            top_k (int, optional): The number of top results to return during
                retriever. Must be a positive integer. Defaults to
                `DEFAULT_TOP_K_RESULTS`.

        Returns:
            List[Dict[str]]: Concatenated list of the query results.
        """

        if top_k <= 0:
            raise ValueError("top_k must be a positive integer.")
        if self.bm25 is None or not self.chunks:
            raise ValueError("BM25 model is not initialized. Call `process` first.")

        body = {
            "query": {
                "match": {
                    "text": query
                }
            }
        }
        res = self.es.search(index=self.index_name, body=body, size=top_k)
        return res["hits"]["hits"]