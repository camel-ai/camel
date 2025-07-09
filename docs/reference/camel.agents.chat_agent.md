<a id="camel.agents.chat_agent"></a>

<a id="camel.agents.chat_agent.StreamContentAccumulator"></a>

## StreamContentAccumulator

```python
class StreamContentAccumulator:
```

Manages content accumulation across streaming responses to ensure
all responses contain complete cumulative content.

<a id="camel.agents.chat_agent.StreamContentAccumulator.__init__"></a>

### __init__

```python
def __init__(self):
```

<a id="camel.agents.chat_agent.StreamContentAccumulator.set_base_content"></a>

### set_base_content

```python
def set_base_content(self, content: str):
```

Set the base content (usually empty or pre-tool content).

<a id="camel.agents.chat_agent.StreamContentAccumulator.add_streaming_content"></a>

### add_streaming_content

```python
def add_streaming_content(self, new_content: str):
```

Add new streaming content.

<a id="camel.agents.chat_agent.StreamContentAccumulator.add_tool_status"></a>

### add_tool_status

```python
def add_tool_status(self, status_message: str):
```

Add a tool status message.

<a id="camel.agents.chat_agent.StreamContentAccumulator.get_full_content"></a>

### get_full_content

```python
def get_full_content(self):
```

Get the complete accumulated content.

<a id="camel.agents.chat_agent.StreamContentAccumulator.get_content_with_new_status"></a>

### get_content_with_new_status

```python
def get_content_with_new_status(self, status_message: str):
```

Get content with a new status message appended.

<a id="camel.agents.chat_agent.StreamContentAccumulator.reset_streaming_content"></a>

### reset_streaming_content

```python
def reset_streaming_content(self):
```

Reset only the streaming content, keep base and tool status.

<a id="camel.agents.chat_agent.StreamingChatAgentResponse"></a>

## StreamingChatAgentResponse

```python
class StreamingChatAgentResponse:
```

A wrapper that makes streaming responses compatible with
non-streaming code.

This class wraps a Generator[ChatAgentResponse, None, None] and provides
the same interface as ChatAgentResponse, so existing code doesn't need to
change.

<a id="camel.agents.chat_agent.StreamingChatAgentResponse.__init__"></a>

### __init__

```python
def __init__(self, generator: Generator[ChatAgentResponse, None, None]):
```

<a id="camel.agents.chat_agent.StreamingChatAgentResponse._ensure_latest_response"></a>

### _ensure_latest_response

```python
def _ensure_latest_response(self):
```

Ensure we have the latest response by consuming the generator.

<a id="camel.agents.chat_agent.StreamingChatAgentResponse.msgs"></a>

### msgs

```python
def msgs(self):
```

Get messages from the latest response.

<a id="camel.agents.chat_agent.StreamingChatAgentResponse.terminated"></a>

### terminated

```python
def terminated(self):
```

Get terminated status from the latest response.

<a id="camel.agents.chat_agent.StreamingChatAgentResponse.info"></a>

### info

```python
def info(self):
```

Get info from the latest response.

<a id="camel.agents.chat_agent.StreamingChatAgentResponse.msg"></a>

### msg

```python
def msg(self):
```

Get the single message if there's exactly one message.

<a id="camel.agents.chat_agent.StreamingChatAgentResponse.__iter__"></a>

### __iter__

```python
def __iter__(self):
```

Make this object iterable.

<a id="camel.agents.chat_agent.StreamingChatAgentResponse.__getattr__"></a>

### __getattr__

```python
def __getattr__(self, name):
```

Forward any other attribute access to the latest response.

<a id="camel.agents.chat_agent.AsyncStreamingChatAgentResponse"></a>

## AsyncStreamingChatAgentResponse

```python
class AsyncStreamingChatAgentResponse:
```

A wrapper that makes async streaming responses awaitable and
compatible with non-streaming code.

This class wraps an AsyncGenerator[ChatAgentResponse, None] and provides
both awaitable and async iterable interfaces.

<a id="camel.agents.chat_agent.AsyncStreamingChatAgentResponse.__init__"></a>

### __init__

```python
def __init__(self, async_generator: AsyncGenerator[ChatAgentResponse, None]):
```

<a id="camel.agents.chat_agent.AsyncStreamingChatAgentResponse.__await__"></a>

### __await__

```python
def __await__(self):
```

Make this object awaitable - returns the final response.

<a id="camel.agents.chat_agent.AsyncStreamingChatAgentResponse.__aiter__"></a>

### __aiter__

```python
def __aiter__(self):
```

Make this object async iterable.

<a id="camel.agents.chat_agent.ChatAgent"></a>

## ChatAgent

```python
class ChatAgent(BaseAgent):
```

Class for managing conversations of CAMEL Chat Agents.

**Parameters:**

- **system_message** (Union[BaseMessage, str], optional): The system message for the chat agent. (default: :obj:`None`) model (Union[BaseModelBackend, Tuple[str, str], str, ModelType, Tuple[ModelPlatformType, ModelType], List[BaseModelBackend], List[str], List[ModelType], List[Tuple[str, str]], List[Tuple[ModelPlatformType, ModelType]]], optional): The model backend(s) to use. Can be a single instance, a specification (string, enum, tuple), or a list of instances or specifications to be managed by `ModelManager`. If a list of specifications (not `BaseModelBackend` instances) is provided, they will be instantiated using `ModelFactory`. (default: :obj:`ModelPlatformType.DEFAULT` with `ModelType.DEFAULT`)
- **memory** (AgentMemory, optional): The agent memory for managing chat messages. If `None`, a :obj:`ChatHistoryMemory` will be used. (default: :obj:`None`)
- **message_window_size** (int, optional): The maximum number of previous messages to include in the context window. If `None`, no windowing is performed. (default: :obj:`None`)
- **token_limit** (int, optional): The maximum number of tokens in a context. The context will be automatically pruned to fulfill the limitation. If `None`, it will be set according to the backend model. (default: :obj:`None`)
- **output_language** (str, optional): The language to be output by the agent. (default: :obj:`None`)
- **tools** (Optional[List[Union[FunctionTool, Callable]]], optional): List of available :obj:`FunctionTool` or :obj:`Callable`. (default: :obj:`None`) external_tools (Optional[List[Union[FunctionTool, Callable, Dict[str, Any]]]], optional): List of external tools (:obj:`FunctionTool` or :obj:`Callable` or :obj:`Dict[str, Any]`) bind to one chat agent. When these tools are called, the agent will directly return the request instead of processing it. (default: :obj:`None`)
- **response_terminators** (List[ResponseTerminator], optional): List of :obj:`ResponseTerminator` bind to one chat agent. (default: :obj:`None`)
- **scheduling_strategy** (str): name of function that defines how to select the next model in ModelManager. (default: :str:`round_robin`)
- **max_iteration** (Optional[int], optional): Maximum number of model calling iterations allowed per step. If `None` (default), there's no explicit limit. If `1`, it performs a single model call. If `N > 1`, it allows up to N model calls. (default: :obj:`None`)
- **agent_id** (str, optional): The ID of the agent. If not provided, a random UUID will be generated. (default: :obj:`None`)
- **stop_event** (Optional[threading.Event], optional): Event to signal termination of the agent's operation. When set, the agent will terminate its execution. (default: :obj:`None`)
- **tool_execution_timeout** (Optional[float], optional): Timeout for individual tool execution. If None, wait indefinitely.
- **mask_tool_output** (Optional[bool]): Whether to return a sanitized placeholder instead of the raw tool output. (default: :obj:`False`)
- **pause_event** (Optional[asyncio.Event]): Event to signal pause of the agent's operation. When clear, the agent will pause its execution. (default: :obj:`None`)

<a id="camel.agents.chat_agent.ChatAgent.__init__"></a>

### __init__

```python
def __init__(
    self,
    system_message: Optional[Union[BaseMessage, str]] = None,
    model: Optional[Union[BaseModelBackend, ModelManager, Tuple[str, str], str, ModelType, Tuple[ModelPlatformType, ModelType], List[BaseModelBackend], List[str], List[ModelType], List[Tuple[str, str]], List[Tuple[ModelPlatformType, ModelType]]]] = None,
    memory: Optional[AgentMemory] = None,
    message_window_size: Optional[int] = None,
    token_limit: Optional[int] = None,
    output_language: Optional[str] = None,
    tools: Optional[List[Union[FunctionTool, Callable]]] = None,
    external_tools: Optional[List[Union[FunctionTool, Callable, Dict[str, Any]]]] = None,
    response_terminators: Optional[List[ResponseTerminator]] = None,
    scheduling_strategy: str = 'round_robin',
    max_iteration: Optional[int] = None,
    agent_id: Optional[str] = None,
    stop_event: Optional[threading.Event] = None,
    tool_execution_timeout: Optional[float] = None,
    mask_tool_output: bool = False,
    pause_event: Optional[asyncio.Event] = None
):
```

<a id="camel.agents.chat_agent.ChatAgent.reset"></a>

### reset

```python
def reset(self):
```

Resets the :obj:`ChatAgent` to its initial state.

<a id="camel.agents.chat_agent.ChatAgent._resolve_models"></a>

### _resolve_models

```python
def _resolve_models(
    self,
    model: Optional[Union[BaseModelBackend, Tuple[str, str], str, ModelType, Tuple[ModelPlatformType, ModelType], List[BaseModelBackend], List[str], List[ModelType], List[Tuple[str, str]], List[Tuple[ModelPlatformType, ModelType]]]]
):
```

Resolves model specifications into model backend instances.

This method handles various input formats for model specifications and
returns the appropriate model backend(s).

**Parameters:**

- **model**: Model specification in various formats including single model, list of models, or model type specifications.

**Returns:**

  Union[BaseModelBackend, List[BaseModelBackend]]: Resolved model
backend(s).

<a id="camel.agents.chat_agent.ChatAgent._resolve_model_list"></a>

### _resolve_model_list

```python
def _resolve_model_list(self, model_list: list):
```

Resolves a list of model specifications into model backend
instances.

**Parameters:**

- **model_list** (list): List of model specifications in various formats.

**Returns:**

  Union[BaseModelBackend, List[BaseModelBackend]]: Resolved model
backend(s).

<a id="camel.agents.chat_agent.ChatAgent.system_message"></a>

### system_message

```python
def system_message(self):
```

Returns the system message for the agent.

<a id="camel.agents.chat_agent.ChatAgent.tool_dict"></a>

### tool_dict

```python
def tool_dict(self):
```

Returns a dictionary of internal tools.

<a id="camel.agents.chat_agent.ChatAgent.output_language"></a>

### output_language

```python
def output_language(self):
```

Returns the output language for the agent.

<a id="camel.agents.chat_agent.ChatAgent.output_language"></a>

### output_language

```python
def output_language(self, value: str):
```

Set the output language for the agent.

Note that this will clear the message history.

<a id="camel.agents.chat_agent.ChatAgent._get_full_tool_schemas"></a>

### _get_full_tool_schemas

```python
def _get_full_tool_schemas(self):
```

Returns a list of tool schemas of all tools, including internal
and external tools.

<a id="camel.agents.chat_agent.ChatAgent._get_external_tool_names"></a>

### _get_external_tool_names

```python
def _get_external_tool_names(self):
```

Returns a set of external tool names.

<a id="camel.agents.chat_agent.ChatAgent.add_tool"></a>

### add_tool

```python
def add_tool(self, tool: Union[FunctionTool, Callable]):
```

Add a tool to the agent.

<a id="camel.agents.chat_agent.ChatAgent.add_tools"></a>

### add_tools

```python
def add_tools(self, tools: List[Union[FunctionTool, Callable]]):
```

Add a list of tools to the agent.

<a id="camel.agents.chat_agent.ChatAgent.add_external_tool"></a>

### add_external_tool

```python
def add_external_tool(self, tool: Union[FunctionTool, Callable, Dict[str, Any]]):
```

<a id="camel.agents.chat_agent.ChatAgent.remove_tool"></a>

### remove_tool

```python
def remove_tool(self, tool_name: str):
```

Remove a tool from the agent by name.

**Parameters:**

- **tool_name** (str): The name of the tool to remove.

**Returns:**

  bool: Whether the tool was successfully removed.

<a id="camel.agents.chat_agent.ChatAgent.remove_tools"></a>

### remove_tools

```python
def remove_tools(self, tool_names: List[str]):
```

Remove a list of tools from the agent by name.

<a id="camel.agents.chat_agent.ChatAgent.remove_external_tool"></a>

### remove_external_tool

```python
def remove_external_tool(self, tool_name: str):
```

Remove an external tool from the agent by name.

**Parameters:**

- **tool_name** (str): The name of the tool to remove.

**Returns:**

  bool: Whether the tool was successfully removed.

<a id="camel.agents.chat_agent.ChatAgent.update_memory"></a>

### update_memory

```python
def update_memory(
    self,
    message: BaseMessage,
    role: OpenAIBackendRole,
    timestamp: Optional[float] = None
):
```

Updates the agent memory with a new message.

If the single *message* exceeds the model's context window, it will
be **automatically split into multiple smaller chunks** before being
written into memory. This prevents later failures in
`ScoreBasedContextCreator` where an over-sized message cannot fit
into the available token budget at all.

This slicing logic handles both regular text messages (in the
`content` field) and long tool call results (in the `result` field of
a `FunctionCallingMessage`).

**Parameters:**

- **message** (BaseMessage): The new message to add to the stored messages.
- **role** (OpenAIBackendRole): The backend role type.
- **timestamp** (Optional[float], optional): Custom timestamp for the memory record. If `None`, the current time will be used. (default: :obj:`None`) (default: obj:`None`)

<a id="camel.agents.chat_agent.ChatAgent.load_memory"></a>

### load_memory

```python
def load_memory(self, memory: AgentMemory):
```

Load the provided memory into the agent.

**Parameters:**

- **memory** (AgentMemory): The memory to load into the agent.

**Returns:**

  None

<a id="camel.agents.chat_agent.ChatAgent.load_memory_from_path"></a>

### load_memory_from_path

```python
def load_memory_from_path(self, path: str):
```

Loads memory records from a JSON file filtered by this agent's ID.

**Parameters:**

- **path** (str): The file path to a JSON memory file that uses JsonStorage.

<a id="camel.agents.chat_agent.ChatAgent.save_memory"></a>

### save_memory

```python
def save_memory(self, path: str):
```

Retrieves the current conversation data from memory and writes it
into a JSON file using JsonStorage.

**Parameters:**

- **path** (str): Target file path to store JSON data.

<a id="camel.agents.chat_agent.ChatAgent.clear_memory"></a>

### clear_memory

```python
def clear_memory(self):
```

**Returns:**

  None

<a id="camel.agents.chat_agent.ChatAgent._generate_system_message_for_output_language"></a>

### _generate_system_message_for_output_language

```python
def _generate_system_message_for_output_language(self):
```

**Returns:**

  BaseMessage: The new system message.

<a id="camel.agents.chat_agent.ChatAgent.init_messages"></a>

### init_messages

```python
def init_messages(self):
```

Initializes the stored messages list with the current system
message.

<a id="camel.agents.chat_agent.ChatAgent.record_message"></a>

### record_message

```python
def record_message(self, message: BaseMessage):
```

Records the externally provided message into the agent memory as if
it were an answer of the :obj:`ChatAgent` from the backend. Currently,
the choice of the critic is submitted with this method.

**Parameters:**

- **message** (BaseMessage): An external message to be recorded in the memory.

<a id="camel.agents.chat_agent.ChatAgent._try_format_message"></a>

### _try_format_message

```python
def _try_format_message(self, message: BaseMessage, response_format: Type[BaseModel]):
```

**Returns:**

  bool: Whether the message is formatted successfully (or no format
is needed).

<a id="camel.agents.chat_agent.ChatAgent._check_tools_strict_compatibility"></a>

### _check_tools_strict_compatibility

```python
def _check_tools_strict_compatibility(self):
```

**Returns:**

  bool: True if all tools are strict mode compatible,
False otherwise.

<a id="camel.agents.chat_agent.ChatAgent._convert_response_format_to_prompt"></a>

### _convert_response_format_to_prompt

```python
def _convert_response_format_to_prompt(self, response_format: Type[BaseModel]):
```

Convert a Pydantic response format to a prompt instruction.

**Parameters:**

- **response_format** (Type[BaseModel]): The Pydantic model class.

**Returns:**

  str: A prompt instruction requesting the specific format.

<a id="camel.agents.chat_agent.ChatAgent._handle_response_format_with_non_strict_tools"></a>

### _handle_response_format_with_non_strict_tools

```python
def _handle_response_format_with_non_strict_tools(
    self,
    input_message: Union[BaseMessage, str],
    response_format: Optional[Type[BaseModel]] = None
):
```

Handle response format when tools are not strict mode compatible.

**Parameters:**

- **input_message**: The original input message.
- **response_format**: The requested response format.

**Returns:**

  Tuple: (modified_message, modified_response_format,
used_prompt_formatting)

<a id="camel.agents.chat_agent.ChatAgent._apply_prompt_based_parsing"></a>

### _apply_prompt_based_parsing

```python
def _apply_prompt_based_parsing(
    self,
    response: ModelResponse,
    original_response_format: Type[BaseModel]
):
```

Apply manual parsing when using prompt-based formatting.

**Parameters:**

- **response**: The model response to parse.
- **original_response_format**: The original response format class.

<a id="camel.agents.chat_agent.ChatAgent._format_response_if_needed"></a>

### _format_response_if_needed

```python
def _format_response_if_needed(
    self,
    response: ModelResponse,
    response_format: Optional[Type[BaseModel]] = None
):
```

Format the response if needed.

This function won't format the response under the following cases:
1. The response format is None (not provided)
2. The response is empty

<a id="camel.agents.chat_agent.ChatAgent.step"></a>

### step

```python
def step(
    self,
    input_message: Union[BaseMessage, str],
    response_format: Optional[Type[BaseModel]] = None
):
```

Executes a single step in the chat session, generating a response
to the input message.

**Parameters:**

- **input_message** (Union[BaseMessage, str]): The input message for the agent. If provided as a BaseMessage, the `role` is adjusted to `user` to indicate an external message.
- **response_format** (Optional[Type[BaseModel]], optional): A Pydantic model defining the expected structure of the response. Used to generate a structured response if provided. (default: :obj:`None`)

**Returns:**

  Union[ChatAgentResponse, StreamingChatAgentResponse]: If stream is
False, returns a ChatAgentResponse. If stream is True, returns
a StreamingChatAgentResponse that behaves like
ChatAgentResponse but can also be iterated for
streaming updates.

<a id="camel.agents.chat_agent.ChatAgent.chat_history"></a>

### chat_history

```python
def chat_history(self):
```

<a id="camel.agents.chat_agent.ChatAgent._create_token_usage_tracker"></a>

### _create_token_usage_tracker

```python
def _create_token_usage_tracker(self):
```

**Returns:**

  Dict[str, int]: A dictionary for tracking token usage.

<a id="camel.agents.chat_agent.ChatAgent._update_token_usage_tracker"></a>

### _update_token_usage_tracker

```python
def _update_token_usage_tracker(self, tracker: Dict[str, int], usage_dict: Dict[str, int]):
```

Updates a token usage tracker with values from a usage dictionary.

**Parameters:**

- **tracker** (Dict[str, int]): The token usage tracker to update.
- **usage_dict** (Dict[str, int]): The usage dictionary with new values.

<a id="camel.agents.chat_agent.ChatAgent._convert_to_chatagent_response"></a>

### _convert_to_chatagent_response

```python
def _convert_to_chatagent_response(
    self,
    response: ModelResponse,
    tool_call_records: List[ToolCallingRecord],
    num_tokens: int,
    external_tool_call_requests: Optional[List[ToolCallRequest]],
    step_api_prompt_tokens: int = 0,
    step_api_completion_tokens: int = 0,
    step_api_total_tokens: int = 0
):
```

Parse the final model response into the chat agent response.

<a id="camel.agents.chat_agent.ChatAgent._process_pending_images"></a>

### _process_pending_images

```python
def _process_pending_images(self):
```

**Returns:**

  List: List of successfully converted PIL Images.

<a id="camel.agents.chat_agent.ChatAgent._record_final_output"></a>

### _record_final_output

```python
def _record_final_output(self, output_messages: List[BaseMessage]):
```

Log final messages or warnings about multiple responses.

<a id="camel.agents.chat_agent.ChatAgent._is_vision_error"></a>

### _is_vision_error

```python
def _is_vision_error(self, exc: Exception):
```

Check if the exception is likely related to vision/image is not
supported by the model.

<a id="camel.agents.chat_agent.ChatAgent._has_images"></a>

### _has_images

```python
def _has_images(self, messages: List[OpenAIMessage]):
```

Check if any message contains images.

<a id="camel.agents.chat_agent.ChatAgent._strip_images_from_messages"></a>

### _strip_images_from_messages

```python
def _strip_images_from_messages(self, messages: List[OpenAIMessage]):
```

Remove images from messages, keeping only text content.

<a id="camel.agents.chat_agent.ChatAgent._get_model_response"></a>

### _get_model_response

```python
def _get_model_response(
    self,
    openai_messages: List[OpenAIMessage],
    num_tokens: int,
    response_format: Optional[Type[BaseModel]] = None,
    tool_schemas: Optional[List[Dict[str, Any]]] = None
):
```

Internal function for agent step model response.

<a id="camel.agents.chat_agent.ChatAgent._sanitize_messages_for_logging"></a>

### _sanitize_messages_for_logging

```python
def _sanitize_messages_for_logging(self, messages):
```

Sanitize OpenAI messages for logging by replacing base64 image
data with a simple message and a link to view the image.

**Parameters:**

- **messages** (List[OpenAIMessage]): The OpenAI messages to sanitize.

**Returns:**

  List[OpenAIMessage]: The sanitized OpenAI messages.

<a id="camel.agents.chat_agent.ChatAgent._step_get_info"></a>

### _step_get_info

```python
def _step_get_info(
    self,
    output_messages: List[BaseMessage],
    finish_reasons: List[str],
    usage_dict: Dict[str, int],
    response_id: str,
    tool_calls: List[ToolCallingRecord],
    num_tokens: int,
    external_tool_call_requests: Optional[List[ToolCallRequest]] = None
):
```

Process the output of a chat step and gather information about the
step.

This method checks for termination conditions, updates the agent's
state, and collects information about the chat step, including tool
calls and termination reasons.

**Parameters:**

- **output_messages** (List[BaseMessage]): The messages generated in this step.
- **finish_reasons** (List[str]): The reasons for finishing the generation for each message.
- **usage_dict** (Dict[str, int]): Dictionary containing token usage information.
- **response_id** (str): The ID of the response from the model.
- **tool_calls** (List[ToolCallingRecord]): Records of function calls made during this step.
- **num_tokens** (int): The number of tokens used in this step.
- **external_tool_call_request** (Optional[ToolCallRequest]): The request for external tool call.

**Returns:**

  Dict[str, Any]: A dictionary containing information about the chat
step, including termination status, reasons, and tool call
information.

**Note:**

This method iterates over all response terminators and checks if
any of them signal termination. If a terminator signals
termination, the agent's state is updated accordingly, and the
termination reason is recorded.

<a id="camel.agents.chat_agent.ChatAgent._handle_batch_response"></a>

### _handle_batch_response

```python
def _handle_batch_response(self, response: ChatCompletion):
```

Process a batch response from the model and extract the necessary
information.

**Parameters:**

- **response** (ChatCompletion): Model response.

**Returns:**

  _ModelResponse: parsed model response.

<a id="camel.agents.chat_agent.ChatAgent._step_terminate"></a>

### _step_terminate

```python
def _step_terminate(
    self,
    num_tokens: int,
    tool_calls: List[ToolCallingRecord],
    termination_reason: str
):
```

Create a response when the agent execution is terminated.

This method is called when the agent needs to terminate its execution
due to various reasons such as token limit exceeded, or other
termination conditions. It creates a response with empty messages but
includes termination information in the info dictionary.

**Parameters:**

- **num_tokens** (int): Number of tokens in the messages.
- **tool_calls** (List[ToolCallingRecord]): List of information objects of functions called in the current step.
- **termination_reason** (str): String describing the reason for termination.

**Returns:**

  ChatAgentResponse: A response object with empty message list,
terminated flag set to True, and an info dictionary containing
termination details, token counts, and tool call information.

<a id="camel.agents.chat_agent.ChatAgent._execute_tool"></a>

### _execute_tool

```python
def _execute_tool(self, tool_call_request: ToolCallRequest):
```

Execute the tool with arguments following the model's response.

**Parameters:**

- **tool_call_request** (_ToolCallRequest): The tool call request.

**Returns:**

  FunctionCallingRecord: A struct for logging information about this
function call.

<a id="camel.agents.chat_agent.ChatAgent._record_tool_calling"></a>

### _record_tool_calling

```python
def _record_tool_calling(
    self,
    func_name: str,
    args: Dict[str, Any],
    result: Any,
    tool_call_id: str,
    mask_output: bool = False
):
```

Record the tool calling information in the memory, and return the
tool calling record.

**Parameters:**

- **func_name** (str): The name of the tool function called.
- **args** (Dict[str, Any]): The arguments passed to the tool.
- **result** (Any): The result returned by the tool execution.
- **tool_call_id** (str): A unique identifier for the tool call.
- **mask_output** (bool, optional): Whether to return a sanitized placeholder instead of the raw tool output. (default: :obj:`False`)

**Returns:**

  ToolCallingRecord: A struct containing information about
this tool call.

<a id="camel.agents.chat_agent.ChatAgent._stream"></a>

### _stream

```python
def _stream(
    self,
    input_message: Union[BaseMessage, str],
    response_format: Optional[Type[BaseModel]] = None
):
```

Executes a streaming step in the chat session, yielding
intermediate responses as they are generated.

**Parameters:**

- **input_message** (Union[BaseMessage, str]): The input message for the agent.
- **response_format** (Optional[Type[BaseModel]], optional): A Pydantic model defining the expected structure of the response.
- **Yields**: 
- **ChatAgentResponse**: Intermediate responses containing partial content, tool calls, and other information as they become available.

<a id="camel.agents.chat_agent.ChatAgent._get_token_count"></a>

### _get_token_count

```python
def _get_token_count(self, content: str):
```

Get token count for content with fallback.

<a id="camel.agents.chat_agent.ChatAgent._stream_response"></a>

### _stream_response

```python
def _stream_response(
    self,
    openai_messages: List[OpenAIMessage],
    num_tokens: int,
    response_format: Optional[Type[BaseModel]] = None
):
```

Internal method to handle streaming responses with tool calls.

<a id="camel.agents.chat_agent.ChatAgent._process_stream_chunks_with_accumulator"></a>

### _process_stream_chunks_with_accumulator

```python
def _process_stream_chunks_with_accumulator(
    self,
    stream: Stream[ChatCompletionChunk],
    content_accumulator: StreamContentAccumulator,
    accumulated_tool_calls: Dict[str, Any],
    tool_call_records: List[ToolCallingRecord],
    step_token_usage: Dict[str, int],
    response_format: Optional[Type[BaseModel]] = None
):
```

Process streaming chunks with content accumulator.

<a id="camel.agents.chat_agent.ChatAgent._accumulate_tool_calls"></a>

### _accumulate_tool_calls

```python
def _accumulate_tool_calls(
    self,
    tool_call_deltas: List[Any],
    accumulated_tool_calls: Dict[str, Any]
):
```

Accumulate tool call chunks and return True when
any tool call is complete.

**Parameters:**

- **tool_call_deltas** (List[Any]): List of tool call deltas.
- **accumulated_tool_calls** (Dict[str, Any]): Dictionary of accumulated tool calls.

**Returns:**

  bool: True if any tool call is complete, False otherwise.

<a id="camel.agents.chat_agent.ChatAgent._execute_tools_sync_with_status_accumulator"></a>

### _execute_tools_sync_with_status_accumulator

```python
def _execute_tools_sync_with_status_accumulator(
    self,
    accumulated_tool_calls: Dict[str, Any],
    content_accumulator: StreamContentAccumulator,
    step_token_usage: Dict[str, int],
    tool_call_records: List[ToolCallingRecord]
):
```

Execute multiple tools synchronously with
proper content accumulation, using threads+queue for
non-blocking status streaming.

<a id="camel.agents.chat_agent.ChatAgent._execute_tool_from_stream_data"></a>

### _execute_tool_from_stream_data

```python
def _execute_tool_from_stream_data(self, tool_call_data: Dict[str, Any]):
```

Execute a tool from accumulated stream data.

<a id="camel.agents.chat_agent.ChatAgent._create_error_response"></a>

### _create_error_response

```python
def _create_error_response(
    self,
    error_message: str,
    tool_call_records: List[ToolCallingRecord]
):
```

Create an error response for streaming.

<a id="camel.agents.chat_agent.ChatAgent._record_assistant_tool_calls_message"></a>

### _record_assistant_tool_calls_message

```python
def _record_assistant_tool_calls_message(self, accumulated_tool_calls: Dict[str, Any], content: str = ''):
```

Record the assistant message that contains tool calls.

This method creates and records an assistant message that includes
the tool calls information, which is required by OpenAI's API format.

<a id="camel.agents.chat_agent.ChatAgent._create_tool_status_response_with_accumulator"></a>

### _create_tool_status_response_with_accumulator

```python
def _create_tool_status_response_with_accumulator(
    self,
    accumulator: StreamContentAccumulator,
    status_message: str,
    status_type: str,
    step_token_usage: Dict[str, int],
    tool_calls: Optional[List[ToolCallingRecord]] = None
):
```

Create a tool status response using content accumulator.

<a id="camel.agents.chat_agent.ChatAgent._create_streaming_response_with_accumulator"></a>

### _create_streaming_response_with_accumulator

```python
def _create_streaming_response_with_accumulator(
    self,
    accumulator: StreamContentAccumulator,
    new_content: str,
    step_token_usage: Dict[str, int],
    response_id: str = '',
    tool_call_records: Optional[List[ToolCallingRecord]] = None
):
```

Create a streaming response using content accumulator.

<a id="camel.agents.chat_agent.ChatAgent.get_usage_dict"></a>

### get_usage_dict

```python
def get_usage_dict(self, output_messages: List[BaseMessage], prompt_tokens: int):
```

Get usage dictionary when using the stream mode.

**Parameters:**

- **output_messages** (list): List of output messages.
- **prompt_tokens** (int): Number of input prompt tokens.

**Returns:**

  dict: Usage dictionary.

<a id="camel.agents.chat_agent.ChatAgent.add_model_scheduling_strategy"></a>

### add_model_scheduling_strategy

```python
def add_model_scheduling_strategy(self, name: str, strategy_fn: Callable):
```

Add a scheduling strategy method provided by user to ModelManger.

**Parameters:**

- **name** (str): The name of the strategy.
- **strategy_fn** (Callable): The scheduling strategy function.

<a id="camel.agents.chat_agent.ChatAgent.clone"></a>

### clone

```python
def clone(self, with_memory: bool = False):
```

Creates a new instance of :obj:`ChatAgent` with the same
configuration as the current instance.

**Parameters:**

- **with_memory** (bool): Whether to copy the memory (conversation history) to the new agent. If True, the new agent will have the same conversation history. If False, the new agent will have a fresh memory with only the system message. (default: :obj:`False`)

**Returns:**

  ChatAgent: A new instance of :obj:`ChatAgent` with the same
configuration.

<a id="camel.agents.chat_agent.ChatAgent._clone_tools"></a>

### _clone_tools

```python
def _clone_tools(self):
```

Clone tools for new agent instance,
handling stateful toolkits properly.

<a id="camel.agents.chat_agent.ChatAgent.__repr__"></a>

### __repr__

```python
def __repr__(self):
```

**Returns:**

  str: The string representation of the :obj:`ChatAgent`.

<a id="camel.agents.chat_agent.ChatAgent.to_mcp"></a>

### to_mcp

```python
def to_mcp(
    self,
    name: str = 'CAMEL-ChatAgent',
    description: str = 'A helpful assistant using the CAMEL AI framework.',
    dependencies: Optional[List[str]] = None,
    host: str = 'localhost',
    port: int = 8000
):
```

Expose this ChatAgent as an MCP server.

**Parameters:**

- **name** (str): Name of the MCP server. (default: :obj:`CAMEL-ChatAgent`)
- **description** (Optional[List[str]]): Description of the agent. If None, a generic description is used. (default: :obj:`A helpful assistant using the CAMEL AI framework.`)
- **dependencies** (Optional[List[str]]): Additional dependencies for the MCP server. (default: :obj:`None`)
- **host** (str): Host to bind to for HTTP transport. (default: :obj:`localhost`)
- **port** (int): Port to bind to for HTTP transport. (default: :obj:`8000`)

**Returns:**

  FastMCP: An MCP server instance that can be run.
