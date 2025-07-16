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
import logging
from typing import (
    Any,
    AsyncIterable,
    ClassVar,
    Dict,
    List,
    Optional,
    Union,
)

import camel.toolkits.a2a.server.utils as utils
from camel.agents import ChatAgent
from camel.responses import ChatAgentResponse
from camel.toolkits.a2a.server.task_manager import InMemoryTaskManager
from camel.toolkits.a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    Artifact,
    DataPart,
    FilePart,
    InternalError,
    InvalidParamsError,
    JSONRPCError,
    JSONRPCResponse,
    Message,
    SendTaskRequest,
    SendTaskResponse,
    SendTaskStreamingRequest,
    SendTaskStreamingResponse,
    TaskSendParams,
    TaskState,
    TaskStatus,
    TextPart,
)

from .server import A2AServer

logger = logging.getLogger(__name__)


class A2AChatAgent:
    _default_content_types: ClassVar[List[str]] = ["text", "text/plain"]

    def __init__(
        self,
        agent: ChatAgent,
        SupportedContentTypes: Optional[List[str]] = None,
    ):
        default_types = self._default_content_types.copy()
        self._supported_content_types = SupportedContentTypes or default_types
        self.agent = agent
        self.agent.reset()

    @property
    def SUPPORTED_CONTENT_TYPES(self) -> List[str]:
        return self._supported_content_types

    @SUPPORTED_CONTENT_TYPES.setter
    def SUPPORTED_CONTENT_TYPES(self, value: List[str]) -> None:
        self._supported_content_types = value

    def invoke(self, query: str) -> ChatAgentResponse:
        respond = self.agent.step(query)
        return respond

    async def stream(self, query: str) -> AsyncIterable[Dict[str, Any]]:
        """Streaming is not supported by CrewAI."""
        raise NotImplementedError(
            "Streaming is not supported by Camel Ai Agent."
        )
        # Add an unreachable return to satisfy the type checker
        if False:
            yield {}

    def run(
        self,
        name: str,
        description: str,
        tags: list[str],
        example: list[str],
        host: str = "0.0.0.0",
        port: int = 10000,
    ) -> str:
        """Starts the CamelAI server."""
        capabilities = AgentCapabilities(streaming=False)
        skill = AgentSkill(
            id=name,
            name=name,
            description=description,
            tags=tags,
            examples=example,
        )
        agent_card = AgentCard(
            name=name,
            description=description,
            url=f"http://{host}:{port}/",
            version="1.0.0",
            defaultInputModes=["text"],
            defaultOutputModes=["text"],
            capabilities=capabilities,
            skills=[skill],
        )

        server = A2AServer(
            agent_card=agent_card,
            task_manager=AgentTaskManager(agent=self.agent),
            host=host,
            port=port,
        )

        print(f"Starting server on {host}:{port}")
        server.start()
        return f"Server started on {host}:{port}"


class AgentTaskManager(InMemoryTaskManager):
    """Task manager for the Google Scholar agent."""

    _default_content_types: ClassVar[List[str]] = ["text", "text/plain"]

    def __init__(self, agent: ChatAgent):
        super().__init__()
        self.agent = agent
        self.lock = asyncio.Lock()  # Initialize the lock
        self._supported_content_types = self._default_content_types.copy()

    @property
    def SUPPORTED_CONTENT_TYPES(self) -> List[str]:
        return self._supported_content_types

    @SUPPORTED_CONTENT_TYPES.setter
    def SUPPORTED_CONTENT_TYPES(self, value: List[str]) -> None:
        self._supported_content_types = value

    async def _run_streaming_agent(self, request: SendTaskStreamingRequest):
        raise NotImplementedError("Not implemented")

    def _get_user_query(self, task_send_params: TaskSendParams) -> str:
        part = task_send_params.message.parts[0]
        if not isinstance(part, TextPart):
            raise ValueError("Only text parts are supported")
        return part.text

    async def _process_agent_response(
        self, request: SendTaskRequest, agent_response: ChatAgentResponse
    ) -> SendTaskResponse:
        """Processes the agent's response and updates the task store."""
        if request.params is None:
            return SendTaskResponse(
                id=request.id,
                error=InvalidParamsError(message="Missing task parameters"),
            )

        task_send_params = TaskSendParams(**request.params)
        task_id = task_send_params.id
        history_length = task_send_params.historyLength

        # Extract the text from the first message
        if not agent_response.msgs:
            raise ValueError("ChatAgentResponse contains no messages")
        # Access the content through the BaseMessage object
        text = agent_response.msgs[0].content
        text_part = TextPart(type="text", text=text)
        parts: List[Union[TextPart, FilePart, DataPart]] = [text_part]

        # Use the terminated flag to decide if user input is required.
        if not agent_response.terminated:
            task_status = TaskStatus(
                state=TaskState.INPUT_REQUIRED,
                message=Message(role="agent", parts=parts),
            )
            artifact = None
        else:
            task_status = TaskStatus(state=TaskState.COMPLETED)
            artifact = Artifact(parts=parts)

        artifacts_list = [artifact] if artifact is not None else []
        task = await self.update_store(task_id, task_status, artifacts_list)
        task_result = self.append_task_history(task, history_length)

        return SendTaskResponse(id=request.id, result=task_result)

    def _validate_request(
        self, request: Union[SendTaskRequest, SendTaskStreamingRequest]
    ) -> Optional[JSONRPCError]:
        if request.params is None:
            return InvalidParamsError(message="Missing task parameters")

        task_send_params = TaskSendParams(**request.params)

        # Check if acceptedOutputModes exists and is not None
        accepted_modes = task_send_params.acceptedOutputModes
        if accepted_modes is None:
            accepted_modes = []

        if not utils.are_modalities_compatible(
            accepted_modes,
            self.SUPPORTED_CONTENT_TYPES,
        ):
            logger.warning(
                "Unsupported output mode. Received %s, Support %s",
                accepted_modes,
                self.SUPPORTED_CONTENT_TYPES,
            )
            return utils.new_incompatible_types_error(request.id)

        if (
            task_send_params.pushNotification
            and not task_send_params.pushNotification.url
        ):
            logger.warning("Push notification URL is missing")
            return InvalidParamsError(
                message="Push notification URL is missing"
            )

        return None

    async def on_send_task(self, request: SendTaskRequest) -> SendTaskResponse:
        """Handles the 'send task' request."""
        try:
            error = self._validate_request(request)
            if error:
                return SendTaskResponse(
                    id=request.id,
                    error=error,
                )

            if request.params is None:
                return SendTaskResponse(
                    id=request.id,
                    error=InvalidParamsError(
                        message="Missing task parameters"
                    ),
                )

            task_send_params = TaskSendParams(**request.params)
            await self.upsert_task(task_send_params)

            query = self._get_user_query(task_send_params)
            try:
                # Use invoke method we've implemented
                task = self.invoke(query)
            except Exception as e:
                logger.error("Error invoking agent: %s", str(e))
                return SendTaskResponse(
                    id=request.id,
                    error=InternalError(
                        code=500,
                        message="Internal server error",
                        data=str(e),
                    ),
                )

            return await self._process_agent_response(request, task)
        except Exception as e:
            logger.error("Error processing task: %s", str(e))
            return SendTaskResponse(
                id=request.id,
                error=InternalError(
                    code=500,
                    message="Internal server error",
                    data=str(e),
                ),
            )

    # Since ChatAgent doesn't have 'invoke', add a method that calls step
    def invoke(self, query: str) -> ChatAgentResponse:
        return self.agent.step(query)

    async def on_send_task_subscribe(
        self, request: SendTaskStreamingRequest
    ) -> Union[AsyncIterable[SendTaskStreamingResponse], JSONRPCResponse]:
        error = self._validate_request(request)
        if error:
            return JSONRPCResponse(id=request.id, error=error)

        if request.params is None:
            return JSONRPCResponse(
                id=request.id,
                error=InvalidParamsError(message="Missing task parameters"),
            )

        task_send_params = TaskSendParams(**request.params)
        await self.upsert_task(task_send_params)

        # Return NotImplementedError since streaming is not supported
        return JSONRPCResponse(
            id=request.id,
            error=InternalError(
                message="Streaming is not supported by this agent"
            ),
        )
