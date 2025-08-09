<a id="camel.toolkits.search_toolkit"></a>

<a id="camel.toolkits.search_toolkit.SearchToolkit"></a>

## SearchToolkit

```python
class SearchToolkit(BaseToolkit):
```

A class representing a toolkit for web search.

This class provides methods for searching information on the web using
search engines like Google, DuckDuckGo, Wikipedia and Wolfram Alpha, Brave.

<a id="camel.toolkits.search_toolkit.SearchToolkit.search_wiki"></a>

### search_wiki

```python
def search_wiki(self, entity: str):
```

Search the entity in WikiPedia and return the summary of the
required page, containing factual information about
the given entity.

**Parameters:**

- **entity** (str): The entity to be searched.

**Returns:**

  str: The search result. If the page corresponding to the entity
exists, return the summary of this entity in a string.

<a id="camel.toolkits.search_toolkit.SearchToolkit.search_linkup"></a>

### search_linkup

```python
def search_linkup(
    self,
    query: str,
    depth: Literal['standard', 'deep'] = 'standard',
    output_type: Literal['searchResults', 'sourcedAnswer', 'structured'] = 'searchResults',
    structured_output_schema: Optional[str] = None
):
```

Search for a query in the Linkup API and return results in various
formats.

**Parameters:**

- **query** (str): The search query.
- **depth** (`Literal["standard", "deep"]`): The depth of the search. "standard" for a straightforward search, "deep" for a more comprehensive search.
- **output_type** (`Literal["searchResults", "sourcedAnswer", "structured"]`): The type of output: - "searchResults" for raw search results, - "sourcedAnswer" for an answer with supporting sources, - "structured" for output based on a provided schema.
- **structured_output_schema** (Optional[str]): If `output_type` is "structured", specify the schema of the output. Must be a string representing a valid object JSON schema.

**Returns:**

  Dict[str, Any]: A dictionary representing the search result. The
structure depends on the `output_type`. If an error occurs,
returns an error message.

<a id="camel.toolkits.search_toolkit.SearchToolkit.search_duckduckgo"></a>

### search_duckduckgo

```python
def search_duckduckgo(
    self,
    query: str,
    source: str = 'text',
    max_results: int = 5
):
```

Use DuckDuckGo search engine to search information for
the given query.

This function queries the DuckDuckGo API for related topics to
the given search term. The results are formatted into a list of
dictionaries, each representing a search result.

**Parameters:**

- **query** (str): The query to be searched.
- **source** (str): The type of information to query (e.g., "text", "images", "videos"). Defaults to "text".
- **max_results** (int): Max number of results, defaults to `5`. (default: 5)

**Returns:**

  List[Dict[str, Any]]: A list of dictionaries where each dictionary
represents a search result.

<a id="camel.toolkits.search_toolkit.SearchToolkit.search_brave"></a>

### search_brave

```python
def search_brave(
    self,
    q: str,
    country: str = 'US',
    search_lang: str = 'en',
    ui_lang: str = 'en-US',
    count: int = 20,
    offset: int = 0,
    safesearch: str = 'moderate',
    freshness: Optional[str] = None,
    text_decorations: bool = True,
    spellcheck: bool = True,
    result_filter: Optional[str] = None,
    goggles_id: Optional[str] = None,
    units: Optional[str] = None,
    extra_snippets: Optional[bool] = None,
    summary: Optional[bool] = None
):
```

This function queries the Brave search engine API and returns a
dictionary, representing a search result.
See https://api.search.brave.com/app/documentation/web-search/query
for more details.

**Parameters:**

- **q** (str): The user's search query term. Query cannot be empty. Maximum of 400 characters and 50 words in the query.
- **country** (str): The search query country where results come from. The country string is limited to 2 character country codes of supported countries. For a list of supported values, see Country Codes. (default: :obj:`US `)
- **search_lang** (str): The search language preference. Use ONLY these exact values, NOT standard ISO codes: 'ar', 'eu', 'bn', 'bg', 'ca', 'zh-hans', 'zh-hant', 'hr', 'cs', 'da', 'nl', 'en', 'en-gb', 'et', 'fi', 'fr', 'gl', 'de', 'gu', 'he', 'hi', 'hu', 'is', 'it', 'jp', 'kn', 'ko', 'lv', 'lt', 'ms', 'ml', 'mr', 'nb', 'pl', 'pt-br', 'pt-pt', 'pa', 'ro', 'ru', 'sr', 'sk', 'sl', 'es', 'sv', 'ta', 'te', 'th', 'tr', 'uk', 'vi'.
- **ui_lang** (str): User interface language preferred in response.
- **Format**: '`<language_code>`-`<country_code>`'. Common examples: 'en-US', 'en-GB', 'jp-JP', 'zh-hans-CN', 'zh-hant-TW', 'de-DE', 'fr-FR', 'es-ES', 'pt-BR', 'ru-RU', 'ko-KR'.
- **count** (int): The number of search results returned in response. The maximum is 20. The actual number delivered may be less than requested. Combine this parameter with offset to paginate search results.
- **offset** (int): The zero based offset that indicates number of search results per page (count) to skip before returning the result. The maximum is 9. The actual number delivered may be less than requested based on the query. In order to paginate results use this parameter together with count. For example, if your user interface displays 20 search results per page, set count to 20 and offset to 0 to show the first page of results. To get subsequent pages, increment offset by 1 (e.g. 0, 1, 2). The results may overlap across multiple pages.
- **safesearch** (str): Filters search results for adult content. The following values are supported: - 'off': No filtering is done. - 'moderate': Filters explicit content, like images and videos, but allows adult domains in the search results. - 'strict': Drops all adult content from search results.
- **freshness** (Optional[str]): Filters search results by when they were
- **discovered**: - 'pd': Discovered within the last 24 hours. - 'pw': Discovered within the last 7 Days. - 'pm': Discovered within the last 31 Days. - 'py': Discovered within the last 365 Days. - 'YYYY-MM-DDtoYYYY-MM-DD': Timeframe is also supported by specifying the date range e.g. '2022-04-01to2022-07-30'.
- **text_decorations** (bool): Whether display strings (e.g. result snippets) should include decoration markers (e.g. highlighting characters).
- **spellcheck** (bool): Whether to spellcheck provided query. If the spellchecker is enabled, the modified query is always used for search. The modified query can be found in altered key from the query response model.
- **result_filter** (Optional[str]): A comma delimited string of result types to include in the search response. Not specifying this parameter will return back all result types in search response where data is available and a plan with the corresponding option is subscribed. The response always includes query and type to identify any query modifications and response type respectively. Available result filter values are: - 'discussions' - 'faq' - 'infobox' - 'news' - 'query' - 'summarizer' - 'videos' - 'web' - 'locations'
- **goggles_id** (Optional[str]): Goggles act as a custom re-ranking on top of Brave's search index. For more details, refer to the Goggles repository.
- **units** (Optional[str]): The measurement units. If not provided, units are derived from search country. Possible values are: - 'metric': The standardized measurement system - 'imperial': The British Imperial system of units.
- **extra_snippets** (Optional[bool]): A snippet is an excerpt from a page you get as a result of the query, and extra_snippets allow you to get up to 5 additional, alternative excerpts. Only available under Free AI, Base AI, Pro AI, Base Data, Pro Data and Custom plans.
- **summary** (Optional[bool]): This parameter enables summary key generation in web search results. This is required for summarizer to be enabled.

**Returns:**

  Dict[str, Any]: A dictionary representing a search result.

<a id="camel.toolkits.search_toolkit.SearchToolkit.search_google"></a>

### search_google

```python
def search_google(self, query: str, num_result_pages: int = 5):
```

Use Google search engine to search information for the given query.

**Parameters:**

- **query** (str): The query to be searched.
- **num_result_pages** (int): The number of result pages to retrieve.

**Returns:**

  List[Dict[str, Any]]: A list of dictionaries where each dictionary
represents a website.
Each dictionary contains the following keys:
- 'result_id': A number in order.
- 'title': The title of the website.
- 'description': A brief description of the website.
- 'long_description': More detail of the website.
- 'url': The URL of the website.

<a id="camel.toolkits.search_toolkit.SearchToolkit.tavily_search"></a>

### tavily_search

```python
def tavily_search(
    self,
    query: str,
    num_results: int = 5,
    **kwargs
):
```

Use Tavily Search API to search information for the given query.

**Parameters:**

- **query** (str): The query to be searched.
- **num_results** (int): The number of search results to retrieve (default is `5`). **kwargs: Additional optional parameters supported by Tavily's API: - search_depth (str): "basic" or "advanced" search depth. - topic (str): The search category, e.g., "general" or "news." - days (int): Time frame in days for news-related searches. - max_results (int): Max number of results to return (overrides `num_results`). See https://docs.tavily.com/docs/python-sdk/tavily-search/ api-reference for details.

**Returns:**

  List[Dict[str, Any]]: A list of dictionaries representing search
results. Each dictionary contains:
- 'result_id' (int): The result's index.
- 'title' (str): The title of the result.
- 'description' (str): A brief description of the result.
- 'long_description' (str): Detailed information, if available.
- 'url' (str): The URL of the result.
- 'content' (str): Relevant content from the search result.
- 'images' (list): A list of related images (if
`include_images` is True).
- 'published_date' (str): Publication date for news topics
(if available).

<a id="camel.toolkits.search_toolkit.SearchToolkit.search_bocha"></a>

### search_bocha

```python
def search_bocha(
    self,
    query: str,
    freshness: str = 'noLimit',
    summary: bool = False,
    count: int = 10,
    page: int = 1
):
```

Query the Bocha AI search API and return search results.

**Parameters:**

- **query** (str): The search query.
- **freshness** (str): Time frame filter for search results. Default is "noLimit". Options include: - 'noLimit': no limit (default). - 'oneDay': past day. - 'oneWeek': past week. - 'oneMonth': past month. - 'oneYear': past year.
- **summary** (bool): Whether to include text summaries in results. Default is False.
- **count** (int): Number of results to return (1-50). Default is 10.
- **page** (int): Page number of results. Default is 1.

**Returns:**

  Dict[str, Any]: A dictionary containing search results, including
web pages, images, and videos if available. The structure
follows the Bocha AI search API response format.

<a id="camel.toolkits.search_toolkit.SearchToolkit.search_baidu"></a>

### search_baidu

```python
def search_baidu(self, query: str, max_results: int = 5):
```

Search Baidu using web scraping to retrieve relevant search
results. This method queries Baidu's search engine and extracts search
results including titles, descriptions, and URLs.

**Parameters:**

- **query** (str): Search query string to submit to Baidu.
- **max_results** (int): Maximum number of results to return. (default: :obj:`5`)

**Returns:**

  Dict[str, Any]: A dictionary containing search results or error
message.

<a id="camel.toolkits.search_toolkit.SearchToolkit.search_bing"></a>

### search_bing

```python
def search_bing(self, query: str, max_results: int = 5):
```

Use Bing search engine to search information for the given query.

This function queries the Chinese version of Bing search engine (cn.
bing.com) using web scraping to retrieve relevant search results. It
extracts search results including titles, snippets, and URLs. This
function is particularly useful when the query is in Chinese or when
Chinese search results are desired.

**Parameters:**

- **query** (str): The search query string to submit to Bing. Works best with Chinese queries or when Chinese results are preferred.
- **max_results** (int): Maximum number of results to return. (default: :obj:`5`)

**Returns:**

  Dict ([str, Any]): A dictionary containing either:
- 'results': A list of dictionaries, each with:
- 'result_id': The index of the result.
- 'snippet': A brief description of the search result.
- 'title': The title of the search result.
- 'link': The URL of the search result.
- or 'error': An error message if something went wrong.

<a id="camel.toolkits.search_toolkit.SearchToolkit.search_exa"></a>

### search_exa

```python
def search_exa(
    self,
    query: str,
    search_type: Literal['auto', 'neural', 'keyword'] = 'auto',
    category: Optional[Literal['company', 'research paper', 'news', 'pdf', 'github', 'tweet', 'personal site', 'linkedin profile', 'financial report']] = None,
    num_results: int = 10,
    include_text: Optional[List[str]] = None,
    exclude_text: Optional[List[str]] = None,
    use_autoprompt: bool = True,
    text: bool = False
):
```

Use Exa search API to perform intelligent web search with optional
content extraction.

**Parameters:**

- **query** (str): The search query string.
- **search_type** (`Literal["auto", "neural", "keyword"]`): The type of search to perform. "auto" automatically decides between keyword and neural search. (default: :obj:`"auto"`)
- **category** (Optional[Literal]): Category to focus the search on, such as "research paper" or "news". (default: :obj:`None`)
- **num_results** (int): Number of results to return (max 100). (default: :obj:`10`)
- **include_text** (Optional[List[str]]): Strings that must be present in webpage text. Limited to 1 string of up to 5 words. (default: :obj:`None`)
- **exclude_text** (Optional[List[str]]): Strings that must not be present in webpage text. Limited to 1 string of up to 5 words. (default: :obj:`None`)
- **use_autoprompt** (bool): Whether to use Exa's autoprompt feature to enhance the query. (default: :obj:`True`)
- **text** (bool): Whether to include webpage contents in results. (default: :obj:`False`)

**Returns:**

  Dict[str, Any]: A dict containing search results and metadata:
- requestId (str): Unique identifier for the request
- autopromptString (str): Generated autoprompt if enabled
- autoDate (str): Timestamp of autoprompt generation
- resolvedSearchType (str): The actual search type used
- results (List[Dict]): List of search results with metadata
- searchType (str): The search type that was selected
- costDollars (Dict): Breakdown of API costs

<a id="camel.toolkits.search_toolkit.SearchToolkit.search_alibaba_tongxiao"></a>

### search_alibaba_tongxiao

```python
def search_alibaba_tongxiao(
    self,
    query: str,
    time_range: Literal['OneDay', 'OneWeek', 'OneMonth', 'OneYear', 'NoLimit'] = 'NoLimit',
    industry: Optional[Literal['finance', 'law', 'medical', 'internet', 'tax', 'news_province', 'news_center']] = None,
    page: int = 1,
    return_main_text: bool = False,
    return_markdown_text: bool = True,
    enable_rerank: bool = True
):
```

Query the Alibaba Tongxiao search API and return search results.

A powerful search API optimized for Chinese language queries with
features:
- Enhanced Chinese language understanding
- Industry-specific filtering (finance, law, medical, etc.)
- Structured data with markdown formatting
- Result reranking for relevance
- Time-based filtering

**Parameters:**

- **query** (str): The search query string (`length ``>= 1` and `<= 100```).
- **time_range** (`Literal["OneDay", "OneWeek", "OneMonth", "OneYear", "NoLimit"]`): Time frame filter for search results. (default: :obj:`"NoLimit"`)
- **industry** (`Optional[Literal["finance", "law", "medical", "internet", "tax", "news_province", "news_center"]]`): Industry-specific search filter. When specified, only returns results from sites in the specified industries. Multiple industries can be comma-separated. (default: :obj:`None`)
- **page** (int): Page number for results pagination. (default: :obj:`1`)
- **return_main_text** (bool): Whether to include the main text of the webpage in results. (default: :obj:`True`)
- **return_markdown_text** (bool): Whether to include markdown formatted content in results. (default: :obj:`True`)
- **enable_rerank** (bool): Whether to enable result reranking. If response time is critical, setting this to False can reduce response time by approximately 140ms. (default: :obj:`True`)

**Returns:**

  Dict[str, Any]: A dictionary containing either search results with
'requestId' and 'results' keys, or an 'error' key with error
message. Each result contains title, snippet, url and other
metadata.

<a id="camel.toolkits.search_toolkit.SearchToolkit.get_tools"></a>

### get_tools

```python
def get_tools(self):
```

**Returns:**

  List[FunctionTool]: A list of FunctionTool objects
representing the functions in the toolkit.
