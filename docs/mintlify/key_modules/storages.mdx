---
title: "Storages"
icon: database
---

## What Are Storages in CAMEL-AI?

<Card icon="database">
The <b>Storage</b> module in CAMEL-AI gives you a **unified interface for saving, searching, and managing your data** from simple key-value records to high-performance vector databases and modern graph engines. It’s your plug-and-play toolkit for building robust, AI-ready storage layers.
</Card>

---
## Types of Storages

<AccordionGroup>

  <Accordion title="Key-Value Storages" icon="database">
    **BaseKeyValueStorage**
    - Abstract base for all key-value storage backends.
    - **Standardizes:** Save, load, clear operations.
    - **Interface:** Python dicts.
    - **Use cases:**
      - JSON file storage
      - NoSQL (MongoDB, Redis)
      - In-memory caches

    **InMemoryKeyValueStorage**
    - Fast, simple, *not persistent* (resets on restart)
    - Ideal for caching, development, or quick prototyping

    **JsonStorage**
    - Human-readable, portable JSON file storage
    - Supports custom JSON encoder (for Enums, etc)
    - Good for configs, small persistent datasets, export/import flows
  </Accordion>

  <Accordion title="VectorDB Storages" icon="file-vector">
    **BaseVectorStorage**
    - Abstract base for vector database backends
    - **Core operations:** Add/query/delete vectors, check DB status
    - **Customizable:** Vector dimensions, collections, distance metrics

    **MilvusStorage**
    - For [Milvus](https://milvus.io/docs/overview.md/) (cloud-native vector search engine)
    - High scalability, real-time search

    **TiDBStorage**
    - For [TiDB](https://pingcap.com/ai) (hybrid vector/relational database)
    - Handles embeddings, knowledge graphs, ops data

    **QdrantStorage**
    - For [Qdrant](https://qdrant.tech/) (open-source vector DB)
    - Fast similarity search for AI/ML

    **OceanBaseStorage**
    - For [OceanBase](https://www.oceanbase.com/) (cloud and on-prem vector DB)
    - Supports large-scale, distributed deployments

    **WeaviateStorage**
    - For [Weaviate](https://weaviate.io/) (open-source vector engine)
    - Schema-based, semantic search, hybrid queries

    **ChromaStorage**
    - For [ChromaDB](https://www.trychroma.com/) (AI-native open-source embedding database)
    - Simple API, scales from notebook to production

    **SurrealStorage**
    - For [SurrealDB](https://surrealdb.com/) (scalable, distributed database with WebSocket support)
    - Efficient vector storage and similarity search with real-time updates

    **PgVectorStorage**
    - For [PostgreSQL with pgvector](https://github.com/pgvector/pgvector) (open-source vector engine)
    - Leverages PostgreSQL for vector search
  </Accordion>

  <Accordion title="Graph Storages" icon="chart-waterfall">
    **BaseGraphStorage**
    - Abstract base for graph database integrations
    - **Supports:**  
      - Schema queries and refresh  
      - Adding/deleting/querying triplets

    **NebulaGraph**
    - For [NebulaGraph](https://www.nebula-graph.io/) (distributed, high-performance graph DB)
    - Scalable, open source

    **Neo4jGraph**
    - For [Neo4jGraph](https://neo4j.com/) (most popular enterprise graph DB)
    - Widely used for graph analytics, recommendations
  </Accordion>

</AccordionGroup>


## Get Started

Here are practical usage patterns for each storage type—pick the ones you need and mix them as you like.

---

<Card title="In-Memory Key-Value Storage" icon="key">
  <b>Use for:</b> Fast, temporary storage. Data is lost when your program exits.  
  <b>Perfect for:</b> Prototyping, testing, in-memory caching.

  <Tabs>
    <Tab title="Python Example">
      ```python
      from camel.storages.key_value_storages import InMemoryKeyValueStorage

      memory_storage = InMemoryKeyValueStorage()
      memory_storage.save([{'key1': 'value1'}, {'key2': 'value2'}])
      records = memory_storage.load()
      print(records)
      memory_storage.clear()
      ```
    </Tab>
    <Tab title="Output">
      ```markdown
      >>> [{'key1': 'value1'}, {'key2': 'value2'}]
      ```
    </Tab>
  </Tabs>
</Card>

---

<Card title="JSON File Storage" icon="files">
  <b>Use for:</b> Persistent, human-readable storage on disk.  
  <b>Perfect for:</b> Logs, local settings, configs, or sharing small data sets.

  <Tabs>
    <Tab title="Python Example">
      ```python
      from camel.storages.key_value_storages import JsonStorage
      from pathlib import Path

      json_storage = JsonStorage(Path("my_data.json"))
      json_storage.save([{'key1': 'value1'}, {'key2': 'value2'}])
      records = json_storage.load()
      print(records)
      json_storage.clear()
      ```
    </Tab>
    <Tab title="Output">
      ```markdown
      >>> [{'key1': 'value1'}, {'key2': 'value2'}]
      ```
    </Tab>
  </Tabs>
</Card>

---

<Card title="Milvus Vector Storage" icon="database">
  <b>Use for:</b> Scalable, high-performance vector search (RAG, embeddings).  
  <b>Perfect for:</b> Semantic search and production AI retrieval.

  <Tabs>
    <Tab title="Python Example">
      ```python
      from camel.storages import MilvusStorage, VectorDBQuery, VectorRecord

      milvus_storage = MilvusStorage(
          url_and_api_key=("Your Milvus URI","Your Milvus Token"),
          vector_dim=4,
          collection_name="my_collection"
      )
      milvus_storage.add([
          VectorRecord(vector=[-0.1, 0.1, -0.1, 0.1], payload={'key1': 'value1'}),
          VectorRecord(vector=[-0.1, 0.1, 0.1, 0.1], payload={'key2': 'value2'}),
      ])
      milvus_storage.load()
      query_results = milvus_storage.query(VectorDBQuery(query_vector=[0.1, 0.2, 0.1, 0.1], top_k=1))
      for result in query_results:
          print(result.record.payload, result.similarity)
      milvus_storage.clear()
      ```
    </Tab>
    <Tab title="Output">
      ```markdown
      >>> {'key2': 'value2'} 0.5669466853141785
      ```
    </Tab>
  </Tabs>
</Card>

---

<Card title="TiDB Vector Storage" icon="vector-square">
  <b>Use for:</b> Hybrid cloud-native storage, vectors + SQL in one.  
  <b>Perfect for:</b> Combining AI retrieval with your business database.

  <Tabs>
    <Tab title="Python Example">
      ```python
      import os
      from camel.storages import TiDBStorage, VectorDBQuery, VectorRecord

      os.environ["TIDB_DATABASE_URL"] = "The database url of your TiDB cluster."
      tidb_storage = TiDBStorage(
          url_and_api_key=(os.getenv("DATABASE_URL"), ''),
          vector_dim=4,
          collection_name="my_collection"
      )
      tidb_storage.add([
          VectorRecord(vector=[-0.1, 0.1, -0.1, 0.1], payload={'key1': 'value1'}),
          VectorRecord(vector=[-0.1, 0.1, 0.1, 0.1], payload={'key2': 'value2'}),
      ])
      tidb_storage.load()
      query_results = tidb_storage.query(VectorDBQuery(query_vector=[0.1, 0.2, 0.1, 0.1], top_k=1))
      for result in query_results:
          print(result.record.payload, result.similarity)
      tidb_storage.clear()
      ```
    </Tab>
    <Tab title="Output">
      ```markdown
      >>> {'key2': 'value2'} 0.5669466755703252
      ```
    </Tab>
  </Tabs>
</Card>


<Card title="Qdrant Vector Storage" icon="square-q">
  <b>Use for:</b> Fast, scalable open-source vector search.  
  <b>Perfect for:</b> RAG, document search, and high-scale retrieval tasks.

  <Tabs>
    <Tab title="Python Example">
      ```python
      from camel.storages import QdrantStorage, VectorDBQuery, VectorRecord

      # Create an instance of QdrantStorage with dimension = 4
      qdrant_storage = QdrantStorage(vector_dim=4, collection_name="my_collection")

      # Add two vector records
      qdrant_storage.add([
          VectorRecord(vector=[-0.1, 0.1, -0.1, 0.1], payload={'key1': 'value1'}),
          VectorRecord(vector=[-0.1, 0.1, 0.1, 0.1], payload={'key2': 'value2'}),
      ])

      # Query similar vectors
      query_results = qdrant_storage.query(VectorDBQuery(query_vector=[0.1, 0.2, 0.1, 0.1], top_k=1))
      for result in query_results:
          print(result.record.payload, result.similarity)

      # Clear all vectors
      qdrant_storage.clear()
      ```
    </Tab>
    <Tab title="Output">
      ```markdown
      >>> {'key2': 'value2'} 0.5669467095138407
      ```
    </Tab>
  </Tabs>
</Card>

---

<Card title="ChromaDB Vector Storage" icon="database">
  <b>Use for:</b> Fastest way to build LLM apps with memory and embeddings.  
  <b>Perfect for:</b> From prototyping in notebooks to production clusters with the same simple API.

  <Tabs>
    <Tab title="Python Example">
      ```python
      from camel.storages import ChromaStorage, VectorDBQuery, VectorRecord
      from camel.types import VectorDistance

      # Create ChromaStorage instance with ephemeral (in-memory) client
      chroma_storage = ChromaStorage(
          vector_dim=4,
          collection_name="camel_example_vectors",
          client_type="ephemeral",  # or "persistent", "http", "cloud"
          distance=VectorDistance.COSINE,
      )

      # Add vector records
      chroma_storage.add([
          VectorRecord(vector=[-0.1, 0.1, -0.1, 0.1], payload={'key1': 'value1'}),
          VectorRecord(vector=[-0.1, 0.1, 0.1, 0.1], payload={'key2': 'value2'}),
      ])

      # Query similar vectors
      query_results = chroma_storage.query(VectorDBQuery(query_vector=[0.1, 0.2, 0.1, 0.1], top_k=1))
      for result in query_results:
          print(result.record.payload, result.similarity)

      # Clear all vectors
      chroma_storage.clear()
      ```
    </Tab>
    <Tab title="Output">
      ```markdown
      >>> {'key2': 'value2'} 0.7834733426570892
      ```
    </Tab>
  </Tabs>
</Card>

---

<Card title="SurrealDB Vector Storage" icon="database">
  <b>Use for:</b> Scalable, distributed vector storage with WebSocket support.
  <b>Perfect for:</b> Real-time vector search with distributed deployments and SQL-like querying.

  <Tabs>
    <Tab title="Python Example">
      ```python
      import os
      from camel.storages import SurrealStorage, VectorDBQuery, VectorRecord

      # Set environment variables for SurrealDB connection
      os.environ["SURREAL_URL"] = "ws://localhost:8000/rpc"
      os.environ["SURREAL_PASSWORD"] = "your_password"

      # Create SurrealStorage instance with WebSocket connection
      surreal_storage = SurrealStorage(
          url=os.getenv("SURREAL_URL"),
          table="camel_vectors",
          namespace="ns",
          database="db",
          user="root",
          password=os.getenv("SURREAL_PASSWORD"),
          vector_dim=4,
      )

      # Add vector records
      surreal_storage.add([
          VectorRecord(vector=[-0.1, 0.1, -0.1, 0.1], payload={'key1': 'value1'}),
          VectorRecord(vector=[-0.1, 0.1, 0.1, 0.1], payload={'key2': 'value2'}),
      ])

      # Query similar vectors
      query_results = surreal_storage.query(VectorDBQuery(query_vector=[0.1, 0.2, 0.1, 0.1], top_k=1))
      for result in query_results:
          print(result.record.payload, result.similarity)

      # Clear all vectors
      surreal_storage.clear()
      ```
    </Tab>
    <Tab title="Output">
      ```markdown
      >>> {'key2': 'value2'} 0.5669467095138407
      ```
    </Tab>
  </Tabs>
</Card>

---

<Card title="OceanBase Vector Storage" icon="earth-oceania">
  <b>Use for:</b> Massive vector storage with advanced analytics.  
  <b>Perfect for:</b> Batch operations, cloud or on-prem setups, and high-throughput search.

  <Tabs>
    <Tab title="Python Example">
      ```python
      import random

      from camel.storages.vectordb_storages import (
          OceanBaseStorage,
          VectorDBQuery,
          VectorRecord,
      )

      # Replace these with your OceanBase connection parameters
      OB_URI = "127.0.0.1:2881"
      OB_USER = "root@sys"
      OB_PASSWORD = ""
      OB_DB_NAME = "oceanbase"

      def main():
          ob_storage = OceanBaseStorage(
              vector_dim=4,
              table_name="my_ob_vector_table",
              uri=OB_URI,
              user=OB_USER,
              password=OB_PASSWORD,
              db_name=OB_DB_NAME,
              distance="cosine",
          )

          status = ob_storage.status()
          print(f"Vector dimension: {status.vector_dim}")
          print(f"Initial vector count: {status.vector_count}")

          random.seed(20241023)
          large_batch = []
          for i in range(1000):
              large_batch.append(
                  VectorRecord(
                      vector=[random.uniform(-1, 1) for _ in range(4)],
                      payload={'idx': i, 'batch': 'example'},
                  )
              )
          ob_storage.add(large_batch, batch_size=100)
          status = ob_storage.status()
          print(f"Vector count after adding batch: {status.vector_count}")

          query_vector = [random.uniform(-1, 1) for _ in range(4)]
          query_results = ob_storage.query(
              VectorDBQuery(query_vector=query_vector, top_k=5)
          )
          for i, result in enumerate(query_results):
              print(f"Result {i+1}:")
              print(f"  ID: {result.record.id}")
              print(f"  Payload: {result.record.payload}")
              print(f"  Similarity: {result.similarity}")

          ob_storage.clear()
          status = ob_storage.status()
          print(f"Vector count after clearing: {status.vector_count}")

      if __name__ == "__main__":
          main()
      ```
    </Tab>
    <Tab title="Output">
      ```markdown
      '''
      ===============================================================================
      Vector dimension: 4
      Initial vector count: 0
      Adding vectors in batches...
      Vector count after adding batch: 1000
      Querying similar vectors...
      Result 1:
        ID: f33f008d-688a-468a-9a2d-e005d27ad9d9
        Payload: {'idx': 496, 'batch': 'example'}
        Similarity: 0.9847431876706196
      Result 2:
        ID: 0946ca4a-9129-4343-b339-b2f13a64c827
        Payload: {'idx': 306, 'batch': 'example'}
        Similarity: 0.9598140307734809
      ...
      Clearing vectors...
      Vector count after clearing: 0
      ===============================================================================
      '''
      ```
    </Tab>
  </Tabs>
</Card>

---

<Card title="Weaviate Vector Storage" icon="file-vector">
  <b>Use for:</b> Vector search with hybrid (vector + keyword) capabilities.  
  <b>Perfect for:</b> Document retrieval and multimodal AI apps.

  <Tabs>
    <Tab title="Python Example">
      ```python
      from camel.storages import WeaviateStorage, VectorDBQuery, VectorRecord

      # Create WeaviateStorage instance with dimension = 4 using Weaviate Cloud
      weaviate_storage = WeaviateStorage(
          vector_dim=4,
          collection_name="camel_example_vectors",
          connection_type="cloud",
          wcd_cluster_url="your-weaviate-cloud-url",
          wcd_api_key="your-weaviate-api-key",
          vector_index_type="hnsw",
          distance_metric="cosine",
      )

      weaviate_storage.add([
          VectorRecord(vector=[-0.1, 0.1, -0.1, 0.1], payload={'key1': 'value1'}),
          VectorRecord(vector=[-0.1, 0.1, 0.1, 0.1], payload={'key2': 'value2'}),
      ])

      query_results = weaviate_storage.query(VectorDBQuery(query_vector=[0.1, 0.2, 0.1, 0.1], top_k=1))
      for result in query_results:
          print(result.record.payload, result.similarity)

      weaviate_storage.clear()
      ```
    </Tab>
    <Tab title="Output">
      ```markdown
      >>> {'key2': 'value2'} 0.7834733128547668
      ```
    </Tab>
  </Tabs>
</Card>

---

<Card title="NebulaGraph Storage" icon="hard-drive">
  <b>Use for:</b> Open-source, distributed graph storage and querying.  
  <b>Perfect for:</b> Knowledge graphs, relationships, and fast distributed queries.

 <CodeGroup>
      ```python
      from camel.storages.graph_storages import NebulaGraph

      nebula_graph = NebulaGraph("your_host", "your_username", "your_password", "your_space")

      # Show existing tags
      query = 'SHOW TAGS;'
      print(nebula_graph.query(query))
      ```
  </CodeGroup>
</Card>

---

<Card title="Neo4j Graph Storage" icon="square-this-way-up">
  <b>Use for:</b> Industry-standard graph database for large-scale relationships.  
  <b>Perfect for:</b> Enterprise graph workloads, Cypher queries, analytics.
<CodeGroup>
      ```python
      from camel.storages import Neo4jGraph

      neo4j_graph = Neo4jGraph(
          url="your_url",
          username="your_username",
          password="your_password",
      )

      query = "MATCH (n) DETACH DELETE n"
      print(neo4j_graph.query(query))
      ```
      </CodeGroup>
</Card>

---

<Card title="PgVectorStorage Vector Storage" icon="database">
  <b>Use for:</b> Storing and querying vectors in PostgreSQL.
  <b>Perfect for:</b> Leveraging an existing PostgreSQL database for vector search.

  <Tabs>
    <Tab title="Python Example">
      ```python
      from camel.storages import PgVectorStorage, VectorDBQuery, VectorRecord

      # Replace with your PostgreSQL connection details
      PG_CONN_INFO = {
          "host": "127.0.0.1",
          "port": 5432,
          "user": "postgres",
          "password": "postgres",
          "dbname": "postgres",
      }

      # Create PgVectorStorage instance
      pg_storage = PgVectorStorage(
          vector_dim=4,
          conn_info=PG_CONN_INFO,
          table_name="camel_example_vectors",
      )

      # Add vector records
      pg_storage.add([
          VectorRecord(vector=[-0.1, 0.1, -0.1, 0.1], payload={'key1': 'value1'}),
          VectorRecord(vector=[-0.1, 0.1, 0.1, 0.1], payload={'key2': 'value2'}),
      ])

      # Query similar vectors
      query_results = pg_storage.query(VectorDBQuery(query_vector=[0.1, 0.2, 0.1, 0.1], top_k=1))
      for result in query_results:
          print(result.record.payload, result.similarity)

      # Clear all vectors
      pg_storage.clear()
      ```
    </Tab>
    <Tab title="Output">
      ```markdown
      >>> {'key2': 'value2'} 0.5669467
      ```
    </Tab>
  </Tabs>
</Card>
