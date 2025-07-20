<a id="camel.utils.message_summarizer"></a>

<a id="camel.utils.message_summarizer.MessageSummary"></a>

## MessageSummary

```python
class MessageSummary(BaseModel):
```

Schema for structured message summaries.

**Parameters:**

- **summary** (str): A brief, one-sentence summary of the conversation.
- **participants** (List[str]): The roles of participants involved.
- **key_topics_and_entities** (List[str]): Important topics, concepts, and entities discussed.
- **decisions_and_outcomes** (List[str]): Key decisions, conclusions, or outcomes reached.
- **action_items** (List[str]): A list of specific tasks or actions to be taken, with assignees if mentioned.
- **progress_on_main_task** (str): A summary of progress made on the primary task.

<a id="camel.utils.message_summarizer.MessageSummarizer"></a>

## MessageSummarizer

```python
class MessageSummarizer:
```

Utility class for generating structured summaries of chat messages.

**Parameters:**

- **model_backend** (Optional[BaseModelBackend], optional): The model backend to use for summarization. If not provided, a default model backend will be created.

<a id="camel.utils.message_summarizer.MessageSummarizer.__init__"></a>

### __init__

```python
def __init__(self, model_backend: Optional[BaseModelBackend] = None):
```

<a id="camel.utils.message_summarizer.MessageSummarizer.summarize"></a>

### summarize

```python
def summarize(self, messages: List[BaseMessage]):
```

Generate a structured summary of the provided messages.

**Parameters:**

- **messages** (List[BaseMessage]): List of messages to summarize.

**Returns:**

  MessageSummary: Structured summary of the conversation.
