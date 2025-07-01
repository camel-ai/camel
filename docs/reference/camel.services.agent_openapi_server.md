<a id="camel.services.agent_openapi_server"></a>

<a id="camel.services.agent_openapi_server.InitRequest"></a>

## InitRequest

```python
class InitRequest(BaseModel):
```

Request schema for initializing a ChatAgent via the OpenAPI server.

Defines the configuration used to create a new agent, including the model,
system message, tool names, and generation parameters.

**Parameters:**

- **model_type** (Optional[str]): The model type to use. Should match a key supported by the model manager, e.g., "gpt-4o-mini". (default: :obj:`"gpt-4o-mini"`)
- **model_platform** (Optional[str]): The model platform to use. (default: :obj:`"openai"`)
- **tools_names** (Optional[List[str]]): A list of tool names to load from the tool registry. These tools will be available to the agent. (default: :obj:`None`)
- **external_tools** (Optional[List[Dict[str, Any]]]): Tool definitions provided directly as dictionaries, bypassing the registry. Currently not supported. (default: :obj:`None`)
- **agent_id** (str): The unique identifier for the agent. Must be provided explicitly to support multi-agent routing and control.
- **system_message** (Optional[str]): The system prompt for the agent, describing its behavior or role. (default: :obj:`None`)
- **message_window_size** (Optional[int]): The number of recent messages to retain in memory for context. (default: :obj:`None`)
- **token_limit** (Optional[int]): The token budget for contextual memory. (default: :obj:`None`)
- **output_language** (Optional[str]): Preferred output language for the agent's replies. (default: :obj:`None`)
- **max_iteration** (Optional[int]): Maximum number of model calling iterations allowed per step. If `None` (default), there's no explicit limit. If `1`, it performs a single model call. If `N > 1`, it allows up to N model calls. (default: :obj:`None`)

<a id="camel.services.agent_openapi_server.StepRequest"></a>

## StepRequest

```python
class StepRequest(BaseModel):
```

Request schema for sending a user message to a ChatAgent.

Supports plain text input or structured message dictionaries, with an
optional response format for controlling output structure.

**Parameters:**

- **input_message** (Union[str, Dict[str, Any]]): The user message to send. Can be a plain string or a message dict with role, content, etc.
- **response_format** (Optional[str]): Optional format name that maps to a registered response schema. Not currently in use. (default: :obj:`None`)

<a id="camel.services.agent_openapi_server.ChatAgentOpenAPIServer"></a>

## ChatAgentOpenAPIServer

```python
class ChatAgentOpenAPIServer:
```

A FastAPI server wrapper for managing ChatAgents via OpenAPI routes.

This server exposes a versioned REST API for interacting with CAMEL
agents, supporting initialization, message passing, memory inspection,
and optional tool usage. It supports multi-agent use cases by mapping
unique agent IDs to active ChatAgent instances.

Typical usage includes initializing agents with system prompts and tools,
exchanging messages using /step or /astep endpoints, and inspecting agent
memory with /history.

Supports pluggable tool and response format registries for customizing
agent behavior or output schemas.

<a id="camel.services.agent_openapi_server.ChatAgentOpenAPIServer.__init__"></a>

### __init__

```python
def __init__(
    self,
    tool_registry: Optional[Dict[str, List[FunctionTool]]] = None,
    response_format_registry: Optional[Dict[str, Type[BaseModel]]] = None
):
```

Initializes the OpenAPI server for managing ChatAgents.

Sets up internal agent storage, tool and response format registries,
and prepares versioned API routes.

**Parameters:**

- **tool_registry** (Optional[Dict[str, List[FunctionTool]]]): A mapping from tool names to lists of FunctionTool instances available to agents via the "tools_names" field. If not provided, an empty registry is used. (default: :obj:`None`)
- **response_format_registry** (Optional[Dict[str, Type[BaseModel]]]): A mapping from format names to Pydantic output schemas for structured response parsing. Used for controlling the format of step results. (default: :obj:`None`)

<a id="camel.services.agent_openapi_server.ChatAgentOpenAPIServer._parse_input_message_for_step"></a>

### _parse_input_message_for_step

```python
def _parse_input_message_for_step(self, raw: Union[str, dict]):
```

Parses raw input into a BaseMessage object.

**Parameters:**

- **raw** (str or dict): User input as plain text or dict.

**Returns:**

  BaseMessage: Parsed input message.

<a id="camel.services.agent_openapi_server.ChatAgentOpenAPIServer._resolve_response_format_for_step"></a>

### _resolve_response_format_for_step

```python
def _resolve_response_format_for_step(self, name: Optional[str]):
```

Resolves the response format by name.

**Parameters:**

- **name** (str or None): Optional format name.

**Returns:**

  Optional[Type[BaseModel]]: Response schema class.

<a id="camel.services.agent_openapi_server.ChatAgentOpenAPIServer._setup_routes"></a>

### _setup_routes

```python
def _setup_routes(self):
```

Registers OpenAPI endpoints for agent creation and interaction.

This includes routes for initializing agents (/init), sending
messages (/step and /astep), resetting agent memory (/reset), and
retrieving conversation history (/history). All routes are added
under the /v1/agents namespace.

<a id="camel.services.agent_openapi_server.ChatAgentOpenAPIServer.get_app"></a>

### get_app

```python
def get_app(self):
```

**Returns:**

  FastAPI: The wrapped application object.
