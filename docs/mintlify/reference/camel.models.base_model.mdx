<a id="camel.models.base_model"></a>

<a id="camel.models.base_model.ModelBackendMeta"></a>

## ModelBackendMeta

```python
class ModelBackendMeta(ABCMeta):
```

Metaclass that automatically preprocesses messages in run method.

Automatically wraps the run method of any class inheriting from
BaseModelBackend to preprocess messages (remove `<think>` tags) before they
are sent to the model.

<a id="camel.models.base_model.ModelBackendMeta.__new__"></a>

### __new__

```python
def __new__(
    mcs,
    name,
    bases,
    namespace
):
```

Wraps run method with preprocessing if it exists in the class.

<a id="camel.models.base_model.BaseModelBackend"></a>

## BaseModelBackend

```python
class BaseModelBackend(ABC):
```

Base class for different model backends.
It may be OpenAI API, a local LLM, a stub for unit tests, etc.

**Parameters:**

- **model_type** (Union[ModelType, str]): Model for which a backend is created.
- **model_config_dict** (Optional[Dict[str, Any]], optional): A config dictionary. (default: :obj:`{}`)
- **api_key** (Optional[str], optional): The API key for authenticating with the model service. (default: :obj:`None`)
- **url** (Optional[str], optional): The url to the model service. (default: :obj:`None`)
- **token_counter** (Optional[BaseTokenCounter], optional): Token counter to use for the model. If not provided, :obj:`OpenAITokenCounter` will be used. (default: :obj:`None`)
- **timeout** (Optional[float], optional): The timeout value in seconds for API calls. (default: :obj:`None`)
- **max_retries** (int, optional): Maximum number of retries for API calls. (default: :obj:`3`)

<a id="camel.models.base_model.BaseModelBackend.__init__"></a>

### __init__

```python
def __init__(
    self,
    model_type: Union[ModelType, str],
    model_config_dict: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None,
    url: Optional[str] = None,
    token_counter: Optional[BaseTokenCounter] = None,
    timeout: Optional[float] = Constants.TIMEOUT_THRESHOLD,
    max_retries: int = 3
):
```

<a id="camel.models.base_model.BaseModelBackend.token_counter"></a>

### token_counter

```python
def token_counter(self):
```

**Returns:**

  BaseTokenCounter: The token counter following the model's
tokenization style.

<a id="camel.models.base_model.BaseModelBackend.preprocess_messages"></a>

### preprocess_messages

```python
def preprocess_messages(self, messages: List[OpenAIMessage]):
```

Preprocess messages before sending to model API.
Removes thinking content from assistant and user messages.
Automatically formats messages for parallel tool calls if tools are
detected.

**Parameters:**

- **messages** (List[OpenAIMessage]): Original messages.

**Returns:**

  List[OpenAIMessage]: Preprocessed messages

<a id="camel.models.base_model.BaseModelBackend._log_request"></a>

### _log_request

```python
def _log_request(self, messages: List[OpenAIMessage]):
```

Log the request messages to a JSON file if logging is enabled.

**Parameters:**

- **messages** (List[OpenAIMessage]): The messages to log.

**Returns:**

  Optional[str]: The path to the log file if logging is enabled,
None otherwise.

<a id="camel.models.base_model.BaseModelBackend._log_response"></a>

### _log_response

```python
def _log_response(self, log_path: str, response: Any):
```

Log the response to the existing log file.

**Parameters:**

- **log_path** (str): The path to the log file.
- **response** (Any): The response to log.

<a id="camel.models.base_model.BaseModelBackend._run"></a>

### _run

```python
def _run(
    self,
    messages: List[OpenAIMessage],
    response_format: Optional[Type[BaseModel]] = None,
    tools: Optional[List[Dict[str, Any]]] = None
):
```

Runs the query to the backend model in a non-stream mode.

**Parameters:**

- **messages** (List[OpenAIMessage]): Message list with the chat history in OpenAI API format.
- **response_format** (Optional[Type[BaseModel]]): The format of the response.
- **tools** (Optional[List[Dict[str, Any]]]): The schema of the tools to use for the request.

**Returns:**

  Union[ChatCompletion, Stream[ChatCompletionChunk], Any]:
`ChatCompletion` in the non-stream mode, or
`Stream[ChatCompletionChunk]` in the stream mode,
or `ChatCompletionStreamManager[BaseModel]` in the structured
stream mode.

<a id="camel.models.base_model.BaseModelBackend.run"></a>

### run

```python
def run(
    self,
    messages: List[OpenAIMessage],
    response_format: Optional[Type[BaseModel]] = None,
    tools: Optional[List[Dict[str, Any]]] = None
):
```

Runs the query to the backend model.

**Parameters:**

- **messages** (List[OpenAIMessage]): Message list with the chat history in OpenAI API format.
- **response_format** (Optional[Type[BaseModel]]): The response format to use for the model. (default: :obj:`None`)
- **tools** (Optional[List[Tool]]): The schema of tools to use for the model for this request. Will override the tools specified in the model configuration (but not change the configuration). (default: :obj:`None`)

**Returns:**

  Union[ChatCompletion, Stream[ChatCompletionChunk], Any]:
`ChatCompletion` in the non-stream mode,
`Stream[ChatCompletionChunk]` in the stream mode, or
`ChatCompletionStreamManager[BaseModel]` in the structured
stream mode.

<a id="camel.models.base_model.BaseModelBackend.count_tokens_from_messages"></a>

### count_tokens_from_messages

```python
def count_tokens_from_messages(self, messages: List[OpenAIMessage]):
```

Count the number of tokens in the messages using the specific
tokenizer.

**Parameters:**

- **messages** (List[Dict]): message list with the chat history in OpenAI API format.

**Returns:**

  int: Number of tokens in the messages.

<a id="camel.models.base_model.BaseModelBackend._to_chat_completion"></a>

### _to_chat_completion

```python
def _to_chat_completion(self, response: ParsedChatCompletion):
```

<a id="camel.models.base_model.BaseModelBackend.token_limit"></a>

### token_limit

```python
def token_limit(self):
```

**Returns:**

  int: The maximum token limit for the given model.

<a id="camel.models.base_model.BaseModelBackend.stream"></a>

### stream

```python
def stream(self):
```

**Returns:**

  bool: Whether the model is in stream mode.
