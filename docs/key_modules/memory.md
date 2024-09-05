# Memory

## Overview

The Memory module in CAMEL provides a flexible and powerful system for storing, retrieving, and managing information for AI agents. It enables agents to maintain context across conversations and retrieve relevant information from past interactions, enhancing the coherence and relevance of AI responses.

## Getting Started

### Installation

Ensure you have CAMEL AI installed in your Python environment:

```bash
pip install camel-ai
```

### Basic Usage

Here's a quick example of how to use the `LongtermAgentMemory`:

```python
from camel.memories import (
    ChatHistoryBlock,
    LongtermAgentMemory,
    MemoryRecord,
    ScoreBasedContextCreator,
    VectorDBBlock,
)
from camel.messages import BaseMessage
from camel.types import ModelType, OpenAIBackendRole, RoleType
from camel.utils import OpenAITokenCounter

# Initialize memory
memory = LongtermAgentMemory(
    context_creator=ScoreBasedContextCreator(
        OpenAITokenCounter(ModelType.GPT_4O_MINI), 1024
    ),
    chat_history_block=ChatHistoryBlock(),
    vector_db_block=VectorDBBlock(),
)

# Write records to memory
records = [
    MemoryRecord(
        message=BaseMessage(
            role_name="User",
            role_type=RoleType.USER,
            meta_dict=None,
            content="What is AI?",
        ),
        role_at_backend=OpenAIBackendRole.USER,
    ),
    MemoryRecord(
        message=BaseMessage(
            role_name="Assistant",
            role_type=RoleType.ASSISTANT,
            meta_dict=None,
            content="AI refers to systems that mimic human intelligence.",
        ),
        role_at_backend=OpenAIBackendRole.ASSISTANT,
    ),
]
memory.write_records(records)

# Retrieve context
context, token_count = memory.get_context()
print(f"Retrieved context (token count: {token_count}):")
for message in context:
    print(f"{message}")

```

```markdown
>>> Retrieved context (token count: 27):
{'role': 'user', 'content': 'What is AI?'}
{'role': 'assistant', 'content': 'AI refers to systems that mimic human intelligence.'}
```

## Core Components

### MemoryRecord

The basic data unit in the `CAMEL` memory system.

Attributes:

- `message`: The main content of the record (`BaseMessage`)
- `role_at_backend`: The role this message played at the OpenAI backend (`OpenAIBackendRole`)
- `uuid`: A unique identifier for the record
- `extra_info`: Additional key-value pairs for extra information

Methods:

- `from_dict()`: Static method to construct a `MemoryRecord` from a dictionary
- `to_dict()`: Convert the `MemoryRecord` to a dictionary for serialization
- `to_openai_message()`: Convert the record to an `OpenAIMessage` object

### ContextRecord

The result of memory retrieval from `AgentMemory`, which is used by `ContextCreator` to select records for creating the context for the agent.

Attributes:

- `memory_record`: A `MemoryRecord`
- `score`: A float value representing the relevance or importance of the record

### MemoryBlock (Abstract Base Class)

Serves as the fundamental component within the agent memory system. `MemoryBlock` class follows the "Composite Design pattern" so that you can compose objects into tree structures and then work with these structures as if they were individual objects.

- `write_records()`: Write multiple records to memory
- `write_record()`: Write a single record to memory
- `clear()`: Remove all records from memory

### BaseContextCreator (Abstract Base Class)

Defines the context creation strategies when retrieval messages exceed the model's context length.

- `token_counter`: For counting tokens in a message
- `token_limit`: The maximum number of tokens allowed in the generated context
- `create_context()`: Create conversational context from chat history

### AgentMemory (Abstract Base Class)

A specialized form of MemoryBlock designed for direct integration with an agent.

- `retrieve()`: Get a list of `ContextRecords` from memory
- `get_context_creator()`: Get a context creator
- `get_context()`: Get chat context with a proper size for the agent

## Memory Block Implementations

### ChatHistoryBlock

Maintains a record of chat histories.

Initialization:

- `storage`: Optional `BaseKeyValueStorage` (default: `InMemoryKeyValueStorage`)
- `keep_rate`: Float value for scoring historical messages (default: `0.9`)

Methods:

- `retrieve()`: Get recent chat history with optional window size
- `write_records()`: Write new records to chat history
- `clear()`: Remove all chat messages

Use Case: Ideal for maintaining recent conversation context and flow.

### VectorDBBlock

Uses vector embeddings for maintaining and retrieving information.

Initialization:

- `storage`: Optional BaseVectorStorage (default: `QdrantStorage`)
- `embedding`: Optional BaseEmbedding (default: `OpenAIEmbedding`)

Methods:

- `retrieve()`: Get similar records based on a keyword
- `write_records()`: Convert and write new records to the vector database
- `clear()`: Remove all records from the vector database

Use Case: Better for retrieving semantically relevant information across a large set of messages.

Key Differences:

1. Storage Mechanism: `ChatHistoryBlock` uses key-value storage, `VectorDBBlock` uses vector database storage.
2. Retrieval Method: `ChatHistoryBlock` retrieves based on recency, `VectorDBBlock` retrieves based on semantic similarity.
3. Data Representation: `ChatHistoryBlock` stores messages in original form, `VectorDBBlock` converts to vector embeddings.

## Agent Memory Implementations

### ChatHistoryMemory

An AgentMemory implementation that wraps ChatHistoryBlock.

Initialization:

- `context_creator`: `BaseContextCreator`
- `storage`: Optional `BaseKeyValueStorage`
- `window_size`: Optional int for retrieval window

Methods:

- `retrieve()`: Get recent chat messages
- `write_records()`: Write new records to chat history
- `get_context_creator()`: Get the context creator
- `clear()`: Remove all chat messages

### VectorDBMemory

An `AgentMemory` implementation that wraps `VectorDBBlock`.

Initialization:

- `context_creator`: `BaseContextCreator`
- `storage`: Optional `BaseVectorStorage`
- `retrieve_limit`: int for maximum number of retrieved messages (default:`3`)

Methods:

- `retrieve()`: Get relevant messages from the vector database
- `write_records()`: Write new records and update current topic
- `get_context_creator()`: Get the context creator

### LongtermAgentMemory

Combines ChatHistoryMemory and VectorDBMemory for comprehensive memory management.

Initialization:

- `context_creator`: `BaseContextCreator`
- `chat_history_block`: Optional `ChatHistoryBlock`
- `vector_db_block`: Optional `VectorDBBlock`
- `retrieve_limit`: int for maximum number of retrieved messages (default: `3`)

Methods:

- `retrieve()`: Get context from both chat history and vector database
- `write_records()`: Write new records to both chat history and vector database
- `get_context_creator()`: Get the context creator
- `clear()`: Remove all records from both memory blocks

## Usage

To use the Memory module in your agent:

1. Choose an appropriate AgentMemory implementation (`ChatHistoryMemory`, `VectorDBMemory`, or `LongtermAgentMemory`).
2. Initialize the memory with a context creator and any necessary parameters.
3. Use `write_records()` to add new information to the memory.
4. Use `retrieve()` to get relevant context for the agent's next action.
5. Use `get_context()` to obtain the formatted context for the agent.

Example using `LongtermAgentMemory`:

```python
from camel.memories import (
    ChatHistoryBlock,
    LongtermAgentMemory,
    MemoryRecord,
    ScoreBasedContextCreator,
    VectorDBBlock,
)
from camel.messages import BaseMessage
from camel.types import ModelType, OpenAIBackendRole
from camel.utils import OpenAITokenCounter

# Initialize the memory
memory = LongtermAgentMemory(
    context_creator=ScoreBasedContextCreator(
        OpenAITokenCounter(ModelType.GPT_4O_MINI), 1024
    ),
    chat_history_block=ChatHistoryBlock(),
    vector_db_block=VectorDBBlock(),
)

# Create and write new records
records = [
    MemoryRecord(
        message=BaseMessage(
            role_name="user",
            role_type="human",
            meta_dict=None,
            content="What is machine learning?",
        ),
        role_at_backend=OpenAIBackendRole.USER,
    ),
    MemoryRecord(
        message=BaseMessage(
            role_name="agent",
            role_type="ai",
            meta_dict=None,
            content="Machine learning is a subset of AI...",
        ),
        role_at_backend=OpenAIBackendRole.ASSISTANT,
    ),
]
memory.write_records(records)

# Get context for the agent
context, token_count = memory.get_context()

print(context)
```

```markdown
>>> [{'role': 'user', 'content': 'What is machine learning?'}, {'role': 'assistant', 'content': 'Machine learning is a subset of AI...'}]
```

```python
print(token_count)
```

```markdown
>>> 27
```

## Advanced Topics

### Customizing Context Creator

You can create custom context creators by subclassing `BaseContextCreator`:

```python
from camel.memories import BaseContextCreator

class MyCustomContextCreator(BaseContextCreator):
    @property
    def token_counter(self):
        # Implement your token counting logic
        return 

    @property
    def token_limit(self):
        return 1000  # Or any other limit

    def create_context(self, records):
        # Implement your context creation logic
        pass

```

### Customizing Vector Database Block

For `VectorDBBlock`, you can customize it by adjusting the embedding models or vector storages:

```python
from camel.embeddings import OpenAIEmbedding
from camel.memories import VectorDBBlock
from camel.storages import QdrantStorage

vector_db = VectorDBBlock(
    embedding=OpenAIEmbedding(),
    storage=QdrantStorage(vector_dim=OpenAIEmbedding().get_output_dim()),
)
```

### Performance Considerations

- For large-scale applications, consider using persistent storage backends instead of in-memory storage.
- Optimize your context creator to balance between context relevance and token limits.
- When using `VectorDBMemory`, be mindful of the trade-off between retrieval accuracy and speed as the database grows.