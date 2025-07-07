<a id="camel.models.model_manager"></a>

<a id="camel.models.model_manager.ModelProcessingError"></a>

## ModelProcessingError

```python
class ModelProcessingError(Exception):
```

Raised when an error occurs during model processing.

<a id="camel.models.model_manager.ModelManager"></a>

## ModelManager

```python
class ModelManager:
```

ModelManager choosing a model from provided list.
Models are picked according to defined strategy.

**Parameters:**

- **models** (Union[BaseModelBackend, List[BaseModelBackend]]): model backend or list of model backends (e.g., model instances, APIs)
- **scheduling_strategy** (str): name of function that defines how to select the next model. (default: :str:`round_robin`)

<a id="camel.models.model_manager.ModelManager.__init__"></a>

### __init__

```python
def __init__(
    self,
    models: Union[BaseModelBackend, List[BaseModelBackend]],
    scheduling_strategy: str = 'round_robin'
):
```

<a id="camel.models.model_manager.ModelManager.model_type"></a>

### model_type

```python
def model_type(self):
```

**Returns:**

  Union[ModelType, str]: Current model type.

<a id="camel.models.model_manager.ModelManager.model_config_dict"></a>

### model_config_dict

```python
def model_config_dict(self):
```

**Returns:**

  Dict[str, Any]: Config dictionary of the current model.

<a id="camel.models.model_manager.ModelManager.model_config_dict"></a>

### model_config_dict

```python
def model_config_dict(self, model_config_dict: Dict[str, Any]):
```

Set model_config_dict to the current model.

**Parameters:**

- **model_config_dict** (Dict[str, Any]): Config dictionary to be set at current model.

<a id="camel.models.model_manager.ModelManager.current_model_index"></a>

### current_model_index

```python
def current_model_index(self):
```

**Returns:**

  int: index of current model in given list of models.

<a id="camel.models.model_manager.ModelManager.num_models"></a>

### num_models

```python
def num_models(self):
```

**Returns:**

  int: The number of models available in the model manager.

<a id="camel.models.model_manager.ModelManager.token_limit"></a>

### token_limit

```python
def token_limit(self):
```

**Returns:**

  int: The maximum token limit for the given model.

<a id="camel.models.model_manager.ModelManager.token_counter"></a>

### token_counter

```python
def token_counter(self):
```

**Returns:**

  BaseTokenCounter: The token counter following the model's
tokenization style.

<a id="camel.models.model_manager.ModelManager.add_strategy"></a>

### add_strategy

```python
def add_strategy(self, name: str, strategy_fn: Callable):
```

Add a scheduling strategy method provided by user in case when none
of existent strategies fits.
When custom strategy is provided, it will be set as
"self.scheduling_strategy" attribute.

**Parameters:**

- **name** (str): The name of the strategy.
- **strategy_fn** (Callable): The scheduling strategy function.

<a id="camel.models.model_manager.ModelManager.round_robin"></a>

### round_robin

```python
def round_robin(self):
```

**Returns:**

  BaseModelBackend for processing incoming messages.

<a id="camel.models.model_manager.ModelManager.always_first"></a>

### always_first

```python
def always_first(self):
```

**Returns:**

  BaseModelBackend for processing incoming messages.

<a id="camel.models.model_manager.ModelManager.random_model"></a>

### random_model

```python
def random_model(self):
```

**Returns:**

  BaseModelBackend for processing incoming messages.

<a id="camel.models.model_manager.ModelManager.run"></a>

### run

```python
def run(
    self,
    messages: List[OpenAIMessage],
    response_format: Optional[Type[BaseModel]] = None,
    tools: Optional[List[Dict[str, Any]]] = None
):
```

Process a list of messages by selecting a model based on
the scheduling strategy.
Sends the entire list of messages to the selected model,
and returns a single response.

**Parameters:**

- **messages** (List[OpenAIMessage]): Message list with the chat history in OpenAI API format.

**Returns:**

  Union[ChatCompletion, Stream[ChatCompletionChunk],
ChatCompletionStreamManager[BaseModel]]:
`ChatCompletion` in the non-stream mode, or
`Stream[ChatCompletionChunk]` in the stream mode, or
`ChatCompletionStreamManager[BaseModel]` for
structured-output stream.
