# Mailbox-Based Multi-Agent System

A mailbox-based multi-agent system implementation for the CAMEL framework, enabling agents to communicate through message passing without directly accessing each other's state.

## Overview

The mailbox-based multi-agent system provides a clean, decoupled architecture where agents communicate exclusively through message passing. Each agent has:

- **A mailbox** (message queue) for receiving messages
- **An internal state** (managed by ChatAgent)
- **A behavior loop**: receive → process → send messages

This design ensures that agents never directly touch each other's state, promoting modularity and scalability.

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

Manages a society of agents with mailbox-based communication.

```python
from camel.societies import MailboxSociety

society = MailboxSociety(name="Research Team")

# Register agents
society.register_agent(agent, agent_card)

# Search for agents
results = society.search_agents(capabilities=["research"])

# Broadcast messages
society.broadcast_message("agent1", "Team meeting at 3 PM")
```

### 4. MailboxToolkit

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

### 5. AgentDiscoveryToolkit

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

## Testing

Comprehensive tests are available in `test/societies/test_mailbox_society.py`:

```bash
pytest test/societies/test_mailbox_society.py
```

## Examples

See `examples/ai_society/mailbox_society_example.py` for a complete demonstration.

## API Reference

For detailed API documentation, refer to the docstrings in:
- `camel/societies/mailbox_society.py`
- `camel/toolkits/mailbox_toolkit.py`
- `camel/toolkits/agent_discovery_toolkit.py`
