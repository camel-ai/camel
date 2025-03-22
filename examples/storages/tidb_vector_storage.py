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

from camel.storages.vectordb_storages import (
    TiDBStorage,
    VectorDBQuery,
    VectorRecord,
)

"""
Before the DATABASE_URL, you can setup the a TiDB database cluster first:

(Option 1): TiDB Serverless

1. Go to [TiDB Cloud](https://tidbcloud.com/console/clusters) to create 
    a serverless cluster
2. Click the **Connect** button
3. Select "SQLAlchemy" > "PyMySQL" for the **Connect With** option, then 
    you can get the DATABASE_URL like:

DATABASE_URL="mysql+pymysql://<USERNAME>:<PASSWORD>@<HOST>:4000/test&ssl_verify_cert=true&ssl_verify_identity=true"

(Option 2): TiDB playground cluster on local

1. Install TiUP via command:

```
curl --proto '=https' --tlsv1.2 -sSf \
    https://tiup-mirrors.pingcap.com/install.sh | sh
```

2. Deploy a playground cluster via command: `tiup playground`
3. The DATABASE_URL should be like: "mysql+pymysql://root:@localhost:4000/test"
"""

DATABASE_URL = "mysql+pymysql://root:@localhost:4000/test"


def main():
    # Create an instance of TiDBStorage with dimension = 4
    tidb_storage = TiDBStorage(
        url_and_api_key=(DATABASE_URL, ''),
        vector_dim=4,
        collection_name="my_collection",
    )

    # Add two vector records
    tidb_storage.add(
        [
            VectorRecord(
                vector=[-0.1, 0.1, -0.1, 0.1],
                payload={'key1': 'value1'},
            ),
            VectorRecord(
                vector=[-0.1, 0.1, 0.1, 0.1],
                payload={'key2': 'value2'},
            ),
        ]
    )

    # Query similar vectors
    query_results = tidb_storage.query(
        VectorDBQuery(query_vector=[0.1, 0.2, 0.1, 0.1], top_k=1)
    )
    for result in query_results:
        print(result.record.payload, result.similarity)

    """
    Output:
    {'key2': 'value2'} 0.5669466755703252
    """

    # Clear all vectors
    tidb_storage.clear()


if __name__ == "__main__":
    main()
