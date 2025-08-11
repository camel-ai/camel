<a id="camel.models.openai_compatible_model"></a>

<a id="camel.models.openai_compatible_model.OpenAICompatibleModel"></a>

## OpenAICompatibleModel

```python
class OpenAICompatibleModel(BaseModelBackend):
```

Constructor for model backend supporting OpenAI compatibility.

**Parameters:**

- **model_type** (Union[ModelType, str]): Model for which a backend is created.
- **model_config_dict** (Optional[Dict[str, Any]], optional): A dictionary that will be fed into:obj:`openai.ChatCompletion.create()`. If :obj:`None`, :obj:`{}` will be used. (default: :obj:`None`)
- **api_key** (str): The API key for authenticating with the model service.
- **url** (str): The url to the model service.
- **token_counter** (Optional[BaseTokenCounter], optional): Token counter to use for the model. If not provided, :obj:`OpenAITokenCounter( ModelType.GPT_4O_MINI)` will be used. (default: :obj:`None`)
- **timeout** (Optional[float], optional): The timeout value in seconds for API calls. If not provided, will fall back to the MODEL_TIMEOUT environment variable or default to 180 seconds. (default: :obj:`None`)
- **max_retries** (int, optional): Maximum number of retries for API calls. (default: :obj:`3`) **kwargs (Any): Additional arguments to pass to the OpenAI client initialization. These can include parameters like 'organization', 'default_headers', 'http_client', etc.

<a id="camel.models.openai_compatible_model.OpenAICompatibleModel.__init__"></a>

### __init__

```python
def __init__(
    self,
    model_type: Union[ModelType, str],
    model_config_dict: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None,
    url: Optional[str] = None,
    token_counter: Optional[BaseTokenCounter] = None,
    timeout: Optional[float] = None,
    max_retries: int = 3,
    **kwargs: Any
):
```

<a id="camel.models.openai_compatible_model.OpenAICompatibleModel._run"></a>

### _run

```python
def _run(
    self,
    messages: List[OpenAIMessage],
    response_format: Optional[Type[BaseModel]] = None,
    tools: Optional[List[Dict[str, Any]]] = None
):
```

Runs inference of OpenAI chat completion.

**Parameters:**

- **messages** (List[OpenAIMessage]): Message list with the chat history in OpenAI API format.
- **response_format** (Optional[Type[BaseModel]]): The format of the response.
- **tools** (Optional[List[Dict[str, Any]]]): The schema of the tools to use for the request.

**Returns:**

  Union[ChatCompletion, Stream[ChatCompletionChunk]]:
`ChatCompletion` in the non-stream mode, or
`Stream[ChatCompletionChunk]` in the stream mode.
`ChatCompletionStreamManager[BaseModel]` for
structured output streaming.

<a id="camel.models.openai_compatible_model.OpenAICompatibleModel._request_chat_completion"></a>

### _request_chat_completion

```python
def _request_chat_completion(
    self,
    messages: List[OpenAIMessage],
    tools: Optional[List[Dict[str, Any]]] = None
):
```

<a id="camel.models.openai_compatible_model.OpenAICompatibleModel._request_parse"></a>

### _request_parse

```python
def _request_parse(
    self,
    messages: List[OpenAIMessage],
    response_format: Type[BaseModel],
    tools: Optional[List[Dict[str, Any]]] = None
):
```

<a id="camel.models.openai_compatible_model.OpenAICompatibleModel._request_stream_parse"></a>

### _request_stream_parse

```python
def _request_stream_parse(
    self,
    messages: List[OpenAIMessage],
    response_format: Type[BaseModel],
    tools: Optional[List[Dict[str, Any]]] = None
):
```

Request streaming structured output parsing.

<a id="camel.models.openai_compatible_model.OpenAICompatibleModel.token_counter"></a>

### token_counter

```python
def token_counter(self):
```

**Returns:**

  OpenAITokenCounter: The token counter following the model's
tokenization style.

<a id="camel.models.openai_compatible_model.OpenAICompatibleModel.stream"></a>

### stream

```python
def stream(self):
```

**Returns:**

  bool: Whether the model is in stream mode.
