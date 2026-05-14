---
title: "Agents with OceanBase (Advanced Usage)"
---

Star us on GitHub: https://github.com/camel-ai/camel

This cookbook shows how to:
- Run OceanBase Community Edition (CE) locally with Docker (4.3.5+).
- Use `OceanBaseStorage` as a persistent vector store in CAMEL.
- Tune vector index settings and query strategy for different data scales.


## Overview

OceanBase is a MySQL-compatible distributed database that can also serve as a vector database via OceanBase Vector. CAMEL provides `OceanBaseStorage` (backed by `pyobvector`) so you can store embeddings + metadata and run ANN similarity search.

This notebook focuses on a repeatable developer setup and the CAMEL-side API.


## Installation

You need the RAG/vector dependencies (this pulls in `pyobvector` on supported Python versions).

```python
!pip install "camel-ai[rag]==0.2.85"
```

If you already have a local checkout installed from source, you can skip this step.


## Recipe 1: Install OceanBase CE with Docker (4.3.5+)

OceanBase provides an official Docker image: `oceanbase/oceanbase-ce`.

- Port: `2881` (MySQL-compatible endpoint) and `2886` (OceanBase dashboard / obshell)
- Recommended environment variable: `OB_TENANT_PASSWORD`

Official image docs:
- https://github.com/oceanbase/docker-images/tree/main/oceanbase-ce
- https://hub.docker.com/r/oceanbase/oceanbase-ce

### Option A: Quick start (`docker run`)

```bash
docker pull oceanbase/oceanbase-ce

docker run -d --name oceanbase-ce \
  -p 2881:2881 \
  -p 2886:2886 \
  -e MODE=SLIM \
  -e OB_TENANT_PASSWORD=TenantPassw0rd! \
  oceanbase/oceanbase-ce

# Watch logs until the service prints "boot success!"
docker logs -f oceanbase-ce
```

### Option B: With persistence (recommended for iterative dev)

```bash
mkdir -p ob ob-cluster

docker run -d --name oceanbase-ce \
  -p 2881:2881 \
  -p 2886:2886 \
  -e MODE=SLIM \
  -e OB_TENANT_PASSWORD=TenantPassw0rd! \
  -v "$PWD/ob:/root/ob" \
  -v "$PWD/ob-cluster:/root/.obd/cluster" \
  oceanbase/oceanbase-ce
```

### Sanity check (optional)

If you have a MySQL client installed, try connecting (usernames can be tenant-qualified, e.g. `root@test`).

```bash
mysql -h 127.0.0.1 -P 2881 -u root@test -p
```

Notes:
- The exact default tenants/users can vary by image version and your configuration.
- For local dev, `MODE=SLIM` starts a lightweight single-node setup quickly.
- Wait until `docker logs -f oceanbase-ce` shows `boot success!` before running the CAMEL storage cells below.


## Recipe 2: Use OceanBaseStorage in CAMEL

`OceanBaseStorage` stores vectors and metadata in an OceanBase table and creates an HNSW vector index if the table does not already exist.

Key parameters (see `camel/storages/vectordb_storages/oceanbase.py`):
- `vector_dim`: embedding dimension
- `table_name`: table name in OceanBase
- `uri`: `host:port` (for local Docker: `127.0.0.1:2881`)
- `user`: typically tenant-qualified (e.g. `root@test`)
- `password`: password for the user
- `db_name`: database name
- `distance`: `"l2"` or `"cosine"`

IMPORTANT: In the current CAMEL implementation, the HNSW index build parameters are fixed in code:
- `m = 16`
- `ef_construction = 256`
If you need different HNSW parameters, you must modify/extend the implementation.



```python
import os
import random

from camel.storages import OceanBaseStorage, VectorDBQuery, VectorRecord

```


```python
# Connection settings for local Docker
OB_URI = os.environ.get("OB_URI", "127.0.0.1:2881")
OB_USER = os.environ.get("OB_USER", "root@test")
OB_PASSWORD = os.environ.get("OB_PASSWORD", "TenantPassw0rd!")
OB_DB_NAME = os.environ.get("OB_DB_NAME", "test")

TABLE_NAME = os.environ.get("OB_TABLE_NAME", "camel_oceanbase_vectors")
VECTOR_DIM = int(os.environ.get("VECTOR_DIM", "4"))

```


```python
storage = OceanBaseStorage(
    vector_dim=VECTOR_DIM,
    table_name=TABLE_NAME,
    uri=OB_URI,
    user=OB_USER,
    password=OB_PASSWORD,
    db_name=OB_DB_NAME,
    distance="cosine",
)

print(storage.status())

```

### Basic operations: add/query/delete/clear

This quick sanity check does not require any embedding model. We insert random vectors, query with a random vector, then clean up.



```python
random.seed(20260131)

records = []
for i in range(200):
    records.append(
        VectorRecord(
            vector=[random.uniform(-1, 1) for _ in range(VECTOR_DIM)],
            payload={"doc_id": f"doc-{i}", "source": "sanity-check"},
        )
    )

storage.add(records=records, batch_size=100)
print(storage.status())

```


```python
query_vector = [random.uniform(-1, 1) for _ in range(VECTOR_DIM)]
results = storage.query(VectorDBQuery(query_vector=query_vector, top_k=5))

for r in results:
    print({"id": r.record.id, "similarity": r.similarity, "payload": r.record.payload})

```


```python
# Clean up the table contents (destructive)
storage.clear()
print(storage.status())

```

## Recipe 3: Index tuning best practices by scale

OceanBase uses an HNSW-style ANN index for vector search. HNSW tuning is always a tradeoff among recall, latency, build time, and memory.

Terminology (common across HNSW implementations):
- `m`: graph connectivity (higher improves recall but increases memory and build time)
- `ef_construction`: build-time search width (higher improves recall but increases build time)
- `ef_search` (or similar): query-time search width (higher improves recall but increases query latency)

### Practical guidance

Small collections (<= 100k vectors):
- Favor fast iteration: keep build settings moderate and increase query-time effort when needed.

Medium collections (~100k to 5M vectors):
- Measure P95/P99 latency and recall. If you cannot reach recall targets without excessive query latency, increase build settings and rebuild.

Large collections (5M+ vectors):
- Plan for memory and rebuild time. Consider sharding/partitioning by tenant/corpus/time to reduce the search space.

### CAMEL-specific note

In the current CAMEL `OceanBaseStorage` implementation, the HNSW index is created with fixed values (`m=16`, `ef_construction=256`) when the table is first created. To tune these, you need to update the implementation so the index creation parameters are configurable.

### Metadata and relational index tips

Vector similarity search is only part of most RAG workloads. For real applications you often filter by tenant, document id, time range, or tags.
If you add structured columns (or store frequently-filtered values in dedicated columns instead of only JSON), you can use normal relational indexing to speed up filters before ANN search.

