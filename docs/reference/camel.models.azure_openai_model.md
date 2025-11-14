<a id="camel.models.azure_openai_model"></a>

<a id="camel.models.azure_openai_model.AzureOpenAIModel"></a>

## AzureOpenAIModel

```python
class AzureOpenAIModel(BaseModelBackend):
```

Azure OpenAI API in a unified BaseModelBackend interface.

**Parameters:**

- **model_type** (Union[ModelType, str]): Model for which a backend is created, one of GPT_* series.
- **model_config_dict** (Optional[Dict[str, Any]], optional): A dictionary that will be fed into:obj:`openai.ChatCompletion.create()`. If :obj:`None`, :obj:`ChatGPTConfig().as_dict()` will be used. (default: :obj:`None`)
- **api_key** (Optional[str], optional): The API key for authenticating with the OpenAI service. (default: :obj:`None`)
- **url** (Optional[str], optional): The url to the OpenAI service. (default: :obj:`None`)
- **api_version** (Optional[str], optional): The api version for the model. (default: :obj:`None`)
- **azure_deployment_name** (Optional[str], optional): The deployment name you chose when you deployed an azure model. (default: :obj:`None`)
- **azure_ad_token** (Optional[str], optional): Your Azure Active Directory token, https://www.microsoft.com/en-us/security/business/ identity-access/microsoft-entra-id. (default: :obj:`None`)
- **azure_ad_token_provider** (Optional[AzureADTokenProvider], optional): A function that returns an Azure Active Directory token, will be invoked on every request. (default: :obj:`None`)
- **token_counter** (Optional[BaseTokenCounter], optional): Token counter to use for the model. If not provided, :obj:`OpenAITokenCounter` will be used. (default: :obj:`None`)
- **timeout** (Optional[float], optional): The timeout value in seconds for API calls. If not provided, will fall back to the MODEL_TIMEOUT environment variable or default to 180 seconds. (default: :obj:`None`)
- **max_retries** (int, optional): Maximum number of retries for API calls. (default: :obj:`3`) **kwargs (Any): Additional arguments to pass to the client initialization.
- **References**: 
- **https**: //learn.microsoft.com/en-us/azure/ai-services/openai/

<a id="camel.models.azure_openai_model.AzureOpenAIModel.__init__"></a>

### __init__

```python
def __init__(
    self,
    model_type: Union[ModelType, str],
    model_config_dict: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None,
    url: Optional[str] = None,
    timeout: Optional[float] = None,
    token_counter: Optional[BaseTokenCounter] = None,
    api_version: Optional[str] = None,
    azure_deployment_name: Optional[str] = None,
    azure_ad_token_provider: Optional['AzureADTokenProvider'] = None,
    azure_ad_token: Optional[str] = None,
    max_retries: int = 3,
    **kwargs: Any
):
```

<a id="camel.models.azure_openai_model.AzureOpenAIModel.token_counter"></a>

### token_counter

```python
def token_counter(self):
```

**Returns:**

  BaseTokenCounter: The token counter following the model's
tokenization style.

<a id="camel.models.azure_openai_model.AzureOpenAIModel._run"></a>

### _run

```python
def _run(
    self,
    messages: List[OpenAIMessage],
    response_format: Optional[Type[BaseModel]] = None,
    tools: Optional[List[Dict[str, Any]]] = None
):
```

Runs inference of Azure OpenAI chat completion.

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

<a id="camel.models.azure_openai_model.AzureOpenAIModel._request_chat_completion"></a>

### _request_chat_completion

```python
def _request_chat_completion(
    self,
    messages: List[OpenAIMessage],
    tools: Optional[List[Dict[str, Any]]] = None
):
```

<a id="camel.models.azure_openai_model.AzureOpenAIModel._request_parse"></a>

### _request_parse

```python
def _request_parse(
    self,
    messages: List[OpenAIMessage],
    response_format: Type[BaseModel],
    tools: Optional[List[Dict[str, Any]]] = None
):
```

<a id="camel.models.azure_openai_model.AzureOpenAIModel._request_stream_parse"></a>

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

<a id="camel.models.azure_openai_model.AzureOpenAIModel.stream"></a>

### stream

```python
def stream(self):
```

**Returns:**

  bool: Whether the model is in stream mode.
