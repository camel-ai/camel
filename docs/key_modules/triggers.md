---
title: "Triggers"
icon: bolt-lightning
---

<Card title="What are Triggers?" icon="bolt">
  Triggers automatically activate agents or workflows in response to events like webhooks, or schedules changes.
</Card>

## Concept

Triggers make your AI agents reactive to real-world events. Instead of manually invoking agents, triggers listen for specific conditions and automatically activate the appropriate agent or workflow.

**Use triggers when you need agents to:**

- Respond to external API events (webhooks)
- Execute tasks on a recurring schedule

## Trigger Types

### ScheduleTrigger

Execute tasks on a recurring schedule using cron expressions. You can create triggers with custom cron expressions or use convenient factory methods:

```python
from camel.triggers import ScheduleTrigger

# Daily at 9 AM
trigger = ScheduleTrigger(
    trigger_id="daily-report",
    name="Daily Report",
    description="Generate daily report at 9 AM", # Relevant toolkit might be necesary
    cron_expression="0 9 * * *",
)

# Or use factory methods
trigger = ScheduleTrigger.create_daily_trigger(
    trigger_id="morning-task",
    name="Morning Task",
    description="Run every morning",
    hour=9,
    minute=0
)
```

**Factory methods:** `create_interval_trigger()`, `create_daily_trigger()`, `create_weekly_trigger()`

### WebhookTrigger

Receive external HTTP events through a webhook endpoint. Configure the host, port, and path where your webhook will listen for incoming requests:

```python
from camel.triggers import WebhookTrigger

trigger = WebhookTrigger(
    trigger_id="github-webhook",
    name="GitHub Events",
    description="Handle GitHub notifications",
    port=8080,
    path="/webhook",
    host="0.0.0.0"
)
```

## Handlers

Handlers define how trigger events are processed. They convert events into actions by processing them through agents, workflows, or custom logic. For simpler use cases you can use `trigger.add_callback()` instead.

### Handler Types

**ChatAgentHandler**: Process events through a single ChatAgent for immediate responses:
```python
from camel.triggers.handlers import ChatAgentHandler
from camel.agents import ChatAgent

agent = ChatAgent(system_message="You are a helpful assistant.")
handler = ChatAgentHandler(
    chat_agent=agent,
    default_prompt="Process this trigger event: {event_payload}"
)
```

**WorkforceHandler**: Distribute events to multi-agent teams for collaborative processing:
```python
from camel.triggers.handlers import WorkforceHandler
from camel.societies.workforce import Workforce
from camel.tasks import Task

workforce = Workforce("Event Processor")
handler = WorkforceHandler(
    workforce=workforce,
    default_task=Task(content="Process event", id="1"),
    stop_after_task=True
)
```

**CallbackHandler**: Use simple functions for lightweight processing:
```python
from camel.triggers.handlers import CallbackHandler
from camel.triggers.base_trigger import TriggerEvent

async def process_event(event: TriggerEvent) -> dict:
    print(f"Processing {event.trigger_id}")
    return {"status": "processed"}

handler = CallbackHandler(callback=process_event)
```

**CompositeHandler**: Chain multiple handlers for complex pipelines:
```python
from camel.triggers.handlers import CompositeHandler, ChatAgentHandler, CallbackHandler

async def log_event(event: TriggerEvent) -> dict:
    print(f"Event: {event.trigger_id}")
    return {"logged": True}

handler = CompositeHandler(handlers=[
    CallbackHandler(callback=log_event),
    ChatAgentHandler(chat_agent=agent)
])
```

### Custom Handlers

Create custom handlers by extending `TriggerEventHandler`:
```python
from camel.triggers.handlers import TriggerEventHandler
from camel.triggers.base_trigger import TriggerEvent

class EmailHandler(TriggerEventHandler):
    def __init__(self, smtp_server: str):
        self.smtp_server = smtp_server
    
    async def handle(self, event: TriggerEvent) -> dict:
        # Send email notification
        await send_email(
            to="admin@example.com",
            subject=f"Trigger {event.trigger_id} activated",
            body=str(event.payload)
        )
        return {"email_sent": True}
```

## TriggerManager

The `TriggerManager` coordinates trigger registration and event processing through handlers.

### Basic Setup

Create a manager with a call back to process trigger events:

```python
from camel.triggers import TriggerManager, ScheduleTrigger

async def handle_callback(event: TriggerEvent):
    """Process incoming event data."""
    logger.info(f"Received event: {event.payload}")

# Create manager with handler
manager = TriggerManager()

# Register and activate trigger
trigger = ScheduleTrigger.create_daily_trigger(
    trigger_id="daily-task",
    name="Daily Task",
    description="Run daily at 9 AM",
    hour=9,
    minute=0
)

# Add simple call backs for raw event processing
trigger.add_callback(handle_callback)

await manager.register_trigger(trigger, auto_activate=True)
```

### Using ChatAgentHandler

Process trigger events through a ChatAgent for single-agent responses:

```python
from camel.triggers.handlers import ChatAgentHandler

handler = ChatAgentHandler(
    chat_agent=agent,
    default_prompt="Analyze this trigger event and provide insights."
)

manager = TriggerManager(handler=handler)
await manager.register_trigger(trigger, auto_activate=True)
```

### Using WorkforceHandler

Distribute event processing across multiple agents in a Workforce:

```python
from camel.triggers.handlers import WorkforceHandler
from camel.societies.workforce import Workforce
from camel.tasks import Task

workforce = Workforce("Event Processor")
handler = WorkforceHandler(
    workforce=workforce,
    default_task=Task(content="Process trigger event", id="1")
)

manager = TriggerManager(handler=handler)
await manager.register_trigger(trigger, auto_activate=True)
```

### Custom Event Processing

Use custom prompt or task factories for advanced event processing:

```python
from camel.triggers.base_trigger import TriggerEvent

# Custom prompt factory for ChatAgentHandler
def create_prompt(event: TriggerEvent) -> str:
    return f"Urgent: Process event from {event.trigger_id}\nData: {event.payload}"

handler = ChatAgentHandler(
    prompt_factory=create_prompt
)

# Custom task factory for WorkforceHandler
def create_task(event: TriggerEvent) -> Task:
    return Task(
        content=f"High priority: {event.payload}",
        id=f"trigger_{event.trigger_id}",
        additional_info={"trigger_type": event.trigger_type.value}
    )

workforce_handler = WorkforceHandler(
    workforce=workforce,
    task_factory=create_task
)
```

## Creating Custom Triggers

Extend `BaseTrigger` to create custom trigger types. This example shows how to build an email trigger that monitors an inbox:

```python
from camel.triggers.base_trigger import BaseTrigger, TriggerEvent, TriggerType
from datetime import datetime

class EmailTrigger(BaseTrigger):
    """Monitor email inbox for new messages"""

    async def initialize(self) -> bool:
        # Setup email connection
        return True

    async def activate(self) -> bool:
        self.state = TriggerState.ACTIVE
        # Start monitoring
        return True

    async def deactivate(self) -> bool:
        self.state = TriggerState.INACTIVE
        return True

    async def test_connection(self) -> bool:
        # Test email server
        return True

    def validate_config(self, config):
        required = ["server", "port", "username"]
        return all(key in config for key in required)

    async def process_trigger_event(self, email_data):
        return TriggerEvent(
            trigger_id=self.trigger_id,
            trigger_type=TriggerType.CUSTOM,
            timestamp=datetime.now(),
            payload={"from": email_data["from"], "subject": email_data["subject"]}
        )
```

## Common Patterns

### Scheduled Reports with ChatAgent

Automatically generate reports on a schedule using a ChatAgent:

```python
from camel.triggers import TriggerManager, ScheduleTrigger
from camel.triggers.handlers import ChatAgentHandler
from camel.agents import ChatAgent

# Setup agent and handler
agent = ChatAgent(system_message="You are a report generator.")
handler = ChatAgentHandler(
    chat_agent=agent,
    default_prompt="Generate today's summary report with key metrics."
)

# Create scheduled trigger
trigger = ScheduleTrigger.create_daily_trigger(
    trigger_id="daily-report",
    name="Daily Report",
    description="Generate report at 5 PM",
    hour=17,
    minute=0
)

# Setup manager and register trigger
manager = TriggerManager(handler=handler)
await manager.register_trigger(trigger, auto_activate=True)
```

### Webhook Processing with Workforce

Process incoming webhook events through a multi-agent Workforce:

```python
from camel.triggers import WebhookTrigger
from camel.triggers.handlers import WorkforceHandler
from camel.societies.workforce import Workforce

# Setup workforce and handler
workforce = Workforce("API Event Processor")
handler = WorkforceHandler(workforce=workforce)

# Create webhook trigger
webhook = WebhookTrigger(
    trigger_id="api-events",
    name="API Events",
    description="Process API webhooks",
    port=8080,
    path="/webhook"
)

# Setup manager and register trigger
manager = TriggerManager(handler=handler)
await manager.register_trigger(webhook, auto_activate=True)
```

### Multi-Stage Processing Pipeline

Chain multiple handlers for complex event processing:

```python
from camel.triggers.handlers import CompositeHandler, CallbackHandler, ChatAgentHandler

# Define logging callback
async def log_event(event: TriggerEvent) -> dict:
    print(f"Received event: {event.trigger_id}")
    return {"logged": True}

# Create composite handler
handler = CompositeHandler(handlers=[
    CallbackHandler(callback=log_event),
    ChatAgentHandler(chat_agent=agent)
])

manager = TriggerManager(handler=handler)
await manager.register_trigger(trigger, auto_activate=True)
```

### Custom Event Processing

Use custom factories to transform events before processing:

```python
from camel.triggers.handlers import ChatAgentHandler
from camel.triggers.base_trigger import TriggerEvent

def custom_prompt_factory(event: TriggerEvent) -> str:
    payload = event.payload
    priority = payload.get("priority", "normal")
    return f"[{priority.upper()}] Process: {payload.get('message', '')}"

handler = ChatAgentHandler(
    chat_agent=agent,
    prompt_factory=custom_prompt_factory
)

manager = TriggerManager(handler=handler)
```
