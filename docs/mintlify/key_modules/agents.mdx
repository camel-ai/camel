---
title: "Agents"
description: "Learn about CAMEL's agent types, with a focus on ChatAgent and advanced agent architectures for AI-powered automation."
icon: user-helmet-safety
---


## Concept

Agents in CAMEL are autonomous entities capable of performing specific tasks through interaction with language models and other components. 
Each agent is designed with a particular role and capability, allowing them to work independently or collaboratively to achieve complex goals.

<Note type="info" title="What is an Agent?">
<strong>Think of an agent as an AI-powered teammate</strong> one that brings a defined role, memory, and tool-using abilities to every workflow. CAMEL’s agents are composable, robust, and can be extended with custom logic.
</Note>

## Base Agent Architecture

All CAMEL agents inherit from the <code>BaseAgent</code> abstract class, which defines two essential methods:

| Method      | Purpose             | Description                                  |
|-------------|---------------------|----------------------------------------------|
| <code>reset()</code> | State Management   | Resets the agent to its initial state         |
| <code>step()</code>  | Task Execution     | Performs a single step of the agent's operation |

## Types

### ChatAgent

The `ChatAgent` is the primary implementation that handles conversations with language models. It supports:
- System message configuration for role definition
- Memory management for conversation history
- Tool/function calling capabilities
- Response formatting and structured outputs
- Multiple model backend support with scheduling strategies
- Async operation support

<AccordionGroup>

  <Accordion title="Other Agent Types (When to Use)">
  
  **`CriticAgent`**  
  Specialized agent for evaluating and critiquing responses or solutions. Used in scenarios requiring quality assessment or validation.

  **`DeductiveReasonerAgent`**  
  Focused on logical reasoning and deduction. Breaks down complex problems into smaller, manageable steps.

  **`EmbodiedAgent`**  
  Designed for embodied AI scenarios, capable of understanding and responding to physical world contexts.

  **`KnowledgeGraphAgent`**  
  Specialized in building and utilizing knowledge graphs for enhanced reasoning and information management.

  **`MultiHopGeneratorAgent`**  
  Handles multi-hop reasoning tasks, generating intermediate steps to reach conclusions.

  **`SearchAgent`**  
  Focused on information retrieval and search tasks across various data sources.

  **`TaskAgent`**  
  Handles task decomposition and management, breaking down complex tasks into manageable subtasks.

  </Accordion>

</AccordionGroup>

## Usage

### Basic ChatAgent Usage

```python
from camel.agents import ChatAgent

# Create a chat agent with a system message
agent = ChatAgent(system_message="You are a helpful assistant.")

# Step through a conversation
response = agent.step("Hello, can you help me?")
```

### Simplified Agent Creation

The `ChatAgent` supports multiple ways to specify the model:

```python
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

# Method 1: Using just a string for the model name (default model platform is used)
agent_1 = ChatAgent("You are a helpful assistant.", model="gpt-4o-mini")

# Method 2: Using a ModelType enum (default model platform is used)
agent_2 = ChatAgent("You are a helpful assistant.", model=ModelType.GPT_4O_MINI)

# Method 3: Using a tuple of strings (platform, model)
agent_3 = ChatAgent("You are a helpful assistant.", model=("openai", "gpt-4o-mini"))

# Method 4: Using a tuple of enums
agent_4 = ChatAgent(
    "You are a helpful assistant.",
    model=(ModelPlatformType.ANTHROPIC, ModelType.CLAUDE_3_5_SONNET),
)

# Method 5: Using default model platform and default model type when none is specified
agent_5 = ChatAgent("You are a helpful assistant.")

# Method 6: Using a pre-created model with ModelFactory (original approach)
model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,  # Using enum
    model_type=ModelType.GPT_4O_MINI,         # Using enum
)
agent_6 = ChatAgent("You are a helpful assistant.", model=model)

# Method 7: Using ModelFactory with string parameters
model = ModelFactory.create(
    model_platform="openai",     # Using string
    model_type="gpt-4o-mini",    # Using string
)
agent_7 = ChatAgent("You are a helpful assistant.", model=model)
```

### Using Tools with Chat Agent

```python
from camel.agents import ChatAgent
from camel.toolkits import FunctionTool

# Define a tool
def calculator(a: int, b: int) -> int:
    return a + b

# Create agent with tool
agent = ChatAgent(tools=[calculator])

# The agent can now use the calculator tool in conversations
response = agent.step("What is 5 + 3?")
```

### Structured Output

CAMEL's `ChatAgent` can produce structured output by leveraging Pydantic models. This feature is especially useful when you need the agent to return data in a specific format, such as JSON. By defining a Pydantic model, you can ensure that the agent's output is predictable and easy to parse.

<Tabs>
<Tab title="Simple Object">

Here's how you can get a structured response from a `ChatAgent`. First, define a `BaseModel` that specifies the desired output fields. You can add descriptions to each field to guide the model.

```python
from pydantic import BaseModel, Field
from typing import List

class JokeResponse(BaseModel):
    joke: str = Field(description="A joke")
    funny_level: int = Field(description="Funny level, from 1 to 10")

# Create agent with structured output
agent = ChatAgent(model="gpt-4o-mini")
response = agent.step("Tell me a joke.", response_format=JokeResponse)

# The response content is a JSON string
print(response.msgs[0].content)
# '{"joke": "Why don't scientists trust atoms? Because they make up everything!", "funny_level": 8}'

# Access the parsed Pydantic object
parsed_response = response.msgs[0].parsed
print(parsed_response.joke)
# "Why don't scientists trust atoms? Because they make up everything!"
print(parsed_response.funny_level)
# 8
```
</Tab>
<Tab title="Nested Objects and Lists">

You can also use nested Pydantic models and lists to define more complex structures. In this example, we define a `StudentList` that contains a list of `Student` objects.

```python
from pydantic import BaseModel
from typing import List

class Student(BaseModel):
    name: str
    age: str
    email: str

class StudentList(BaseModel):
    students: List[Student]

# Create agent with structured output
agent = ChatAgent(model="gpt-4o-mini")
response = agent.step(
    "Create a list of two students with their names, ages, and email addresses.",
    response_format=StudentList,
)

# Access the parsed Pydantic object
parsed_response = response.msgs[0].parsed
for student in parsed_response.students:
    print(f"Name: {student.name}, Age: {student.age}, Email: {student.email}")
# Name: Alex, Age: 22, Email: alex@example.com
# Name: Beth, Age: 25, Email: beth@example.com
```
</Tab>
</Tabs>

## Best Practices

<AccordionGroup>

  <Accordion title="Memory Management">
    <ul>
      <li>Use appropriate window sizes to manage conversation history</li>
      <li>Consider token limits when dealing with long conversations</li>
      <li>Utilize the memory system for maintaining context</li>
    </ul>
  </Accordion>

  <Accordion title="Tool Integration">
    <ul>
      <li>Keep tool functions focused and well-documented</li>
      <li>Handle tool errors gracefully</li>
      <li>Use external tools for operations that should be handled by the user</li>
    </ul>
  </Accordion>

  <Accordion title="Response Handling">
    <ul>
      <li>Implement appropriate response terminators for conversation control</li>
      <li>Use structured outputs when specific response formats are needed</li>
      <li>Handle async operations properly when dealing with long-running tasks</li>
    </ul>
  </Accordion>

  <Accordion title="Model Specification">
    <ul>
      <li>Use the simplified model specification methods for cleaner code</li>
      <li>For default platform models, just specify the model name as a string</li>
      <li>For specific platforms, use the tuple format (platform, model)</li>
      <li>Use enums for better type safety and IDE support</li>
    </ul>
  </Accordion>

</AccordionGroup>

## Advanced Features

<Tabs>
  <Tab title="Model Scheduling">
    <Note type="info" title="Custom Model Selection">
      You can dynamically select which model an agent uses for each step by adding your own scheduling strategy.
    </Note>
    <CodeGroup>
      ```python title="Custom Model Scheduling"
      def custom_strategy(models):
          # Custom model selection logic
          return models[0]

      agent.add_model_scheduling_strategy("custom", custom_strategy)
      ```
    </CodeGroup>
  </Tab>
  <Tab title="Output Language Control">
    <Note type="tip" title="Multilingual Output">
      Agents can respond in any language. Set the output language on-the-fly during conversations.
    </Note>
    <CodeGroup>
      ```python title="Set Output Language"
      agent.set_output_language("Spanish")
      ```
    </CodeGroup>
  </Tab>
</Tabs>
