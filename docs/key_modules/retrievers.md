# Retrievers
## 1. Concept
The RetrievalModule is essentially a search engine. It's designed to help you find specific pieces of information by searching through large volumes of text. Imagine you have a huge library of books and you want to find where certain topics or keywords are mentioned, this module is like a librarian that helps you do just that.


## 2. Types

### 2.1. Vector Retriever
Vector Retriever typically refers to a method or system used in information retrieval and machine learning that utilizes vector representations of data. This approach is based on converting data, like text, images, or other forms of information, into numerical vectors in a high-dimensional space.

Here's a brief overview of how it works:

- Embedding Model: First, it uses an [embedding model](https://github.com/camel-ai/camel/wiki/Embeddings). This model turns text into a mathematical form (vectors).

- Storing Information: The module takes large documents, breaks them down into smaller chunks, and then uses the embedding model to turn these chunks into vectors. These vectors are stored in a [vector storage](https://github.com/camel-ai/camel/wiki/Storages).

- Retrieving Information: When you ask a question or make a query, the [embedding model](https://github.com/camel-ai/camel/wiki/Embeddings) translates your question into vector and then searches in this [vector storage](https://github.com/camel-ai/camel/wiki/Storages) for the closest matching vector. The closest matches are likely the most relevant pieces of information you are looking for.


### 2.2. Keyword Retriever(WIP)
The Keyword Retriever is designed to retrieve relevant information based on keyword matching. Unlike the Vector Retriever that works with vector representations of data, the Keyword Retriever operates by identifying keywords or specific terms within documents and queries to find matches.

Here's a brief overview of how it works:

- Document Preprocessing: Before using the retriever, the documents are preprocessed to tokenize and index the keywords within them. Tokenization is the process of splitting text into individual words or phrases, making it easier to identify keywords.

- Query Parsing: When you input a question or query, the retriever parses the query to extract relevant keywords. This involves breaking down the query into its constituent terms.

- Keyword Matching: Once the keywords from the query are identified, the retriever searches the preprocessed documents for occurrences of these keywords. It checks for exact matches of the keywords within the documents.

- Ranking and Retrieval: After finding documents that contain the queried keywords, the retriever ranks these documents based on various factors, such as the frequency of keyword matches, document relevance, or other scoring methods. The top-ranked documents are then retrieved as the most relevant results.

## 3. Get Started

### 3.1. Using Customize Retrieval

To get started, you need to initialize the RetrievalModule with an optional embedding model. If you don't provide an embedding model, it will use the default `OpenAIEmbedding`. Here's how to do it:
```python
from camel.embeddings import OpenAIEmbedding
from camel.retrievers.retrieval_module import RetrievalModule

# Initialize the RetrievalModule with an optional embedding model
rm = RetrievalModule(embedding_model=OpenAIEmbedding())
```

**Embed and Store Data:**

Before you can retrieve information, you need to prepare your data and store it in vector storage. The embed_and_store_chunks method takes care of this for you. It processes content from a file or URL, divides it into chunks, and stores their embeddings in the specified vector storage.
```python
# Provide the path to your content input (can be a file or URL)
content_input_path = "https://arxiv.org/pdf/2303.17760.pdf"

# Create or initialize a vector storage (e.g., QdrantStorage)
from camel.storages.vectordb_storages import QdrantStorage

vector_storage = QdrantStorage(
    vector_dim=embedding_instance.get_output_dim(),
    collection="my first collection",
    path="storage_customized_run",
)

# Embed and store chunks of data in the vector storage
rm.embed_and_store_chunks(content_input_path, vector_storage)
```

**Execute a Query:**

Now that your data is stored, you can execute a query to retrieve information based on a search string. The query_and_compile_results method executes the query and compiles the retrieved results into a string.
```python
# Specify your query string
query = "What is CAMEL"

# Execute the query and retrieve results
results = rm.query_and_compile_results(query, vector_storage)
print(results)
```
```markdown
>>>  {'similarity score': '0.8321616118446469', 'content path': 'local_data/camel paper.pdf', 'metadata': {'filetype': 'application/pdf', 'languages': ['eng'], 'last_modified': '2024-01-14T22:55:19', 'page_number': 45}, 'text': 'CAMEL Data and Code License The intended purpose and licensing of CAMEL is solely for research use. The source code is licensed under Apache 2.0. The datasets are licensed under CC BY NC 4.0, which permits only non-commercial usage. It is advised that any models trained using the dataset should not be utilized for anything other than research purposes.\n\n45'}
```

### 3.2. Using Default Retrieval

To simplify the retrieval process further, you can use the run_default_retrieval method. This method handles both embedding and storing data and executing queries. It's particularly useful when dealing with multiple content input paths.
```python
rm = RetrievalModule()
retrieved_info = rm.run_default_retrieval(
    content_input_paths=[
        "https://www.camel-ai.org/",  # example remote url
    ],
    vector_storage_local_path="storage_default_run",
    query="What is CAMEL-AI",
)

print(retrieved_info)
```
```markdown
>>>  Original Query:
>>>  {What is CAMEL-AI}
>>>  Retrieved Context:
>>>  {'similarity score': '0.8380731206379989', 'content path': 'https://www.camel-ai.org/', 'metadata': {'emphasized_text_contents': ['Mission', 'CAMEL-AI.org', 'is an open-source community dedicated to the study of autonomous and communicative agents. We believe that studying these agents on a large scale offers valuable insights into their behaviors, capabilities, and potential risks. To facilitate research in this field, we provide, implement, and support various types of agents, tasks, prompts, models, datasets, and simulated environments.', 'Join us via', 'Slack', 'Discord', 'or'], 'emphasized_text_tags': ['span', 'span', 'span', 'span', 'span', 'span', 'span'], 'filetype': 'text/html', 'languages': ['eng'], 'link_texts': [None, None, None], 'link_urls': ['#h.3f4tphhd9pn8', 'https://join.slack.com/t/camel-ai/shared_invite/zt-1vy8u9lbo-ZQmhIAyWSEfSwLCl2r2eKA', 'https://discord.gg/CNcNpquyDc'], 'page_number': 1, 'url': 'https://www.camel-ai.org/'}, 'text': 'Mission\n\nCAMEL-AI.org is an open-source community dedicated to the study of autonomous and communicative agents. We believe that studying these agents on a large scale offers valuable insights into their behaviors, capabilities, and potential risks. To facilitate research in this field, we provide, implement, and support various types of agents, tasks, prompts, models, datasets, and simulated environments.\n\nJoin us via\n\nSlack\n\nDiscord\n\nor'}
```

That's it! You've successfully set up and used the RetrievalModule to retrieve information based on queries from your data collection.

Feel free to customize the code according to your specific use case and data sources. Happy retrieving!
