# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Union

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from camel.agents.chat_agent import ChatAgent
from camel.messages import BaseMessage


class ChatMessage(BaseModel):
    role: str
    content: str = ""
    name: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None


class FunctionDefinition(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]


class ChatCompletionRequest(BaseModel):
    model: str = "camel-model"
    messages: List[ChatMessage]
    max_tokens: Optional[int] = None
    temperature: Optional[float] = 0.7
    stream: Optional[bool] = False
    functions: Optional[List[Dict[str, Any]]] = None
    function_call: Optional[Union[str, Dict[str, Any]]] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None


class ChatCompletionChoice(BaseModel):
    index: int = 0
    message: ChatMessage
    finish_reason: str = "stop"


class ChatCompletionUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: ChatCompletionUsage


class ChatAgentServer:
    def __init__(self, agent: ChatAgent = None):
        self.agent = agent or ChatAgent()
        self.app = FastAPI(title="CAMEL OpenAI-compatible API")
        self.setup_routes()

    def setup_routes(self):
        @self.app.post("/v1/chat/completions")
        async def chat_completions(request: ChatCompletionRequest):
            # Convert OpenAI messages to CAMEL format
            camel_messages = []
            for msg in request.messages:
                if msg.role == "system":
                    system_msg = BaseMessage.make_system_message(
                        content=msg.content
                    )
                    self.agent._original_system_message = system_msg
                    self.agent._system_message = self.agent._generate_system_message_for_output_language()  # noqa: E501
                    self.agent.init_messages()
                elif msg.role == "user":
                    camel_messages.append(msg.content)
                elif msg.role == "assistant":
                    # Record previous assistant messages
                    assistant_msg = BaseMessage.make_assistant_message(
                        role_name="Assistant", content=msg.content
                    )
                    self.agent.record_message(assistant_msg)
                elif msg.role == "function":
                    # Handle function messages if needed
                    pass

            # Process tools/functions if provided
            if request.tools or request.functions:
                tools_to_use = (
                    request.tools if request.tools else request.functions
                )
                for tool in tools_to_use:
                    # Convert to CAMEL tool format and add to agent
                    if "function" in tool:
                        self.agent.add_external_tool(tool)
                    else:
                        self.agent.add_external_tool({"function": tool})

            # Get the response from the agent
            if len(camel_messages) > 0:
                last_message = camel_messages[-1]

                if request.stream:
                    return StreamingResponse(
                        self._stream_response(last_message, request),
                        media_type="text/event-stream",
                    )
                else:
                    agent_response = self.agent.step(last_message)

                    # Convert CAMEL response to OpenAI format
                    if not agent_response.msgs:
                        # Empty response or error
                        content = "No response generated"
                        finish_reason = "error"
                    else:
                        content = agent_response.msgs[0].content
                        finish_reason = "stop"

                    # Check for tool calls
                    function_call = None
                    if agent_response.info.get("external_tool_call_requests"):
                        tool_call = agent_response.info[
                            "external_tool_call_requests"
                        ][0]
                        function_call = {
                            "name": tool_call.tool_name,
                            "arguments": json.dumps(tool_call.args),
                        }
                        finish_reason = "function_call"

                    usage = agent_response.info.get("token_usage") or {
                        "prompt_tokens": agent_response.info.get(
                            "prompt_tokens", 0
                        ),
                        "completion_tokens": agent_response.info.get(
                            "completion_tokens", 0
                        ),
                        "total_tokens": agent_response.info.get(
                            "total_tokens", 0
                        ),
                    }

                    response = {
                        "id": agent_response.info.get(
                            "response_id", f"chatcmpl-{int(time.time())}"
                        ),
                        "object": "chat.completion",
                        "created": int(time.time()),
                        "model": request.model,
                        "choices": [
                            {
                                "index": 0,
                                "message": {
                                    "role": "assistant",
                                    "content": (
                                        content if not function_call else None
                                    ),
                                    "function_call": function_call,
                                },
                                "finish_reason": finish_reason,
                            }
                        ],
                        "usage": usage,
                    }

                    return response
            else:
                # No message provided
                return JSONResponse(
                    status_code=400,
                    content={"error": "No user message provided"},
                )

    async def _stream_response(
        self, message: str, request: ChatCompletionRequest
    ):
        # Start a separate task for the agent processing
        agent_response = self.agent.step(message)

        if not agent_response.msgs:
            # Stream an error message if no response
            yield f"data: {json.dumps({'error': 'No response generated'})}\n\n"
            return

        content = agent_response.msgs[0].content
        tokens = content.split(" ")

        # Send the first event with model info
        first_chunk = {
            'id': f'chatcmpl-{int(time.time())}',
            'object': 'chat.completion.chunk',
            'created': int(time.time()),
            'model': request.model,
            'choices': [
                {
                    'index': 0,
                    'delta': {'role': 'assistant'},
                    'finish_reason': None,
                }
            ],
        }
        yield f"data: {json.dumps(first_chunk)}\n\n"

        # Stream the content word by word
        for token in tokens:
            token_chunk = {
                'choices': [
                    {
                        'index': 0,
                        'delta': {'content': token + ' '},
                        'finish_reason': None,
                    }
                ]
            }
            yield f"data: {json.dumps(token_chunk)}\n\n"
            await asyncio.sleep(0.05)

        # Send the final event
        final_chunk = {
            'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}]
        }
        yield f"data: {json.dumps(final_chunk)}\n\n"
        yield "data: [DONE]\n\n"

    def run(self, host: str = "0.0.0.0", port: int = 8000):
        uvicorn.run(self.app, host=host, port=port)


def create_server(
    agent: ChatAgent = None, host: str = "0.0.0.0", port: int = 8000
):
    """Create and run an OpenAI-compatible server for a CAMEL ChatAgent.

    Args:
        agent: The ChatAgent to expose through the API
        host: Host address to bind the server to
        port: Port to run the server on

    Example:
        ```python
        from camel.agents.chat_agent import ChatAgent
        from services.openai_compatible_server import create_server

        agent = ChatAgent(model="gpt-4")
        create_server(agent, port=8000)
        ```
    """
    server = ChatAgentServer(agent)
    server.run(host=host, port=port)


if __name__ == "__main__":
    # Example usage, define your own agent here
    agent = ChatAgent()

    # Create the server
    server = ChatAgentServer(agent)
    server.run()
