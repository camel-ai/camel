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
from typing import List, Dict

import chromadb
import pandas as pd
from camel.utils.commons import create_chunks
from chromadb.utils import embedding_functions
# from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction


default_ef = embedding_functions.DefaultEmbeddingFunction()
# sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
# openai_ef = embedding_functions.OpenAIEmbeddingFunction(
#                 api_key="YOUR_API_KEY",
#                 model_name="text-embedding-ada-002"
#             )

class Chromadb:
    """
    The embedding function takes text as input, and performs tokenization and
    embedding. If no embedding function is supplied, Chroma will use sentence
    transfomer as a default.
    By default, chromadb run in memory. Setting pesistent=True, you can
    configure Chroma to save and load from your local machine. Data will be
    persisted automatically and loaded on start (if it exists). The path is
    where Chroma will store its database files on disk, and load them on start.
    https://docs.trychroma.com/usage-guide
    """
    def __init__(self,
                 embedding_function=default_ef,
                 distance="cosine",
                 persistent=False,
                 name='content',
                 path="./save"):
        """
        args:
            embedding_function: how you embed data, using the Sentence
                Transformers all-MiniLM-L6-v2 model by default. Chroma supports
                OpenAIEmbeddingFunction, also can use any Sentence Transformers
                model to create embeddings.
            distance: caculate the similarity, Valid options are "l2", "ip, "or
                "cosine".
            persistent: save and load from local or memory.
            name: each collection has an unique name to identify itself, if you
                creat two collections with the same name will cause error.
            path: The path is where Chroma will store its database files on
                disk, and load them on start.
        """
        self.df = pd.DataFrame()
        if persistent:
            self.client = chromadb.PersistentClient(path=path)
        else:
            self.client = chromadb.EphemeralClient()
        self.embedding_function = embedding_function
        self.collection = self.client.get_or_create_collection(
                name=name,
                embedding_function=self.embedding_function,
                metadata={"hnsw:space": distance})

    def add_text(self, texts: str, max_len: int = 512, metadata: Dict = None):
        """
        If Chroma is passed a list of documents, it will automatically tokenize
        and embed them with the collection's embedding function (the default
        will be used if none was supplied at collection creation). Chroma will
        also store the documents themselves.
        args:
            texts: the data need to be stored.
            max_len: texts will be split to small chunks.
            metadata: An optional list of metadata dictionaries can be supplied
                for each document, to store additional information and enable
                filtering.
        """
        # Split the texts to a list of chunks.
        chunks = create_chunks(texts, max_len)
        # Each document must have a unique associated id.
        ids = [i + self.collection.count() for i in range(1, len(chunks) + 1)]
        self.df = pd.DataFrame({'id': ids, 'text': chunks})
        self.df['id'] = self.df['id'].apply(str)
        ids = self.df['id'].tolist()
        # An empty ids list will cause error.
        if ids:
            self.collection.add(
                ids=ids,
                documents=self.df['text'].tolist(),
                metadatas=metadata
            )

    def query_texts(self,
                    query_texts: [str | List[str]],
                    n_results: int = 10,
                    where: Dict = None,
                    where_document: Dict = None):
        """
        The query will return the n_results closest matches to each
        query_embedding, in order. An optional where filter dictionary can be
        supplied to filter by the metadata associated with each document.
        Additionally, an optional where_document filter dictionary can be
        supplied to filter by contents of the document.

        args:
            query_texts: You can also query by a set of query_texts. Chroma will
                first embed each query_text with the collection's embedding
                function, and then perform the query with the generated embedding.
            n_results: how many result you want. Each result contains about 512
                words.
            where: filter by the metadata associated with each document.
            where_document: filter by contents of the document.

        example:
            query_texts=["doc10", "thus spake zarathustra", ...],
                n_results=10,
                where={"metadata_field": "is_equal_to_this"},
                where_document={"$contains": "search_string"}
        """
        return self.collection.query(
            query_texts=query_texts,
            n_results=n_results,
            where=where,
            where_document=where_document
        )

    def query_texts_named_collection(self, collection_name: str, query_texts: str,
                                     n_results: int = 10, where: Dict = None,
                                     where_document: Dict = None):
        """
        query a named collection.
        args:
            query_texts: You can also query by a set of query_texts. Chroma will
                first embed each query_text with the collection's embedding
                function, and then perform the query with the generated embedding.
            n_results: how many result you want. Each result contains about 512
                words.
            where: filter by the metadata associated with each document.
            where_document: filter by contents of the document.

        """
        collection = self.client.get_collection(collection_name)
        return collection.query(
            query_texts=query_texts,
            n_results=n_results,
            where=where,
            where_document=where_document
        )

    def create_collection(self, collection_name: str,
                          embedding_function=default_ef, metadata: Dict = None):
        """
        Chroma collections are created with a name and an optional embedding function.
        """
        collection = self.client.create_collection(
            name=collection_name,
            embedding_function=embedding_function,
            metadata=metadata)
        return collection

    def list_collection_name(self):
        """
        list all collections' name.
        """
        names = []
        for collection in self.client.list_collections():
            names.append(collection.name)
        return names

    def update(self, ids: List[str], documents: List[str], embediings=None,
               metadatas: Dict = None):
        """
        Any property of items in a collection can be updated using .update.
        If an id is not found in the collection, an error will be logged and the
        update will be ignored. If documents are supplied without corresponding
        embeddings, the embeddings will be recomupted with the collection's
        embedding function. If the supplied embeddings are not the same dimension
        as the collection, an exception will be raised.

        example:
            ids=["id1", "id2", "id3", ...],
            embeddings=[[1.1, 2.3, 3.2], [4.5, 6.9, 4.4], [1.1, 2.3, 3.2], ...],
            metadatas=[{"chapter": "3", "verse": "16"},
                       {"chapter": "3", "verse": "5"},
                       {"chapter": "29", "verse": "11"}, ...],
            documents=["doc1", "doc2", "doc3", ...],
        """
        if ids:
            self.collection.update(
                ids=ids,
                embeddings=embediings,
                metadatas=metadatas,
                documents=documents,
            )

    def delete_ids(self, ids: List[str], where: Dict = None):
        """
        Chroma supports deleting items from a collection by id using .delete.
        The embeddings, documents, and metadata associated with each item will
        be deleted.
        Naturally, this is a destructive operation, and cannot be undone.

        example:
            ids=["id1", "id2", "id3", ...],
            where={"chapter": "20"}
        """
        if ids:
            self.collection.delete(
                ids=ids,
                where=where
            )
