from typing import Any, Dict, List, Optional, Union

from openai import AsyncStream, Stream
from pydantic import BaseModel, ConfigDict

from camel.messages import BaseMessage
from camel.types import ChatCompletion


class ToolCallRequest(BaseModel):
    r"""The request for tool calling."""

    func_name: str
    args: Dict[str, Any]


class ModelResponse(BaseModel):
    r"""The response from the model."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    response: Union[ChatCompletion, Stream, AsyncStream]
    tool_call_request: Optional[ToolCallRequest]
    output_messages: List[BaseMessage]
    finish_reasons: List[str]
    usage_dict: Dict[str, Any]
    response_id: str
