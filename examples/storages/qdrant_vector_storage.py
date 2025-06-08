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
import random

from camel.storages.vectordb_storages import (
    QdrantStorage,
    VectorDBQuery,
    VectorDBSearch,
    VectorRecord,
)

"""
Before using the DATABASE_URL, you can set up a Qdrant vector database cluster:

(Option 1): ☁️ Qdrant Cloud (Official Hosted Service)

1. Visit [Qdrant Cloud](https://cloud.qdrant.io) and sign up or log in.
2. Create a free or paid cluster.
3. Go to the **Connect** section of your cluster dashboard.
4. Copy your **Cluster URL** (e.g., https://your-cluster.cloud.qdrant.io).
5. Generate an **API Key** in the "Settings" > "API Keys" section.
6. Set up your connection using:

   DATABASE_URL = ("https://your-cluster.cloud.qdrant.io", "your-api-key")


"""
uri = "https://132b2d40-b5d8-4e50-9235-781c30d92956.us-west-1-0.aws.cloud.qdrant.io"
token = "replace-this-with-your-api-key"
DATABASE_URL = (uri, token)


def main():
    # Create an instance of MilvusStorage with dimension = 4
    qdrant_storage = QdrantStorage(
        url_and_api_key=(DATABASE_URL),
        vector_dim=4,
        collection_name="my_collection",
    )

    # Add two vector records
    records = []
    for i in range(100):
        vector = [random.uniform(-1, 1) for _ in range(4)]
        payload = {"group": "A" if i % 2 == 0 else "B", "index": i}
        records.append(VectorRecord(vector=vector, payload=payload))
    qdrant_storage.add(records)

    qdrant_storage.load()

    # Query similar vectors
    query_results = qdrant_storage.query(
        VectorDBQuery(query_vector=[0.1, 0.2, 0.1, 0.1], top_k=1)
    )
    for result in query_results:
        print(result.record.payload, result.similarity)

    """
    Output:
    {'group': 'B', 'index': 59} 0.9667742848396301
    """

    search_results = qdrant_storage.search(
        VectorDBSearch(
            payload_filter={"group": {"$eq": "A"}},
            top_k=2,
        )
    )
    for result in search_results:
        print(result.record.payload)

    """
    Output:
    {'group': 'A', 'index': 98}
    {'group': 'A', 'index': 6}
    """


if __name__ == "__main__":
    main()
