<a id="camel.memories.context_creators.score_based"></a>

<a id="camel.memories.context_creators.score_based.ScoreBasedContextCreator"></a>

## ScoreBasedContextCreator

```python
class ScoreBasedContextCreator(BaseContextCreator):
```

A default implementation of context creation strategy, which inherits
from :obj:`BaseContextCreator`.

This class provides a strategy to generate a conversational context from
a list of chat history records while ensuring the total token count of
the context does not exceed a specified limit. It prunes messages based
on their score if the total token count exceeds the limit.

**Parameters:**

- **token_counter** (BaseTokenCounter): An instance responsible for counting tokens in a message.
- **token_limit** (int): The maximum number of tokens allowed in the generated context.

<a id="camel.memories.context_creators.score_based.ScoreBasedContextCreator.__init__"></a>

### __init__

```python
def __init__(self, token_counter: BaseTokenCounter, token_limit: int):
```

<a id="camel.memories.context_creators.score_based.ScoreBasedContextCreator.token_counter"></a>

### token_counter

```python
def token_counter(self):
```

<a id="camel.memories.context_creators.score_based.ScoreBasedContextCreator.token_limit"></a>

### token_limit

```python
def token_limit(self):
```

<a id="camel.memories.context_creators.score_based.ScoreBasedContextCreator.create_context"></a>

### create_context

```python
def create_context(self, records: List[ContextRecord]):
```

Constructs conversation context from chat history while respecting
token limits.

Key strategies:
1. System message is always prioritized and preserved
2. Truncation removes low-score messages first
3. Final output maintains chronological order and in history memory,
the score of each message decreases according to keep_rate. The
newer the message, the higher the score.
4. Tool calls and their responses are kept together to maintain
API compatibility

**Parameters:**

- **records** (List[ContextRecord]): List of context records with scores and timestamps.

**Returns:**

  Tuple[List[OpenAIMessage], int]:
- Ordered list of OpenAI messages
- Total token count of the final context

<a id="camel.memories.context_creators.score_based.ScoreBasedContextCreator._group_tool_calls_and_responses"></a>

### _group_tool_calls_and_responses

```python
def _group_tool_calls_and_responses(self, units: List[_ContextUnit]):
```

Groups tool calls with their corresponding responses based on
`tool_call_id`.

This improved logic robustly gathers all messages (assistant requests
and tool responses, including chunks) that share a `tool_call_id`.

**Parameters:**

- **units** (List[_ContextUnit]): List of context units to analyze.

**Returns:**

  Dict[str, List[_ContextUnit]]: Mapping from `tool_call_id` to a
list of related units.

<a id="camel.memories.context_creators.score_based.ScoreBasedContextCreator._truncate_with_tool_call_awareness"></a>

### _truncate_with_tool_call_awareness

```python
def _truncate_with_tool_call_awareness(
    self,
    regular_units: List[_ContextUnit],
    tool_call_groups: Dict[str, List[_ContextUnit]],
    system_tokens: int
):
```

Truncates messages while preserving tool call-response pairs.
This method implements a more sophisticated truncation strategy:
1. It treats tool call groups (request + responses) and standalone
messages as individual items to be included.
2. It sorts all items by score and greedily adds them to the context.
3. **Partial Truncation**: If a complete tool group is too large to
fit,it attempts to add the request message and as many of the most
recent response chunks as the token budget allows.

**Parameters:**

- **regular_units** (List[_ContextUnit]): All regular message units.
- **tool_call_groups** (Dict[str, List[_ContextUnit]]): Grouped tool calls.
- **system_tokens** (int): Tokens used by the system message.

**Returns:**

  List[_ContextUnit]: A list of units that fit within the token
limit.

<a id="camel.memories.context_creators.score_based.ScoreBasedContextCreator._extract_system_message"></a>

### _extract_system_message

```python
def _extract_system_message(self, records: List[ContextRecord]):
```

Extracts the system message from records and validates it.

**Parameters:**

- **records** (List[ContextRecord]): List of context records representing conversation history.

**Returns:**

  Tuple[Optional[_ContextUnit], List[_ContextUnit]]: containing:
- The system message as a `_ContextUnit`, if valid; otherwise,
`None`.
- An empty list, serving as the initial container for regular
messages.

<a id="camel.memories.context_creators.score_based.ScoreBasedContextCreator._conversation_sort_key"></a>

### _conversation_sort_key

```python
def _conversation_sort_key(self, unit: _ContextUnit):
```

Defines the sorting key for assembling the final output.

Sorting priority:
- Primary: Sort by timestamp in ascending order (chronological order).
- Secondary: Sort by score in descending order (higher scores first
when timestamps are equal).

**Parameters:**

- **unit** (_ContextUnit): A `_ContextUnit` representing a conversation record.

**Returns:**

  Tuple[float, float]:
- Timestamp for chronological sorting.
- Negative score for descending order sorting.

<a id="camel.memories.context_creators.score_based.ScoreBasedContextCreator._assemble_output"></a>

### _assemble_output

```python
def _assemble_output(
    self,
    context_units: List[_ContextUnit],
    system_unit: Optional[_ContextUnit]
):
```

Assembles final message list with proper ordering and token count.

**Parameters:**

- **context_units** (List[_ContextUnit]): Sorted list of regular message units.
- **system_unit** (Optional[_ContextUnit]): System message unit (if present).

**Returns:**

  Tuple[List[OpenAIMessage], int]: Tuple of (ordered messages, total
tokens)
