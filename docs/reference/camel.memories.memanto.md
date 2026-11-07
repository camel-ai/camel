<a id="camel.memories.memanto"></a>

# Memanto Memory

<a id="camel.memories.memanto.MemantoMemory"></a>

## MemantoMemory

```python
class MemantoMemory(ChatHistoryMemory):
```

Automatic semantic long-term memory for `ChatAgent`. Complete conversation
records use the normal chat-history storage. User and assistant text is also
archived in Memanto, and relevant memories are added as historical context
when generating model input.

**Parameters:**

- **context_creator** (`BaseContextCreator`): Context creation strategy.
- **agent_id** (`str`, optional): Existing Memanto agent ID; falls back to
  `MEMANTO_AGENT_ID`. This selects the remote archive at construction time.
- **base_url** (`str`, optional): Memanto server URL; falls back to
  `MEMANTO_BASE_URL`, then `http://localhost:8000`.
- **storage** (`BaseKeyValueStorage`, optional): Storage for current chat
  history. Defaults to in-memory storage.
- **window_size** (`int`, optional): Recent chat-history window. Defaults to
  the complete current conversation.
- **retrieve_limit** (`int`, optional): Maximum semantic recall results,
  from 1 to 100. Defaults to 3.
- **timeout** (`float`, optional): HTTP timeout in seconds. Defaults to 30.

### write_records

```python
def write_records(self, records: List[MemoryRecord]) -> None:
```

Stores complete records in chat history, then archives nonempty user and
assistant text in Memanto. System instructions, tool-call metadata, and
attachments stay in chat history. Remote text memories supplement context;
they do not provide exact conversation restoration.

HTTP failures propagate. If a remote write fails, the original records remain
in chat history. Session expiration triggers one retry with a fresh token.

### retrieve

```python
def retrieve(self) -> List[ContextRecord]:
```

Searches Memanto with the latest user message in the chat-history window and
combines matching memories with that history. Memories corresponding to
records already in the window are omitted. Recalled context is placed after
initial instructions and before conversation turns, preserving tool-call and
tool-response pairs.

Without a user message, retrieval returns chat history without a remote query.

### clear

```python
def clear(self) -> None:
```

Clears current chat history. Remote memories remain available across agent
initialization and resets; delete archived memories through Memanto itself.
Inherited rollback and tool-cleanup operations also affect chat history only.

### close

```python
def close(self) -> None:
```

Closes the HTTP client without deleting memory. Call when finished using the
memory instance.

See the [usage example](/key_modules/memory) and
[Memanto documentation](https://docs.memanto.ai).
