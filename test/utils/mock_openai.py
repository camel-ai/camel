from unittest.mock import MagicMock
from typing import Optional, List, Dict, Any, Literal

from openai.types.chat import (
    ChatCompletion,
    ChatCompletionMessage,
    ChatCompletionMessageToolCall,
)
from openai.types.chat.chat_completion import Choice
from openai.types.completion_usage import CompletionUsage


def mock_chat_completion(
    content: str = "Mock response",
    role: Literal['assistant'] = "assistant",
    tool_calls: Optional[List[Dict[str, Any]]] = None,
    usage: Optional[CompletionUsage] = None,
) -> ChatCompletion:
    """Create a mock ChatCompletion object."""
    message = ChatCompletionMessage(
        role=role,
        content=content,
        tool_calls=[
            ChatCompletionMessageToolCall(**tc) for tc in tool_calls or []
        ],
    )
    
    return ChatCompletion(
        id="mock_id",
        choices=[Choice(finish_reason="stop", index=0, message=message)],
        created=1234567890,
        model="gpt-4",
        object="chat.completion",
        usage=usage if usage else CompletionUsage(
            completion_tokens=10,
            prompt_tokens=5,
            total_tokens=15
        ),
    )


def mock_openai_backend(
    content: str = "Mock response",
    role: Literal['assistant'] = "assistant",
    **kwargs
) -> MagicMock:
    """Create a mock OpenAI backend that returns a ChatCompletion."""
    mock = MagicMock()
    mock.run.return_value = mock_chat_completion(content, role, **kwargs)
    return mock