import pandas as pd
import os

import chromadb
from chromadb.utils import embedding_functions
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

from camel.utils.commons import create_chunks

default_ef = embedding_functions.DefaultEmbeddingFunction()

class Chromadb:
    def __init__(self, embedding_function=default_ef, distance="cosine"):
        self.df = pd.DataFrame()
        self.client = chromadb.EphemeralClient()
        self.embedding_function = embedding_function
        self.collection = self.client.create_collection(name='content',
                                                        embedding_function=self.embedding_function,
                                                        metadata={"hnsw:space": distance})

    def set_embedding_function(self, model,  distance="cosine"):
        if model in {"all-MiniLM-L6-v2", "sentencetransformer"}:
            embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2")
        elif model in {"text-embedding-ada-002", "openaiembedding"}:
            embedding_function = OpenAIEmbeddingFunction(
                api_key=os.environ.get('OPENAI_API_KEY'),
                model_name="text-embedding-ada-002")
        else:
            embedding_function = default_ef

        self.embedding_function = embedding_function
        self.collection = self.client.create_collection(name='content',
                                                        embedding_function=self.embedding_function,
                                                        metadata={"hnsw:space": distance})

    def add_text(self, texts, max_len=512, metadata=None):
        chunks = create_chunks(texts, max_len)
        ids = [i+self.count() for i in range(1, len(chunks)+1)]
        self.df = pd.DataFrame({'id': ids, 'text': chunks})
        self.df['id'] = self.df['id'].apply(str)
        self.collection.add(
            ids=self.df['id'].tolist(),
            documents=self.df['text'].tolist(),
            metadatas=metadata
        )

    def add_csv(self, path, metadata=None):
        self.df = pd.read_csv(path)
        self.df['id'] = self.df['id'].apply(lambda x: x+self.count())
        self.df['id'] = self.df['id'].apply(str)
        self.collection.add(
            ids=self.df['id'].tolist(),
            documents=self.df['text'].tolist(),
            metadatas=metadata
        )

    def add_csv_with_embedding(self, path, metadata=None):
        self.df = pd.read_csv(path)
        self.df['id'] = self.df['id'].apply(lambda x: x + self.count())
        self.df['id'] = self.df['id'].apply(str)
        self.collection.add(
            ids=self.df['id'].tolist(),
            documents=self.df['text'].tolist(),
            embeddings=self.df['embedding'].tolist(),
            metadatas=metadata
        )

    def add_embedding(self, embeddings, ids, metadata=None):
        self.collection.add(
            ids=[str(_id) for _id in ids],
            embeddings=embeddings,
            metadatas=metadata
        )

    def query_texts(self, query_texts, n_results=10, where=None, where_document=None):
        """
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

    def query_embeddings(self, query_embeddings, n_results=10, where=None, where_document=None):
        """"
            query_embeddings=[[11.1, 12.1, 13.1],[1.1, 2.3, 3.2], ...],
            n_results=10,
            where={"metadata_field": "is_equal_to_this"},
            where_document={"$contains":"search_string"}
        """
        return self.collection.query(
                    query_embeddings=query_embeddings,
                    n_results=n_results,
                    where=where,
                    where_document=where_document
                )

    def query_texts_named_collection(self, collection_name, query_texts, n_results=10, where=None, where_document=None):
        collection = self.get_collection(collection_name)
        return collection.query(
                    query_texts=query_texts,
                    n_results=n_results,
                    where=where,
                    where_document=where_document
                )

    def query_embeddings_named_collection(self, collection_name, query_embeddings, n_results=10, where=None, where_document=None):
        collection = self.get_collection(collection_name)
        return collection.query(
                    query_texts=query_embeddings,
                    n_results=n_results,
                    where=where,
                    where_document=where_document
                )

    def create_collection(self, collection_name: str, embedding_function=default_ef, metadata=None):
        collection = self.client.create_collection(
            name=collection_name,
            embedding_function=embedding_function,
            metadata=metadata)
        return collection

    def get_collection(self, collection_name: str):
        collection = self.client.get_or_create_collection(name=collection_name)
        return collection

    def change_name(self, collection_name: str, new_name: str):
        collection = self.get_collection(collection_name)
        collection.modify(name=new_name)

    def change_self_name(self, new_name: str):
        self.collection.modify(name=new_name)

    def update(self, ids, documents, embediings=None, metadatas=None):
        """
            ids=["id1", "id2", "id3", ...],
            embeddings=[[1.1, 2.3, 3.2], [4.5, 6.9, 4.4], [1.1, 2.3, 3.2], ...],
            metadatas=[{"chapter": "3", "verse": "16"},
                       {"chapter": "3", "verse": "5"},
                       {"chapter": "29", "verse": "11"}, ...],
            documents=["doc1", "doc2", "doc3", ...],
        """
        self.collection.update(
            ids=ids,
            embeddings=embediings,
            metadatas=metadatas,
            documents=documents,
        )

    def delete_ids(self, ids, where=None):
        """
            ids=["id1", "id2", "id3", ...],
            where={"chapter": "20"}
        """
        self.collection.delete(
            ids=ids,
            where=where
        )

    def list_collection(self):
        return self.client.list_collections()

    def count_named_collection(self, collection_name):
        collection = self.get_collection(collection_name)
        return collection.count()

    def get(self):
        return self.collection.get()

    def get_named_collection(self, collection_name):
        collection = self.get_collection(collection_name)
        return collection.get()

    def count(self):
        return self.collection.count()

    def peek(self):
        return self.collection.peek()

    def delete(self, collection_name='content'):
        self.client.delete_collection(name=collection_name)
