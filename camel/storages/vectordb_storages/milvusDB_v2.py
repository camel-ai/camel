from pymilvus import MilvusClient, Collection
from typing import Any, Dict, List, Optional, Tuple, Union, cast
import uuid

from camel.storages.vectordb_storages import (
    BaseVectorStorage,
    VectorDBQuery,
    VectorDBQueryResult,
    VectorDBStatus,
    VectorRecord,
)

class MilvusStorage(BaseVectorStorage):
    """
    This module is to integration of Milvus, a vector database, into Camel agent.
    The information of Milvus can be accessed to Milvus websites at: https://milvus.io/docs

    Args:
        vector_dim (int): The dimenstion of storing vectors.
        collection_name (Optional[str], optional): Name for the collection in
            the Milvus. If not provided, set it to the current time with iso
            format. (default: :obj:`None`)
        url_and_api_key (Optional[Tuple[str, str]], optional): Tuple containing
            the URL and API key for connecting to a remote Milvus instance.
            (default: :obj:`None`)
        path (Optional[str], optional): Path to a directory for initializing a
            local Milvus client. (default: :obj:`None`)
        distance (VectorDistance, optional): The distance metric for vector
            comparison (default: :obj:`VectorDistance.COSINE`)
        **kwargs (Any): Additional keyword arguments for initializing
            `MilvusClient`.
    """

    # Initialize the MilvusStorage class with required parameters
    def __init__(self, vector_dim: int, url_and_api: Tuple[str, str], collection_name: Optional[str] = None, **kwargs: Any) -> None:
        self._client: MilvusClient
        self.vector_dim = vector_dim
        self.create_client(url_and_api, **kwargs)   
        self.collection_name = self.create_collection()

    # Create a Milvus client using the provided URL and API key
    def create_client(self, url_and_api_key: Tuple[str, str], **kwargs: Any) -> None:
        self._client = MilvusClient(uri=url_and_api_key[0], token=url_and_api_key[1], **kwargs)

    # Create a new collection in Milvus with a unique name and vector dimensions
    def create_collection(self, **kwargs: Any,) -> str:
        try:    
            collection_name  = self.generate_collection_name()
            self._client.create_collection(collection_name = collection_name, dimension = self.vector_dim, **kwargs,)
            return collection_name
        except Exception as e:
            print(f"Failed to create collection: {e}")
            raise 

    # Delete a specified collection from Milvus 
    def delete_collection(self, collection_name: str) -> None:
        self._client.drop_collection(collection_name=collection_name)

    # Generate a unique collection name using UUID
    def generate_collection_name(self) -> str:
        return str(uuid.uuid4())

    # Add vector records to the collection    
    def add(self, records: List[VectorRecord], **kwargs) -> None:
        try:
            vectors = [record.vector for record in records]
            ids = [record.id for record in records] if hasattr(records[0], 'id') else None
            self._client.insert(collection_name=self.collection_name, entities=vectors, ids=ids, **kwargs)
            self._client.flush()
        except Exception as e:
            print(f"Failed to add records: {e}")
            raise
    
    # Delete specified vector records from the collection using their IDs
    def delete(self, ids: List[str],**kwargs: Any) -> None:
        results = self._client.delete(collection_name=self.collection_name, pks=ids, **kwargs)

    # Retrieve the current status of the collection, including vector dimensions and count
    def status(self) -> VectorDBStatus:
        collection = Collection(self.collection_name)
        return VectorDBStatus(
            vector_dim = collection.schema.fields[-1].params['dim'], 
            vector_count = len(collection.indexes))
    
    # Query the collection for similar vector records based on a given vector
    def query(self, query: VectorDBQuery, **kwargs: Any) -> List[VectorDBQueryResult]:
        search_results = self._client.search(collection_name=self.collection_name, data=query.query_vector, limit=query.top_k, **kwargs)
        query_results = [VectorDBQueryResult(similarity=(1 - point.distance), id=str(point.id)) for point in search_results]
        return query_results

    # Clear the collection by deleting and recreating it
    def clear(self) -> None:
        self.delete_collection(self.collection_name)
        self.collection_name  = self.create_collection()

    # Provide access to the private Milvus client instance
    @property
    def client(self) -> Any:
        return self._client