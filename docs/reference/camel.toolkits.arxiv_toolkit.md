<a id="camel.toolkits.arxiv_toolkit"></a>

<a id="camel.toolkits.arxiv_toolkit.ArxivToolkit"></a>

## ArxivToolkit

```python
class ArxivToolkit(BaseToolkit):
```

A toolkit for interacting with the arXiv API to search and download
academic papers.

<a id="camel.toolkits.arxiv_toolkit.ArxivToolkit.__init__"></a>

### __init__

```python
def __init__(self, timeout: Optional[float] = None):
```

Initializes the ArxivToolkit and sets up the arXiv client.

<a id="camel.toolkits.arxiv_toolkit.ArxivToolkit._get_search_results"></a>

### _get_search_results

```python
def _get_search_results(
    self,
    query: str,
    paper_ids: Optional[List[str]] = None,
    max_results: Optional[int] = 5
):
```

Retrieves search results from the arXiv API based on the provided
query and optional paper IDs.

**Parameters:**

- **query** (str): The search query string used to search for papers on arXiv.
- **paper_ids** (List[str], optional): A list of specific arXiv paper IDs to search for. (default: :obj:`None`)
- **max_results** (int, optional): The maximum number of search results to retrieve. (default: :obj:`5`)

**Returns:**

  Generator: A generator that yields results from the arXiv search
query, which includes metadata about each paper matching the
query.

<a id="camel.toolkits.arxiv_toolkit.ArxivToolkit.search_papers"></a>

### search_papers

```python
def search_papers(
    self,
    query: str,
    paper_ids: Optional[List[str]] = None,
    max_results: Optional[int] = 5
):
```

Searches for academic papers on arXiv using a query string and
optional paper IDs.

**Parameters:**

- **query** (str): The search query string.
- **paper_ids** (List[str], optional): A list of specific arXiv paper IDs to search for. (default: :obj:`None`)
- **max_results** (int, optional): The maximum number of search results to return. (default: :obj:`5`)

**Returns:**

  List[Dict[str, str]]: A list of dictionaries, each containing
information about a paper, including title, published date,
authors, entry ID, summary, and extracted text from the paper.

<a id="camel.toolkits.arxiv_toolkit.ArxivToolkit.download_papers"></a>

### download_papers

```python
def download_papers(
    self,
    query: str,
    paper_ids: Optional[List[str]] = None,
    max_results: Optional[int] = 5,
    output_dir: Optional[str] = './'
):
```

Downloads PDFs of academic papers from arXiv based on the provided
query.

**Parameters:**

- **query** (str): The search query string.
- **paper_ids** (List[str], optional): A list of specific arXiv paper IDs to download. (default: :obj:`None`)
- **max_results** (int, optional): The maximum number of search results to download. (default: :obj:`5`)
- **output_dir** (str, optional): The directory to save the downloaded PDFs. Defaults to the current directory.

**Returns:**

  str: Status message indicating success or failure.

<a id="camel.toolkits.arxiv_toolkit.ArxivToolkit.get_tools"></a>

### get_tools

```python
def get_tools(self):
```

**Returns:**

  List[FunctionTool]: A list of FunctionTool objects
representing the functions in the toolkit.
