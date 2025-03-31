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
    MilvusStorage,
    VectorDBQuery,
    VectorDBSearch,
    VectorRecord,
)

"""
Before the DATABASE_URL, you can setup the a Milvus database cluster first:

(Option 1): ☁️ Milvus Serverless 

1. Go to [Zilliz Cloud](https://zilliz.com/cloud) and create a Milvus 
    serverless instance
2. Click the **Connect** button on your instance dashboard
3. Go to "Cluster Detail" > "Connect" Copy the **Public 
    Endpoint** and **Token**  
4. Pass them as a tuple into MilvusStorage like:

DATABASE_URL = ("https://xxx.api.zillizcloud.com", "your-api-key")
"""

uri = "https://in03-4a0c9f648c49848.serverless.gcp-us-west1.cloud.zilliz.com"
token = "replace-this-with-your-api-key"
DATABASE_URL = (uri, token)


def main():
    # Create an instance of MilvusStorage with dimension = 4
    milvus_storage = MilvusStorage(
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
    milvus_storage.add(records)

    milvus_storage.load()

    # Query similar vectors
    query_results = milvus_storage.query(
        VectorDBQuery(query_vector=[0.1, 0.2, 0.1, 0.1], top_k=1)
    )
    for result in query_results:
        print(result.record.payload, result.similarity)

    """
    Output:
    {'group': 'B', 'index': 59} 0.9667742848396301
    """

    search_results = milvus_storage.search(
        VectorDBSearch(
            payload_filter={"group": {"$eq": "A"}},
            top_k=2,
        )
    )
    for result in search_results:
        print(result.record.payload)

    """
    Output:
    {'group': 'A', 'index': 64}
    {'group': 'A', 'index': 76}
    """


if __name__ == "__main__":
    main()
