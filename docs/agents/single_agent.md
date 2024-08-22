# Creating Your First Agent

## Philosophical Bits
[![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1hG_q9F8PY1kDua_JyoHirJAPOGRexFmM?usp=sharing)


The `ChatAgent()` class is a cornerstone of CAMEL. We design our agent with the spirit to answer the following question:

> Can we design an autonomous communicative agent capable of steering the conversation toward task completion with minimal human supervision?

In our current implementation, we consider agents with the following key features:
- **Role**: along with the goal and content specification, this sets the initial state of an agent, guiding the agent to take actions during the sequential interaction.
- **Memory**: in-context memory and external memory which allows the agent to infer and learn in a more grounded approach.
- **Tools**: a set of functions that our agents can utilize to interact with the external world; essentially this gives embodiments to our agents.
- **Communication**: our framework allows flexible and scalable communication between agents. This is fundamental for the critical research question.
- **Reasoning**: we will equip agents with different planning and reward (critic) learning abilities, allowing them to optimize task completion in a more guided approach.



<!-- - (WIP) **Reasoning Ability**: since any goal can be formalized as the outcome of maximizing cumulative rewards, we will equip our agents with policy which they could follow to achieve goals. -->

<!-- We will first start with the single agent setting, where the agent can interact with users, process and store messages, and utilize external tools to generate responses and accomplish tasks. -->

## Quick Start
Let's first play with a `ChatAgent` instance by simply initialize it with a system message and interact with user messages.

### Step 0: Prepartions
```python
from camel.messages import BaseMessage as bm
from camel.agents import ChatAgent
```

### Step 1: Define the Role
Create a system message to define agent's default role and behaviors.
```python
sys_msg = bm.make_assistant_message(
    role_name='stone',
    content='you are a curious stone wondering about the universe.')
```

### Step 2: Initialize the Agent
```python
agent = ChatAgent(
    system_message=sys_msg,
    message_window_size=10,    # [Optional] the length for chat memory
    )
```
### Step 3: Interact with the Agent with `.step()`
```python
# Define a user message
usr_msg = bm.make_user_message(
    role_name='prof. claude shannon',
    content='what is information in your mind?')

# Sending the message to the agent
response = agent.step(usr_msg)

# Check the response (just for illustrative purpose)
print(response.msgs[0].content)
>>> information is the resolution of uncertainty.
```
Woohoo, your first agent is ready to play with you!


## Advanced Features

### Tool Usage
```python
# Import the necessary functions
from camel.toolkits import MATH_FUNCS, SEARCH_FUNCS

# Initialize the agent with list of tools
agent = ChatAgent(
    system_message=sys_msg,        
    tools=[*MATH_FUNCS, *SEARCH_FUNCS]
    )

# Check if tools are enabled
agent.is_tools_added()
>>> True
```

### Memory
By default our agent is initialized with `ChatHistoryMemory`, allowing agents to do in-context learning, though restricted by the finite window length.

Assume that you have followed the setup in [Quick Start](#quick-start). Let's first check what is inside its brain.
<!-- ```python
agent.memory.get_context()
>>> ([{'role': 'system', 'content': 'you are a helpful assistant.'},
      {'role': 'user', 'content': 'what is information in your mind?'}],
      30)
``` -->
```python
# Check the current memory
agent.memory.get_context()
>>> ([{'role': 'system', 'content': 'you are a helpful assistant.'},
      {'role': 'user', 'content': 'what is information in your mind?'}],
      {'role': 'assistant', 'content': 'information is the resolution of uncertainty.'}
      44)
```
You can connect the agent with external database (as long-term memory) in which they can access and retrieve at each step. We will soon update instructions on this part.

### Miscs
- Setting the agent to its initial state.
    ```python
    agent.reset()
    ```
- Set the output language for the agent.
    ```python
    agent.set_output_language('french')
    ```
- Using open-source models.
    ```python
    # Please refer to our setup chapter for details on backend settings.
    ...

    # Import the necessary classes

    from camel.configs import ChatGPTConfig, OpenSourceConfig
    from camel.types import ModelType, ModelPlatformType
    from camel.models import ModelFactory

    # Set the LLM model type and model config
    model_platform = ModelPlatformType.OPEN_SOURCE
    model_type = ModelType.LLAMA_2
    model_config=OpenSourceConfig(
        model_path='meta-llama/Llama-2-7b-chat-hf',  # a local folder or HuggingFace repo Name
        server_url='http://localhost:8000/v1')      # The url with the set port number

    # Create the backend model
    model = ModelFactory.create(
        model_platform=model_platform,
        model_type=model_type,
        model_config=model_config)

    # Set the agent
    agent = ChatAgent(sys_msg, model=model)
    ```

- The `ChatAgent` class offers several useful initialization options, including `model`, `memory`, `message_window_size`, `token_limit`, `output_language`, `tools`, and `response_terminators`. Check [`chat_agent.py`](https://github.com/camel-ai/camel/blob/master/camel/agents/chat_agent.py) for detailed usage guidance.


## Remarks
Awesome. Now you have made your first step in creating a single agent. In the next chapter, we will explore the creation of different types agents along with the role playing features. Stay tuned.
