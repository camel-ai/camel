<a id="camel.toolkits.dappier_toolkit"></a>

<a id="camel.toolkits.dappier_toolkit.DappierToolkit"></a>

## DappierToolkit

```python
class DappierToolkit(BaseToolkit):
```

A class representing a toolkit for interacting with the Dappier API.

This class provides methods for searching real time data and fetching
ai recommendations across key verticals like News, Finance, Stock Market,
Sports, Weather and more.

<a id="camel.toolkits.dappier_toolkit.DappierToolkit.__init__"></a>

### __init__

```python
def __init__(self, timeout: Optional[float] = None):
```

Initialize the DappierTookit with API clients.The API keys and
credentials are retrieved from environment variables.

<a id="camel.toolkits.dappier_toolkit.DappierToolkit.search_real_time_data"></a>

### search_real_time_data

```python
def search_real_time_data(
    self,
    query: str,
    ai_model_id: str = 'am_01j06ytn18ejftedz6dyhz2b15'
):
```

Search real-time data using an AI model.

This function accesses real-time information using the specified
AI model based on the given query. Depending on the AI model ID,
the data retrieved can vary between general web search results or
financial news and stock prices.

Supported AI Models:
- `am_01j06ytn18ejftedz6dyhz2b15`:
Access real-time Google web search results, including the latest
news, weather updates, travel details, deals, and more.
- `am_01j749h8pbf7ns8r1bq9s2evrh`:
Access real-time financial news, stock prices, and trades from
polygon.io, with AI-powered insights and up-to-the-minute updates.

**Parameters:**

- **query** (str): The user-provided query. Examples include: - "How is the weather today in Austin, TX?" - "What is the latest news for Meta?" - "What is the stock price for AAPL?"
- **ai_model_id** (str, optional): The AI model ID to use for the query. The AI model ID always starts with the prefix "am_". (default: `am_01j06ytn18ejftedz6dyhz2b15`)

**Returns:**

  str: The search result corresponding to the provided query and
AI model ID. This may include real time search data,
depending on the selected AI model.

**Note:**

Multiple AI model IDs are available, which can be found at:
https://marketplace.dappier.com/marketplace

<a id="camel.toolkits.dappier_toolkit.DappierToolkit.get_ai_recommendations"></a>

### get_ai_recommendations

```python
def get_ai_recommendations(
    self,
    query: str,
    data_model_id: str = 'dm_01j0pb465keqmatq9k83dthx34',
    similarity_top_k: int = 9,
    ref: Optional[str] = None,
    num_articles_ref: int = 0,
    search_algorithm: Literal['most_recent', 'semantic', 'most_recent_semantic', 'trending'] = 'most_recent'
):
```

Retrieve AI-powered recommendations based on the provided query
and data model.

This function fetches real-time AI-generated recommendations using the
specified data model and search algorithm. The results include
personalized content based on the query and, optionally, relevance
to a specific reference domain.

Supported Data Models:
- `dm_01j0pb465keqmatq9k83dthx34`:
Real-time news, updates, and personalized content from top sports
sources such as Sportsnaut, Forever Blueshirts, Minnesota Sports
Fan, LAFB Network, Bounding Into Sports, and Ringside Intel.
- `dm_01j0q82s4bfjmsqkhs3ywm3x6y`:
Real-time updates, analysis, and personalized content from top
sources like The Mix, Snipdaily, Nerdable, and Familyproof.

**Parameters:**

- **query** (str): The user query for retrieving recommendations.
- **data_model_id** (str, optional): The data model ID to use for recommendations. Data model IDs always start with the prefix "dm_". (default: :obj:`dm_01j0pb465keqmatq9k83dthx34`)
- **similarity_top_k** (int, optional): The number of top documents to retrieve based on similarity. (default: :obj:`9`)
- **ref** (Optional[str], optional): The site domain where AI recommendations should be displayed. (default: :obj:`None`)
- **num_articles_ref** (int, optional): The minimum number of articles to return from the specified reference domain (`ref`). The remaining articles will come from other sites in the RAG model. (default: :obj:`0`) search_algorithm (Literal[ "most_recent", "semantic", "most_recent_semantic", "trending", ], optional): The search algorithm to use for retrieving articles. (default: :obj:`most_recent`)

**Returns:**

  List[Dict[str, str]]: A list of recommended articles or content
based on the specified parameters, query, and data model.

**Note:**

Multiple data model IDs are available and can be found at:
https://marketplace.dappier.com/marketplace

<a id="camel.toolkits.dappier_toolkit.DappierToolkit.get_tools"></a>

### get_tools

```python
def get_tools(self):
```

**Returns:**

  List[FunctionTool]: A list of FunctionTool objects representing
the functions in the toolkit.
