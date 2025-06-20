---
title: "Retrievers"
icon: code-compare
---

## What Are Retrievers?

<Card title="Concept" icon="laptop-file">
Retrievers are your AI search engine for large text collections or knowledge bases. They let you find the most relevant information based on a query—using either advanced embeddings (semantic search) or classic keyword matching.
</Card>

<Tip>
Want a deep dive? Check out the <a href="/cookbooks/advanced_features/agents_with_rag">RAG Cookbook</a> for advanced agent + retrieval use cases.
</Tip>

## Types of Retrievers

<CardGroup cols={2}>
  <Card title="Vector Retriever" icon="box">
    Converts documents into vectors using an embedding model, stores them, and retrieves by semantic similarity. Best for “meaning-based” search, RAG, and LLM workflows.
    <ul>
      <li>Chunks data, embeds with OpenAI or custom model</li>
      <li>Stores in vector DB (like Qdrant)</li>
      <li>Finds the most relevant info even with different wording</li>
    </ul>
  </Card>
  <Card title="Keyword Retriever" icon="hashtag">
    Classic keyword search! Breaks documents and queries into tokens/keywords, and matches on those.
    <ul>
      <li>Tokenizes documents</li>
      <li>Indexes by keyword</li>
      <li>Fast, transparent, great for exact matches</li>
    </ul>
  </Card>
</CardGroup>

## How To Use

<Card title="Semantic Retrieval with VectorRetriever" icon="box">
This example uses OpenAI embeddings and Qdrant vector storage for semantic search.

<CodeGroup>
```python vector_retriever_setup.py
from camel.embeddings import OpenAIEmbedding
from camel.retrievers import VectorRetriever
from camel.storages.vectordb_storages import QdrantStorage

# Set up vector DB for embeddings
vector_storage = QdrantStorage(
    vector_dim=OpenAIEmbedding().get_output_dim(),
    collection_name="my first collection",
    path="storage_customized_run",
)
vr = VectorRetriever(embedding_model=OpenAIEmbedding(), storage=vector_storage)
```
</CodeGroup>

<CodeGroup>
```python vector_retriever_ingest.py
# Embed and store your data (URL or file)
content_input_path = "https://www.camel-ai.org/"
vr.process(content=content_input_path)
```
</CodeGroup>

<CodeGroup>
```python vector_retriever_query.py
# Run a query for semantic search
query = "What is CAMEL"
results = vr.query(query=query, similarity_threshold=0)
print(results)
```
```markdown vector_retriever_output.md
>>>  [{'similarity score': '0.81...', 'content path': 'https://www.camel-ai.org/', 'metadata': {...}, 'text': '...CAMEL-AI.org is an open-source community dedicated to the study of autonomous and communicative agents...'}]
```
</CodeGroup>
</Card>

<Card title="AutoRetriever: Quick RAG with One Call" icon="zap">
AutoRetriever simplifies everything: just specify storage and content, and it handles embedding, storage, and querying.

<CodeGroup>
```python auto_retriever.py
from camel.retrievers import AutoRetriever
from camel.types import StorageType

ar = AutoRetriever(
    vector_storage_local_path="camel/retrievers",
    storage_type=StorageType.QDRANT,
)

retrieved_info = ar.run_vector_retriever(
    contents=["https://www.camel-ai.org/"],   # One or many URLs/files
    query="What is CAMEL-AI",
    return_detailed_info=True,
)
print(retrieved_info)
```
```markdown auto_retriever_output.md
>>> Original Query: {What is CAMEL-AI}
>>> Retrieved Context:
>>> {'similarity score': '0.83...', 'content path': 'https://www.camel-ai.org/', 'metadata': {...}, 'text': 'Mission\n\nCAMEL-AI.org is an open-source community dedicated to the study of autonomous and communicative agents...'}
```
</CodeGroup>

<Tip>
Use AutoRetriever for fast experiments and RAG workflows; for advanced control, use VectorRetriever directly.
</Tip>
</Card>

<Card title="KeywordRetriever (Classic Search)" icon="hashtag">
For simple, blazing-fast search by keyword—use KeywordRetriever.  
Great for small data, transparency, or keyword-driven tasks.  
*(API and code example coming soon—see RAG Cookbook for details.)*
</Card>

<CardGroup cols={2}>
  <Card
    title="See RAG Agents in Action"
    icon="rocket"
    href="../cookbooks/advanced_features/agents_with_rag.ipynb"
  >
    Build retrieval-augmented agents using these retrievers.
  </Card>
  <Card
    title="Reference API"
    icon="book"
    href="/reference/#retrievers"
  >
    Full configuration and options for all retriever classes.
  </Card>
</CardGroup>

