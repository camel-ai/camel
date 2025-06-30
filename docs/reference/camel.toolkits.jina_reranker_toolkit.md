<a id="camel.toolkits.jina_reranker_toolkit"></a>

<a id="camel.toolkits.jina_reranker_toolkit.JinaRerankerToolkit"></a>

## JinaRerankerToolkit

```python
class JinaRerankerToolkit(BaseToolkit):
```

A class representing a toolkit for reranking documents
using Jina Reranker.

This class provides methods for reranking documents (text or images)
based on their relevance to a given query using the Jina Reranker model.

<a id="camel.toolkits.jina_reranker_toolkit.JinaRerankerToolkit.__init__"></a>

### __init__

```python
def __init__(
    self,
    timeout: Optional[float] = None,
    model_name: str = 'jinaai/jina-reranker-m0',
    device: Optional[str] = None,
    use_api: bool = True
):
```

Initializes a new instance of the JinaRerankerToolkit class.

**Parameters:**

- **timeout** (Optional[float]): The timeout value for API requests in seconds. If None, no timeout is applied. (default: :obj:`None`)
- **model_name** (str): The reranker model name. (default: :obj:`"jinaai/jina-reranker-m0"`)
- **device** (Optional[str]): Device to load the model on. If None, will use CUDA if available, otherwise CPU. Only effective when use_api=False. (default: :obj:`None`)
- **use_api** (bool): A flag to switch between local model and API. (default: :obj:`True`)

<a id="camel.toolkits.jina_reranker_toolkit.JinaRerankerToolkit._sort_documents"></a>

### _sort_documents

```python
def _sort_documents(self, documents: List[str], scores: List[float]):
```

Sort documents by their scores in descending order.

**Parameters:**

- **documents** (List[str]): List of documents to sort.
- **scores** (List[float]): Corresponding scores for each document.

**Returns:**

  List[Dict[str, object]]: Sorted list of (document, score) pairs.

<a id="camel.toolkits.jina_reranker_toolkit.JinaRerankerToolkit._call_jina_api"></a>

### _call_jina_api

```python
def _call_jina_api(self, data: Dict[str, Any]):
```

Makes a call to the JINA API for reranking.

**Parameters:**

- **data** (Dict[str]): The data to be passed into the api body.

**Returns:**

  List[Dict[str, object]]: A list of dictionary containing
the reranked documents and their relevance scores.

<a id="camel.toolkits.jina_reranker_toolkit.JinaRerankerToolkit.rerank_text_documents"></a>

### rerank_text_documents

```python
def rerank_text_documents(
    self,
    query: str,
    documents: List[str],
    max_length: int = 1024
):
```

Reranks text documents based on their relevance to a text query.

**Parameters:**

- **query** (str): The text query for reranking.
- **documents** (List[str]): List of text documents to be reranked.
- **max_length** (int): Maximum token length for processing. (default: :obj:`1024`)

**Returns:**

  List[Dict[str, object]]: A list of dictionary containing
the reranked documents and their relevance scores.

<a id="camel.toolkits.jina_reranker_toolkit.JinaRerankerToolkit.rerank_image_documents"></a>

### rerank_image_documents

```python
def rerank_image_documents(
    self,
    query: str,
    documents: List[str],
    max_length: int = 2048
):
```

Reranks image documents based on their relevance to a text query.

**Parameters:**

- **query** (str): The text query for reranking.
- **documents** (List[str]): List of image URLs or paths to be reranked.
- **max_length** (int): Maximum token length for processing. (default: :obj:`2048`)

**Returns:**

  List[Dict[str, object]]: A list of dictionary containing
the reranked image URLs/paths and their relevance scores.

<a id="camel.toolkits.jina_reranker_toolkit.JinaRerankerToolkit.image_query_text_documents"></a>

### image_query_text_documents

```python
def image_query_text_documents(
    self,
    image_query: str,
    documents: List[str],
    max_length: int = 2048
):
```

Reranks text documents based on their relevance to an image query.

**Parameters:**

- **image_query** (str): The image URL or path used as query.
- **documents** (List[str]): List of text documents to be reranked.
- **max_length** (int): Maximum token length for processing. (default: :obj:`2048`)

**Returns:**

  List[Dict[str, object]]: A list of dictionary containing
the reranked documents and their relevance scores.

<a id="camel.toolkits.jina_reranker_toolkit.JinaRerankerToolkit.image_query_image_documents"></a>

### image_query_image_documents

```python
def image_query_image_documents(
    self,
    image_query: str,
    documents: List[str],
    max_length: int = 2048
):
```

Reranks image documents based on their relevance to an image query.

**Parameters:**

- **image_query** (str): The image URL or path used as query.
- **documents** (List[str]): List of image URLs or paths to be reranked.
- **max_length** (int): Maximum token length for processing. (default: :obj:`2048`)

**Returns:**

  List[Dict[str, object]]: A list of dictionary containing
the reranked image URLs/paths and their relevance scores.

<a id="camel.toolkits.jina_reranker_toolkit.JinaRerankerToolkit.get_tools"></a>

### get_tools

```python
def get_tools(self):
```

**Returns:**

  List[FunctionTool]: A list of FunctionTool objects
representing the functions in the toolkit.
