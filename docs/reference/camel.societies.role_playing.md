<a id="camel.societies.role_playing"></a>

<a id="camel.societies.role_playing.RolePlaying"></a>

## RolePlaying

```python
class RolePlaying:
```

Role playing between two agents.

**Parameters:**

- **assistant_role_name** (str): The name of the role played by the assistant.
- **user_role_name** (str): The name of the role played by the user.
- **critic_role_name** (str, optional): The name of the role played by the critic. Role name with :obj:`"human"` will set critic as a :obj:`Human` agent, else will create a :obj:`CriticAgent`. (default: :obj:`"critic"`)
- **task_prompt** (str, optional): A prompt for the task to be performed. (default: :obj:`""`)
- **with_task_specify** (bool, optional): Whether to use a task specify agent. (default: :obj:`True`)
- **with_task_planner** (bool, optional): Whether to use a task planner agent. (default: :obj:`False`)
- **with_critic_in_the_loop** (bool, optional): Whether to include a critic in the loop. (default: :obj:`False`)
- **critic_criteria** (str, optional): Critic criteria for the critic agent. If not specified, set the criteria to improve task performance.
- **model** (BaseModelBackend, optional): The model backend to use for generating responses. If specified, it will override the model in all agents if not specified in agent-specific kwargs. (default: :obj:`OpenAIModel` with `GPT_4O_MINI`)
- **task_type** (TaskType, optional): The type of task to perform. (default: :obj:`TaskType.AI_SOCIETY`)
- **assistant_agent_kwargs** (Dict, optional): Additional arguments to pass to the assistant agent. (default: :obj:`None`)
- **user_agent_kwargs** (Dict, optional): Additional arguments to pass to the user agent. (default: :obj:`None`)
- **task_specify_agent_kwargs** (Dict, optional): Additional arguments to pass to the task specify agent. (default: :obj:`None`)
- **task_planner_agent_kwargs** (Dict, optional): Additional arguments to pass to the task planner agent. (default: :obj:`None`)
- **critic_kwargs** (Dict, optional): Additional arguments to pass to the critic. (default: :obj:`None`)
- **sys_msg_generator_kwargs** (Dict, optional): Additional arguments to pass to the system message generator. (default: :obj:`None`)
- **extend_sys_msg_meta_dicts** (List[Dict], optional): A list of dicts to extend the system message meta dicts with. (default: :obj:`None`)
- **extend_task_specify_meta_dict** (Dict, optional): A dict to extend the task specify meta dict with. (default: :obj:`None`)
- **output_language** (str, optional): The language to be output by the agents. (default: :obj:`None`)
- **stop_event** (Optional[threading.Event], optional): Event to signal termination of the agent's operation. When set, the agent will terminate its execution. (default: :obj:`None`)

<a id="camel.societies.role_playing.RolePlaying.__init__"></a>

### __init__

```python
def __init__(self, assistant_role_name: str, user_role_name: str):
```

<a id="camel.societies.role_playing.RolePlaying._init_specified_task_prompt"></a>

### _init_specified_task_prompt

```python
def _init_specified_task_prompt(
    self,
    assistant_role_name: str,
    user_role_name: str,
    task_specify_agent_kwargs: Optional[Dict] = None,
    extend_task_specify_meta_dict: Optional[Dict] = None,
    output_language: Optional[str] = None
):
```

Use a task specify agent to generate a specified task prompt.
Generated specified task prompt will be used to replace original
task prompt. If there is no task specify agent, specified task
prompt will not be generated.

**Parameters:**

- **assistant_role_name** (str): The name of the role played by the assistant.
- **user_role_name** (str): The name of the role played by the user.
- **task_specify_agent_kwargs** (Dict, optional): Additional arguments to pass to the task specify agent. (default: :obj:`None`)
- **extend_task_specify_meta_dict** (Dict, optional): A dict to extend the task specify meta dict with. (default: :obj:`None`)
- **output_language** (str, optional): The language to be output by the agents. (default: :obj:`None`)

<a id="camel.societies.role_playing.RolePlaying._init_planned_task_prompt"></a>

### _init_planned_task_prompt

```python
def _init_planned_task_prompt(
    self,
    task_planner_agent_kwargs: Optional[Dict] = None,
    output_language: Optional[str] = None
):
```

Use a task plan agent to append a planned task prompt to task
prompt. The planned task prompt is generated based on the task
prompt, which can be original task prompt or specified task prompt
if available. If there is no task plan agent, planned task prompt
will not be generated.

**Parameters:**

- **task_planner_agent_kwargs** (Dict, optional): Additional arguments to pass to the task planner agent. (default: :obj:`None`)
- **output_language** (str, optional): The language to be output by the agents. (default: :obj:`None`)

<a id="camel.societies.role_playing.RolePlaying._get_sys_message_info"></a>

### _get_sys_message_info

```python
def _get_sys_message_info(
    self,
    assistant_role_name: str,
    user_role_name: str,
    sys_msg_generator: SystemMessageGenerator,
    extend_sys_msg_meta_dicts: Optional[List[Dict]] = None
):
```

Get initial assistant and user system message with a list of
system message meta dicts.

**Parameters:**

- **assistant_role_name** (str): The name of the role played by the assistant.
- **user_role_name** (str): The name of the role played by the user.
- **sys_msg_generator** (SystemMessageGenerator): A system message generator for agents.
- **extend_sys_msg_meta_dicts** (List[Dict], optional): A list of dicts to extend the system message meta dicts with. (default: :obj:`None`)

**Returns:**

  Tuple[BaseMessage, BaseMessage, List[Dict]]: A tuple containing a
`BaseMessage` representing the assistant's initial system
message, a `BaseMessage` representing the user's initial system
message, and a list of system message meta dicts.

<a id="camel.societies.role_playing.RolePlaying._init_agents"></a>

### _init_agents

```python
def _init_agents(
    self,
    init_assistant_sys_msg: BaseMessage,
    init_user_sys_msg: BaseMessage,
    assistant_agent_kwargs: Optional[Dict] = None,
    user_agent_kwargs: Optional[Dict] = None,
    output_language: Optional[str] = None,
    stop_event: Optional[threading.Event] = None
):
```

Initialize assistant and user agents with their system messages.

**Parameters:**

- **init_assistant_sys_msg** (BaseMessage): Assistant agent's initial system message.
- **init_user_sys_msg** (BaseMessage): User agent's initial system message.
- **assistant_agent_kwargs** (Dict, optional): Additional arguments to pass to the assistant agent. (default: :obj:`None`)
- **user_agent_kwargs** (Dict, optional): Additional arguments to pass to the user agent. (default: :obj:`None`)
- **output_language** (str, optional): The language to be output by the agents. (default: :obj:`None`)
- **stop_event** (Optional[threading.Event], optional): Event to signal termination of the agent's operation. When set, the agent will terminate its execution. (default: :obj:`None`)

<a id="camel.societies.role_playing.RolePlaying._init_critic"></a>

### _init_critic

```python
def _init_critic(
    self,
    sys_msg_generator: SystemMessageGenerator,
    sys_msg_meta_dicts: List[Dict],
    critic_role_name: str,
    critic_criteria: Optional[str] = None,
    critic_kwargs: Optional[Dict] = None
):
```

Initialize critic agent. If critic role name is :obj:`"human"`,
create a :obj:`Human` critic agent. Else, create a :obj:`CriticAgent`
critic agent with specified critic criteria. If the critic criteria
is not specified, set it to improve task performance.

**Parameters:**

- **sys_msg_generator** (SystemMessageGenerator): A system message generator for agents.
- **sys_msg_meta_dicts** (list): A list of system message meta dicts.
- **critic_role_name** (str): The name of the role played by the critic.
- **critic_criteria** (str, optional): Critic criteria for the critic agent. If not specified, set the criteria to improve task performance. (default: :obj:`None`)
- **critic_kwargs** (Dict, optional): Additional arguments to pass to the critic. (default: :obj:`None`)

<a id="camel.societies.role_playing.RolePlaying._reduce_message_options"></a>

### _reduce_message_options

```python
def _reduce_message_options(self, messages: Sequence[BaseMessage]):
```

Processes a sequence of chat messages, returning the processed
message. If multiple messages are provided and
`with_critic_in_the_loop` is `False`, raises a `ValueError`.
If no messages are provided, a `ValueError` will be raised.

**Parameters:**

- **messages** (Sequence[BaseMessage]): A sequence of `BaseMessage` objects to process.

**Returns:**

  BaseMessage: A single `BaseMessage` representing the processed
message.

<a id="camel.societies.role_playing.RolePlaying.init_chat"></a>

### init_chat

```python
def init_chat(self, init_msg_content: Optional[str] = None):
```

Initializes the chat by resetting both of the assistant and user
agents. Returns an initial message for the role-playing session.

**Parameters:**

- **init_msg_content** (str, optional): A user-specified initial message. Will be sent to the role-playing session as the initial message. (default: :obj:`None`)

**Returns:**

  BaseMessage: A single `BaseMessage` representing the initial
message.

<a id="camel.societies.role_playing.RolePlaying.step"></a>

### step

```python
def step(self, assistant_msg: BaseMessage):
```

Advances the conversation by taking a message from the assistant,
processing it using the user agent, and then processing the resulting
message using the assistant agent. Returns a tuple containing the
resulting assistant message, whether the assistant agent terminated
the conversation, and any additional assistant information, as well as
a tuple containing the resulting user message, whether the user agent
terminated the conversation, and any additional user information.

**Parameters:**

- **assistant_msg**: A `BaseMessage` representing the message from the assistant.

**Returns:**

  Tuple[ChatAgentResponse, ChatAgentResponse]: A tuple containing two
ChatAgentResponse: the first struct contains the resulting
assistant message, whether the assistant agent terminated the
conversation, and any additional assistant information; the
second struct contains the resulting user message, whether the
user agent terminated the conversation, and any additional user
information.

<a id="camel.societies.role_playing.RolePlaying.clone"></a>

### clone

```python
def clone(self, task_prompt: str, with_memory: bool = False):
```

Creates a new instance of RolePlaying with the same configuration.

**Parameters:**

- **task_prompt** (str): The task prompt to be used by the new instance.
- **with_memory** (bool, optional): Whether to copy the memory (conversation history) to the new instance. If True, the new instance will have the same conversation history. If False, the new instance will have a fresh memory. (default: :obj:`False`)

**Returns:**

  RolePlaying: A new instance of RolePlaying with the same
configuration.

<a id="camel.societies.role_playing.RolePlaying._is_multi_response"></a>

### _is_multi_response

```python
def _is_multi_response(self, agent: ChatAgent):
```

Checks if the given agent supports multi-response.

**Parameters:**

- **agent** (ChatAgent): The agent to check for multi-response support.

**Returns:**

  bool: True if the agent supports multi-response, False otherwise.
