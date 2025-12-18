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

## TriggerManager

The `TriggerManager` connects triggers to your agents or workflows.

### Basic Usage with ChatAgent

Create a trigger manager that connects a trigger to a ChatAgent. The agent will automatically process events with the provided prompt:

```python
from camel.triggers import TriggerManager, ScheduleTrigger
from camel.triggers.trigger_manager import CallbackHandlerType
from camel.agents import ChatAgent

# Create agent and manager
agent = ChatAgent(system_message="You are a helpful assistant.")
manager = TriggerManager(
    handler_type=CallbackHandlerType.CHATAGENT,
    chat_agent=agent,
    default_prompt="Process this event: {event_payload}"
)

# Create and register trigger
trigger = ScheduleTrigger.create_daily_trigger(
    trigger_id="daily-task",
    name="Daily Task",
    description="Run daily",
    hour=9,
    minute=0
)

await manager.register_trigger(trigger, auto_activate=True)
```

### Using with Workforce

Integrate triggers with a Workforce to distribute event processing across multiple agents in your multi-agent system:

```python
from camel.triggers.trigger_manager import CallbackHandlerType
from camel.societies.workforce import Workforce
from camel.tasks import Task

workforce = Workforce("Task Processor")

manager = TriggerManager(
    handler_type=CallbackHandlerType.WORKFORCE,
    workforce=workforce,
    default_task=Task(content="Process: {event_payload}", id="1")
)

await manager.register_trigger(trigger, auto_activate=True)
```

### Custom Callbacks

Handle trigger events with custom callback functions. This gives you full control over how to process events:

```python
from camel.triggers.base_trigger import TriggerEvent

async def handle_event(event: TriggerEvent):
    print(f"Event from {event.trigger_id}: {event.payload}")

manager = TriggerManager()
trigger.add_callback(handle_event)
await manager.register_trigger(trigger, auto_activate=True)
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

**Scheduled Reports**

Automatically generate reports on a schedule. This example creates a daily report trigger at 5 PM:

```python
trigger = ScheduleTrigger.create_daily_trigger(
    trigger_id="daily-report",
    name="Daily Report",
    description="Generate report at 5 PM",
    hour=17,
    minute=0
)

manager = TriggerManager(
    handler_type=CallbackHandlerType.CHATAGENT,
    chat_agent=agent,
    default_prompt="Generate today's summary report."
)
await manager.register_trigger(trigger, auto_activate=True)
```

**Webhook Processing**

Process incoming webhook events through a Workforce to handle multiple API events efficiently:

```python
webhook = WebhookTrigger(
    trigger_id="api-events",
    name="API Events",
    description="Process API webhooks",
    port=8080,
    path="/webhook"
)

manager = TriggerManager(
    handler_type=CallbackHandlerType.WORKFORCE,
    workforce=workforce
)
await manager.register_trigger(webhook, auto_activate=True)
```
