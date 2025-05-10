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


from typing import Any, Dict, List, Optional, Type, Union

from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel

from camel.agents.chat_agent import ChatAgent
from camel.messages import BaseMessage
from camel.toolkits import FunctionTool
from camel.types import ModelType, RoleType


class InitRequest(BaseModel):
    model: Optional[str] = "gpt-4o-mini"
    tools_names: Optional[List[str]] = None
    external_tools: Optional[List[Dict[str, Any]]] = None

    agent_id: str  # Required: explicitly set agent_id to
    # support future multi-agent and permission control

    system_message: Optional[str] = None
    message_window_size: Optional[int] = None
    token_limit: Optional[int] = None
    output_language: Optional[str] = None
    single_iteration: Optional[bool] = False


class StepRequest(BaseModel):
    input_message: Union[str, Dict[str, Any]]
    response_format: Optional[str] = None  # reserved, not used yet


class ChatAgentOpenAPIServer:
    r"""A modular FastAPI server for ChatAgent with versioned routes and
    multi-agent support.
    """

    def __init__(
        self,
        tool_registry: Optional[Dict[str, List[FunctionTool]]] = None,
        response_format_registry: Optional[Dict[str, Type[BaseModel]]] = None,
    ):
        r"""
        Initialize a ChatAgentOpenAPIServer instance.
        Args:
            agent:
            tool_registry: a dictionary mapping tool names to actual tools
            response_format_registry: a dictionary mapping ChatAgent Response
                format names to actual data models
        """

        # Initialize FastAPI app and agent
        self.app = FastAPI(title="CAMEL OpenAPI-compatible Server")
        self.agents: Dict[str, ChatAgent] = {}
        self.tool_registry = tool_registry or {}
        self.response_format_registry = response_format_registry or {}
        self._setup_routes()

    def _setup_routes(self):
        router = APIRouter(prefix="/v1")

        @router.post("/init")
        def init_agent(request: InitRequest):
            r"""
            Note: The following ChatAgent parameters are currently
            not supported via the init API:

            - (type of) memory
            - response_terminators
            - scheduling_strategy
            - stop_event

            These limitations may be relaxed in future
            versions as needed
            Args:
                request:

            Returns:

            """

            agent_id = request.agent_id
            if agent_id in self.agents:
                return {
                    "agent_id": agent_id,
                    "message": "Agent already exists.",
                }

            model = request.model

            # tools lookup
            tools = []
            if request.tools_names:
                for name in request.tools_names:
                    if name in self.tool_registry:
                        tools.extend(self.tool_registry[name])
                    else:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Tool '{name}' " f"not found in registry",
                        )

            # system message
            system_message = request.system_message

            model = ModelType(model)
            agent = ChatAgent(
                model=model,
                tools=tools,
                system_message=system_message,
                message_window_size=request.message_window_size,
                token_limit=request.token_limit,
                output_language=request.output_language,
                single_iteration=request.single_iteration,
                agent_id=agent_id,
            )

            self.agents[agent_id] = agent
            return {"agent_id": agent_id, "message": "Agent initialized."}

        # === Step Agent Helpers ===
        def _parse_input_message_for_step(
            raw: Union[str, dict],
        ) -> BaseMessage:
            if isinstance(raw, str):
                return BaseMessage.make_user_message(
                    role_name="User", content=raw
                )
            elif isinstance(raw, dict):
                if isinstance(raw.get("role_type"), str):
                    raw["role_type"] = RoleType(raw["role_type"].lower())
                return BaseMessage(**raw)
            raise HTTPException(
                status_code=400, detail="Unsupported input format."
            )

        def _resolve_response_format_for_step(
            name: Optional[str],
        ) -> Optional[Type[BaseModel]]:
            if name is None:
                return None
            if name not in self.response_format_registry:
                raise HTTPException(
                    status_code=400, detail=f"Unknown response_format: {name}"
                )
            return self.response_format_registry[name]

        # === Step Agent Helpers end===

        @router.post("/astep/{agent_id}")
        async def astep_agent(agent_id: str, request: StepRequest):
            if agent_id not in self.agents:
                raise HTTPException(status_code=404, detail="Agent not found.")

            agent = self.agents[agent_id]
            input_message = _parse_input_message_for_step(
                request.input_message
            )
            format_cls = _resolve_response_format_for_step(
                request.response_format
            )

            response = await agent.astep(
                input_message=input_message, response_format=format_cls
            )
            return response.model_dump()

        @router.post("/step/{agent_id}")
        def step_agent(agent_id: str, request: StepRequest):
            if agent_id not in self.agents:
                raise HTTPException(status_code=404, detail="Agent not found.")

            agent = self.agents[agent_id]
            input_message = _parse_input_message_for_step(
                request.input_message
            )
            format_cls = _resolve_response_format_for_step(
                request.response_format
            )

            response = agent.step(
                input_message=input_message, response_format=format_cls
            )
            return response.model_dump()

        @router.post("/reset/{agent_id}")
        def reset_agent(agent_id: str):
            if agent_id not in self.agents:
                raise HTTPException(status_code=404, detail="Agent not found.")
            self.agents[agent_id].reset()
            return {"message": f"Agent {agent_id} reset."}

        @router.get("/history/{agent_id}")
        def get_agent_chat_history(agent_id: str):
            if agent_id not in self.agents:
                raise HTTPException(status_code=404, detail="Agent not found.")
            return self.agents[agent_id].chat_history

        # Register all routes to the main FastAPI app
        self.app.include_router(router)

    def get_app(self) -> FastAPI:
        """Returns the FastAPI app instance for deployment."""
        return self.app
