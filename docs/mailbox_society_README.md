# Mailbox-Based Multi-Agent System

A mailbox-based multi-agent system implementation for the CAMEL framework, enabling agents to communicate through message passing without directly accessing each other's state.

## Overview

The mailbox-based multi-agent system provides a clean, decoupled architecture where agents communicate exclusively through message passing. Each agent has:

- **A mailbox** (message queue) for receiving messages
- **An internal state** (managed by ChatAgent)
- **A behavior loop**: receive → process → send messages

This design ensures that agents never directly touch each other's state, promoting modularity and scalability.

## Key Features

- **Message Passing**: Direct and broadcast messaging between agents
- **Entry Points**: Both synchronous (`run()`) and asynchronous (`run_async()`) entry points for processing
- **Lifecycle Control**: Start, stop, pause, and resume message processing
- **Custom Handlers**: Set custom message handlers per agent
- **Discovery**: Search and discover agents by capability, tag, or description

## Key Components

### 1. MailboxMessage

Represents a message in the system.

```python
from camel.societies import MailboxMessage

message = MailboxMessage(
    sender_id="agent1",
    recipient_id="agent2",
    content="Hello, Agent 2!",
    subject="Greeting"
)
```

### 2. AgentCard

Describes an agent's identity and capabilities.

```python
from camel.societies import AgentCard

card = AgentCard(
    agent_id="researcher",
    description="Specializes in finding and analyzing information",
    capabilities=["research", "data_analysis", "literature_review"],
    tags=["research", "analysis"]
)
```

### 3. MailboxSociety

Manages a society of agents with mailbox-based communication and automatic message processing.

```python
from camel.societies import MailboxSociety

# Create society with configuration
society = MailboxSociety(
    name="Research Team",
    max_iterations=None,    # None = infinite (default)
    process_interval=0.1    # Check every 0.1 seconds (default)
)

# Register agents
society.register_agent(agent, agent_card)

# Search for agents
results = society.search_agents(capabilities=["research"])

# Broadcast messages
society.broadcast_message("agent1", "Team meeting at 3 PM")

# Use entry point to process messages automatically
society.run()  # Synchronous processing

# Or use async
await society.run_async()  # Asynchronous processing
```

**Default Behavior:**
- `max_iterations=None`: Runs indefinitely until stopped (infinite loop)
- `process_interval=0.1`: Checks for messages every 0.1 seconds

### 4. Entry Points for Message Processing

The MailboxSociety provides entry points similar to Workforce for automatic message processing:

```python
# Synchronous entry point
society.run()

# Asynchronous entry point
await society.run_async()

# Lifecycle controls
society.stop()    # Stop processing
society.pause()   # Pause processing
society.resume()  # Resume processing
society.reset()   # Reset state
```

#### Initial Messages

Both `run()` and `run_async()` support sending initial messages to kick off coordination:

```python
# Send initial task messages to specific agents
initial_messages = {
    "project_manager": "Start the research project on AI safety",
    "researcher": "Check your mailbox for assignments",
}

# Synchronous
society.run(initial_messages=initial_messages)

# Asynchronous
await society.run_async(initial_messages=initial_messages)
```

Messages can be:
- **String**: Automatically converted to MailboxMessage with sender "system"
- **MailboxMessage**: Full control over sender, subject, etc.

This enables starting autonomous workflows with a single command!

#### Custom Message Handlers

Set custom handlers to control how agents process messages. **If no handler is specified, the default handler automatically uses `ChatAgent.step()` to process messages.**

```python
def custom_handler(agent: ChatAgent, message: MailboxMessage):
    """Custom logic for processing messages."""
    print(f"Processing: {message.content}")
    # Your custom logic here
    
society.set_message_handler("agent1", custom_handler)
```

**Default Handler Behavior:**
When no custom handler is set for an agent, the society uses a default handler that:
1. Creates a user message containing the mailbox message details (sender, subject, content)
2. Calls `agent.step()` with this user message
3. The agent processes the message using its LLM and system prompt

This means agents can process messages automatically without requiring custom handler code.

### 5. MailboxToolkit

Provides agents with mailbox functionality.

```python
from camel.toolkits import MailboxToolkit

mailbox = MailboxToolkit("agent1", message_router)

# Send messages
mailbox.send_message("agent2", "Hello!", subject="Greeting")

# Receive messages
messages = mailbox.receive_messages(max_messages=5)

# Check mailbox
status = mailbox.check_messages()

# Peek at messages without removing them
preview = mailbox.peek_messages(max_messages=3)
```

### 6. AgentDiscoveryToolkit

Enables agents to discover other agents in the society.

```python
from camel.toolkits import AgentDiscoveryToolkit

discovery = AgentDiscoveryToolkit("agent1", agent_registry)

# List all agents
all_agents = discovery.list_all_agents()

# Search by capability
writers = discovery.search_agents_by_capability("writing")

# Search by tag
helpers = discovery.search_agents_by_tag("assistant")

# Get agent details
details = discovery.get_agent_details("agent2")
```

## Quick Start

### Basic Setup

```python
from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.societies import AgentCard, MailboxSociety
from camel.toolkits import AgentDiscoveryToolkit, MailboxToolkit
from camel.types import ModelPlatformType, ModelType

# Create society
society = MailboxSociety(name="My Society")

# Create agent card
card = AgentCard(
    agent_id="assistant",
    description="A helpful assistant",
    capabilities=["chat", "help"],
    tags=["assistant"]
)

# Create model
model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)

# Create agent with toolkits
mailbox = MailboxToolkit("assistant", society.message_router)
discovery = AgentDiscoveryToolkit("assistant", society.agent_cards)

agent = ChatAgent(
    system_message=BaseMessage.make_assistant_message(
        role_name="Assistant",
        content="You are a helpful assistant."
    ),
    model=model,
    tools=[*mailbox.get_tools(), *discovery.get_tools()]
)

# Register agent
society.register_agent(agent, card)
```

### Using the Entry Point

Process messages automatically using the entry point:

```python
# Option 1: Manual message handling with toolkits
# Agents use their mailbox tools to send/receive messages

# Option 2: Automatic processing with entry point (infinite by default)
society = MailboxSociety(
    name="Auto Processing Society",
    max_iterations=None,  # None = infinite (default)
    process_interval=0.1   # Check every 0.1 seconds (default)
)

# Register agents...
# Add initial messages...

# Start automatic processing (runs until stopped)
society.run()

# Or with limited iterations
society = MailboxSociety(name="Limited", max_iterations=10)
society.run()  # Will stop after 10 iterations

# Or with custom handlers
def my_handler(agent, message):
    print(f"Processing: {message.content}")
    # Custom logic here
    
society.set_message_handler("agent1", my_handler)
society.run()
```

## Autonomous Agent Coordination

The most powerful use of MailboxSociety is enabling ChatAgents to autonomously coordinate using the toolkits:

```python
from camel.societies import MailboxSociety, AgentCard
from camel.toolkits import MailboxToolkit, AgentDiscoveryToolkit
from camel.agents import ChatAgent

# Create society
society = MailboxSociety(name="Research Team")

# Create agent with both toolkits
mailbox = MailboxToolkit("researcher", society.message_router)
discovery = AgentDiscoveryToolkit("researcher", society.agent_cards)

agent = ChatAgent(
    system_message=BaseMessage.make_assistant_message(
        role_name="Researcher",
        content=(
            "You are a researcher. Use discovery tools to find collaborators "
            "and mailbox tools to coordinate with them."
        )
    ),
    model=model,
    tools=[*mailbox.get_tools(), *discovery.get_tools()]
)

# Agent autonomously uses tools through natural language
user_msg = BaseMessage.make_user_message(
    role_name="User",
    content="Find a writer on the team and send them your research findings."
)
response = agent.step(user_msg)
# Agent will:
# 1. Use discovery tools to find writer
# 2. Use mailbox tools to send message
# 3. All done autonomously through LLM tool calling!
```

For a complete example, see `examples/ai_society/mailbox_society_coordination_example.py` which demonstrates a full multi-agent workflow where agents discover each other and coordinate autonomously.

### Quick Start with Async and Initial Messages

The recommended way to start a coordination workflow is using `run_async()` with initial messages:

```python
import asyncio
from camel.societies import MailboxSociety

# Create society and register agents with toolkits
society = MailboxSociety(name="Team", max_iterations=15)
# ... register agents with MailboxToolkit and AgentDiscoveryToolkit ...

# Send initial task and let agents coordinate autonomously
async def main():
    await society.run_async(
        initial_messages={
            "project_manager": (
                "Start a research project on AI safety. "
                "Discover team members and assign tasks."
            ),
        }
    )

asyncio.run(main())
```

This single command triggers complete autonomous coordination! See `examples/ai_society/mailbox_coordination_async_example.py` for a full working example.

## Features

### Message Passing

- **Direct messaging**: Send messages to specific agents
- **Broadcast**: Send messages to all agents in the society
- **Peek functionality**: Preview messages without removing them
- **Message metadata**: Include subjects and timestamps

### Agent Discovery

- **Search by capability**: Find agents with specific skills
- **Search by tag**: Find agents by category
- **Search by description**: Text-based search of agent descriptions
- **List all agents**: Get overview of all available agents

### Society Management

- **Agent registration**: Add agents to the society
- **Agent unregistration**: Remove agents from the society
- **Mailbox management**: Clear mailboxes, check message counts
- **Agent lookup**: Retrieve agents and their cards by ID

## Example Use Cases

### 1. Collaborative Research Team

```python
# Create researchers, writers, and reviewers
# Each agent discovers others and collaborates through messages
# Workflow: Research → Write → Review → Publish
```

### 2. Customer Service System

```python
# Create specialized agents for different departments
# Route customer queries to appropriate agents
# Agents escalate or forward messages as needed
```

### 3. Workflow Orchestration

```python
# Create agents for different stages of a pipeline
# Each agent processes messages and forwards to next stage
# Broadcast notifications when tasks complete
```

## Architecture Benefits

### Decoupling
Agents are independent units that communicate only through messages, making the system modular and maintainable.

### Scalability
New agents can be added without modifying existing ones. The message-passing architecture supports dynamic agent networks.

### Flexibility
Agents can be composed with different capabilities and toolkits, enabling diverse multi-agent scenarios.

### Observability
All communication goes through the mailbox system, making it easy to monitor, log, and debug agent interactions.

## Comparison with Workforce

MailboxSociety shares similarities with Workforce but is designed for different use cases:

| Feature | MailboxSociety | Workforce |
|---------|----------------|-----------|
| **Communication** | Message passing via mailboxes | Task-based via TaskChannel |
| **Entry Point** | `run()` / `run_async()` | `process_task()` / `process_task_async()` |
| **Main Loop** | `_process_messages_loop()` | `_listen_to_channel()` |
| **Lifecycle** | start/stop/pause/resume/reset | start/stop/pause/resume/reset |
| **Processing** | Iterative message processing | Task decomposition & assignment |
| **Coordination** | Peer-to-peer messaging | Coordinator-worker hierarchy |
| **Use Case** | Collaborative multi-agent systems | Hierarchical task execution |

**When to use MailboxSociety:**
- Agents need to communicate freely with each other
- Peer-to-peer collaboration workflows
- Event-driven agent interactions
- Discovery and dynamic messaging patterns

**When to use Workforce:**
- Task decomposition and hierarchical execution
- Coordinator-worker patterns
- Dependency-based task management
- Failure recovery and task retry strategies

## Testing

Comprehensive tests are available in `test/societies/test_mailbox_society.py`:

```bash
pytest test/societies/test_mailbox_society.py
```

## Examples

See the following examples:
- `examples/ai_society/mailbox_society_example.py` - Basic message passing demonstration (manual toolkit invocation)
- `examples/ai_society/mailbox_society_processing_example.py` - Entry point and automatic processing demonstration
- `examples/ai_society/default_handler_example.py` - Default handler behavior demonstration
- `examples/ai_society/mailbox_society_coordination_example.py` - Full autonomous agent coordination example (manual step-by-step)
- `examples/ai_society/mailbox_coordination_async_example.py` - **Autonomous coordination using run_async with initial_messages** (recommended)

## API Reference

For detailed API documentation, refer to the docstrings in:
- `camel/societies/mailbox_society.py`
- `camel/toolkits/mailbox_toolkit.py`
- `camel/toolkits/agent_discovery_toolkit.py`
