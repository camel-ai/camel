<a id="camel.toolkits.message_agent_toolkit"></a>

<a id="camel.toolkits.message_agent_toolkit.MessageAgentTool"></a>

## MessageAgentTool

```python
class MessageAgentTool(BaseToolkit):
```

A toolkit for agent-to-agent communication.

This toolkit allows agents to send messages to other agents by their IDs
and receive responses, enabling multi-agent collaboration.

**Parameters:**

- **agents** (Optional[Dict[str, ChatAgent]], optional): Dictionary mapping agent IDs to ChatAgent instances. (default: :obj:`None`)
- **timeout** (Optional[float], optional): Maximum execution time allowed for toolkit operations in seconds. If None, no timeout is applied. (default: :obj:`None`)

<a id="camel.toolkits.message_agent_toolkit.MessageAgentTool.__init__"></a>

### __init__

```python
def __init__(
    self,
    agents: Optional[Dict[str, ChatAgent]] = None,
    timeout: Optional[float] = None
):
```

<a id="camel.toolkits.message_agent_toolkit.MessageAgentTool.register_agent"></a>

### register_agent

```python
def register_agent(self, agent_id: str, agent: ChatAgent):
```

Register a new agent for communication.

**Parameters:**

- **agent_id** (str): Unique identifier for the agent.
- **agent** (ChatAgent): The ChatAgent instance to register.

**Returns:**

  str: Confirmation message.

<a id="camel.toolkits.message_agent_toolkit.MessageAgentTool.message_agent"></a>

### message_agent

```python
def message_agent(self, message: str, receiver_agent_id: str):
```

Send a message to another agent and get the response.

**Parameters:**

- **message** (str): The message to send to the target agent.
- **receiver_agent_id** (str): Unique identifier of the target agent.

**Returns:**

  str: Response from the target agent or error message if the
operation fails.

<a id="camel.toolkits.message_agent_toolkit.MessageAgentTool.list_available_agents"></a>

### list_available_agents

```python
def list_available_agents(self):
```

**Returns:**

  str: Formatted list of registered agent IDs or message if no
agents are registered.

<a id="camel.toolkits.message_agent_toolkit.MessageAgentTool.remove_agent"></a>

### remove_agent

```python
def remove_agent(self, agent_id: str):
```

Remove an agent from the communication registry.

**Parameters:**

- **agent_id** (str): Unique identifier of the agent to remove.

**Returns:**

  str: Confirmation message or error message if agent not found.

<a id="camel.toolkits.message_agent_toolkit.MessageAgentTool.get_agent_count"></a>

### get_agent_count

```python
def get_agent_count(self):
```

**Returns:**

  str: Number of currently registered agents.

<a id="camel.toolkits.message_agent_toolkit.MessageAgentTool.get_tools"></a>

### get_tools

```python
def get_tools(self):
```

**Returns:**

  List[FunctionTool]: A list of FunctionTool objects for agent
communication and management.
