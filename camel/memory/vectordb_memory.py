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

from dataclasses import asdict
from typing import List, Optional
from uuid import uuid4

from camel.embedding.base import BaseEmbedding
from camel.embedding.openai_embedding import OpenAiEmbedding
from camel.memory.base_memory import BaseMemory
from camel.memory.vector_storage.base import BaseVectorStorage, VectorRecord
from camel.memory.vector_storage.qdrant import Qdrant
from camel.messages.base import BaseMessage
from camel.typing import VectorDistance


class VectorDBMemory(BaseMemory):
    """
    An implementation of the :obj:`BaseMemory` abstract base class for
    maintaining and retrieving information using vector embeddings within a
    vector database.

    This memory class leverages embeddings to convert chat messages
    into vector representations, which are then stored in a vector database.
    This mechanism facilitates efficient searches based on content similarity,
    enabling functionalities like context retrieval, recommendation, etc.

    Args:
        storage (Optional[BaseVectorStorage], optional): The storage mechanism
            for the vector database. Defaults to in-memory :obj:`Qdrant` if not
            provided. (default: :obj:`None`)
        embedding (Optional[BaseEmbedding], optional): Embedding mechanism to
            convert chat messages into vector representations. Defaults to
            :obj:`OpenAiEmbedding` if not provided. (default: :obj:`None`)
        distance (VectorDistance, optional): The distance metric used in the
            vector database. (default: :obj:`VectorDistance.DOT`)
        collection_name (Optional[str], optional): Desired name for the
            collection within the vector database. If not provided, a unique
            identifier is generated. (default: :obj:`None`)
        del_collection (bool, optional): Determines whether to delete the
            collection upon object destruction. (default: :obj:`False`)
        **kwargs: Additional keyword arguments passing to
            :obj:`create_collection`.
    """

    def __init__(
        self,
        storage: Optional[BaseVectorStorage] = None,
        embedding: Optional[BaseEmbedding] = None,
        distance: VectorDistance = VectorDistance.DOT,
        collection_name: Optional[str] = None,
        del_collection: bool = False,
        **kwargs,
    ) -> None:
        self.storage = storage or Qdrant()
        self.embedding = embedding or OpenAiEmbedding()
        self.vector_dim = self.embedding.get_output_dim()
        self.del_collection = del_collection
        self.distance = distance

        if collection_name is not None:
            try:
                info = self.storage.check_collection(collection_name)
                if info["vector_dim"] != self.vector_dim:
                    raise RuntimeError(
                        "Vector dimension of the existing collection "
                        f"{collection_name} ({info['vector_dim']}) "
                        "is different from the embedding dim "
                        f"({self.vector_dim}).")
                return
            except ValueError:
                pass
        self.collection_name = collection_name or str(uuid4())
        self.storage.create_collection(
            collection=self.collection_name,
            size=self.vector_dim,
            distance=distance,
            **kwargs,
        )

    def __del__(self):
        """
        Destructor that deletes the collection if :obj:`del_collection` is set
        to :obj:`True`.
        """
        if self.del_collection:
            self.storage.delete_collection(self.collection_name)

    def read(
        self,
        current_state: Optional[BaseMessage] = None,
        limit: int = 3,
    ) -> List[BaseMessage]:
        """
        Retrieves similar chat messages from the vector database based on the
        content of the current state message.

        Args:
            current_state (Optional[BaseMessage], optional): **Mandatory.** An
                incoming message representing the current state. This message's
                content will be converted into a vector representation to query
                the database. (default: :obj:`None`)
            limit (int, optional): The maximum number of similar messages to
                retrieve. (default: :obj:`3`).

        Returns:
            List[BaseMessage]: A list of chat messages retrieved from the
                vector database based on similarity to :obj:`current_state`.

        Raises:
            ValueError: If the current state is not provided.
        """
        if current_state is None:
            raise ValueError(
                "Reading vector database memeory without message input is not "
                "allowed.")
        query_vector = self.embedding.embed(current_state.content)
        results = self.storage.search(
            self.collection_name,
            VectorRecord(vector=query_vector),
            limit,
        )
        return [
            BaseMessage(**res.payload) for res in results
            if res.payload is not None
        ]

    def write(self, msgs: List[BaseMessage]) -> None:
        """
        Converts the provided chat messages into vector representations and
        writes them to the vector database.

        Args:
            msgs (List[BaseMessage]): Messages to be added to the vector
                database.
        """
        records = [
            VectorRecord(
                vector=self.embedding.embed(msg.content),
                payload=asdict(msg),
            ) for msg in msgs
        ]

        self.storage.add_vectors(
            collection=self.collection_name,
            vectors=records,
        )

    def clear(self) -> None:
        """
        Clears all vector representations and chat messages from the collection
        and reinitializes the collection in the vector database.
        """
        self.storage.delete_collection(self.collection_name)
        self.storage.create_collection(
            self.collection_name,
            size=self.vector_dim,
            distance=self.distance,
        )
