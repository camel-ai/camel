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
from camel.models import ModelFactory
from camel.toolkits import FunctionTool
from camel.types import RoleType


class InitRequest(BaseModel):
    r"""Request schema for initializing a ChatAgent via the OpenAPI server.

    Defines the configuration used to create a new agent, including the model,
    system message, tool names, and generation parameters.

    Args:
        model_type (Optional[str]): The model type to use. Should match a key
            supported by the model manager, e.g., "gpt-4o-mini".
            (default: :obj:`"gpt-4o-mini"`)
        model_platform (Optional[str]): The model platform to use.
            (default: :obj:`"openai"`)
        tools_names (Optional[List[str]]): A list of tool names to load from
            the tool registry. These tools will be available to the agent.
            (default: :obj:`None`)
        external_tools (Optional[List[Dict[str, Any]]]): Tool definitions
            provided directly as dictionaries, bypassing the registry.
            Currently not supported. (default: :obj:`None`)
        agent_id (str): The unique identifier for the agent. Must be provided
            explicitly to support multi-agent routing and control.
        system_message (Optional[str]): The system prompt for the agent,
            describing its behavior or role. (default: :obj:`None`)
        message_window_size (Optional[int]): The number of recent messages to
            retain in memory for context. (default: :obj:`None`)
        token_limit (Optional[int]): The token budget for contextual memory.
            (default: :obj:`None`)
        output_language (Optional[str]): Preferred output language for the
            agent's replies. (default: :obj:`None`)
        max_iteration (Optional[int]): Maximum number of model
            calling iterations allowed per step. If `None` (default), there's
            no explicit limit. If `1`, it performs a single model call. If `N
            > 1`, it allows up to N model calls. (default: :obj:`None`)
    """

    model_type: Optional[str] = "gpt-4o-mini"
    model_platform: Optional[str] = "openai"

    tools_names: Optional[List[str]] = None
    external_tools: Optional[List[Dict[str, Any]]] = None

    agent_id: str  # Required: explicitly set agent_id to
    # support future multi-agent and permission control

    system_message: Optional[str] = None
    message_window_size: Optional[int] = None
    token_limit: Optional[int] = None
    output_language: Optional[str] = None
    max_iteration: Optional[int] = None  # Changed from Optional[bool] = False


class StepRequest(BaseModel):
    r"""Request schema for sending a user message to a ChatAgent.

    Supports plain text input or structured message dictionaries, with an
    optional response format for controlling output structure.

    Args:
        input_message (Union[str, Dict[str, Any]]): The user message to send.
            Can be a plain string or a message dict with role, content, etc.
        response_format (Optional[str]): Optional format name that maps to a
            registered response schema. Not currently in use.
            (default: :obj:`None`)
    """

    input_message: Union[str, Dict[str, Any]]
    response_format: Optional[str] = None  # reserved, not used yet


class ChatAgentOpenAPIServer:
    r"""A FastAPI server wrapper for managing ChatAgents via OpenAPI routes.

    This server exposes a versioned REST API for interacting with CAMEL
    agents, supporting initialization, message passing, memory inspection,
    and optional tool usage. It supports multi-agent use cases by mapping
    unique agent IDs to active ChatAgent instances.

    Typical usage includes initializing agents with system prompts and tools,
    exchanging messages using /step or /astep endpoints, and inspecting agent
    memory with /history.

    Supports pluggable tool and response format registries for customizing
    agent behavior or output schemas.
    """

    def __init__(
        self,
        tool_registry: Optional[Dict[str, List[FunctionTool]]] = None,
        response_format_registry: Optional[Dict[str, Type[BaseModel]]] = None,
    ):
        r"""Initializes the OpenAPI server for managing ChatAgents.

        Sets up internal agent storage, tool and response format registries,
        and prepares versioned API routes.

        Args:
            tool_registry (Optional[Dict[str, List[FunctionTool]]]): A mapping
                from tool names to lists of FunctionTool instances available
                to agents via the "tools_names" field. If not provided, an
                empty registry is used. (default: :obj:`None`)
            response_format_registry (Optional[Dict[str, Type[BaseModel]]]):
                A mapping from format names to Pydantic output schemas for
                structured response parsing. Used for controlling the format
                of step results. (default: :obj:`None`)
        """

        # Initialize FastAPI app and agent
        self.app = FastAPI(title="CAMEL OpenAPI-compatible Server")
        self.agents: Dict[str, ChatAgent] = {}
        self.tool_registry = tool_registry or {}
        self.response_format_registry = response_format_registry or {}
        self._setup_routes()

    def _parse_input_message_for_step(
        self, raw: Union[str, dict]
    ) -> BaseMessage:
        r"""Parses raw input into a BaseMessage object.

        Args:
            raw (str or dict): User input as plain text or dict.

        Returns:
            BaseMessage: Parsed input message.
        """
        if isinstance(raw, str):
            return BaseMessage.make_user_message(role_name="User", content=raw)
        elif isinstance(raw, dict):
            if isinstance(raw.get("role_type"), str):
                raw["role_type"] = RoleType(raw["role_type"].lower())
            return BaseMessage(**raw)
        raise HTTPException(
            status_code=400, detail="Unsupported input format."
        )

    def _resolve_response_format_for_step(
        self, name: Optional[str]
    ) -> Optional[Type[BaseModel]]:
        r"""Resolves the response format by name.

        Args:
            name (str or None): Optional format name.

        Returns:
            Optional[Type[BaseModel]]: Response schema class.
        """
        if name is None:
            return None
        if name not in self.response_format_registry:
            raise HTTPException(
                status_code=400, detail=f"Unknown response_format: {name}"
            )
        return self.response_format_registry[name]

    def _setup_routes(self):
        r"""Registers OpenAPI endpoints for agent creation and interaction.

        This includes routes for initializing agents (/init), sending
        messages (/step and /astep), resetting agent memory (/reset), and
        retrieving conversation history (/history). All routes are added
        under the /v1/agents namespace.
        """

        router = APIRouter(prefix="/v1/agents")

        @router.post("/init")
        def init_agent(request: InitRequest):
            r"""Initializes a ChatAgent instance with a model,
            system message, and optional tools.

            Args:
                request (InitRequest): The agent config including
                    model, tools, system message, and agent ID.

            Returns:
                dict: A message with the agent ID and status.
            """

            agent_id = request.agent_id
            if agent_id in self.agents:
                return {
                    "agent_id": agent_id,
                    "message": "Agent already exists.",
                }

            model_type = request.model_type
            model_platform = request.model_platform

            model = ModelFactory.create(
                model_platform=model_platform,  # type: ignore[arg-type]
                model_type=model_type,  # type: ignore[arg-type]
            )

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

            agent = ChatAgent(
                model=model,
                tools=tools,  # type: ignore[arg-type]
                external_tools=request.external_tools,  # type: ignore[arg-type]
                system_message=system_message,
                message_window_size=request.message_window_size,
                token_limit=request.token_limit,
                output_language=request.output_language,
                max_iteration=request.max_iteration,
                agent_id=agent_id,
            )

            self.agents[agent_id] = agent
            return {"agent_id": agent_id, "message": "Agent initialized."}

        @router.post("/astep/{agent_id}")
        async def astep_agent(agent_id: str, request: StepRequest):
            r"""Runs one async step of agent response.

            Args:
                agent_id (str): The ID of the target agent.
                request (StepRequest): The input message.

            Returns:
                dict: The model response in serialized form.
            """

            if agent_id not in self.agents:
                raise HTTPException(status_code=404, detail="Agent not found.")

            agent = self.agents[agent_id]
            input_message = self._parse_input_message_for_step(
                request.input_message
            )
            format_cls = self._resolve_response_format_for_step(
                request.response_format
            )

            try:
                response = await agent.astep(
                    input_message=input_message, response_format=format_cls
                )
                return response.model_dump()
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Unexpected error during async step: {e!s}",
                )

        @router.get("/list_agent_ids")
        def list_agent_ids():
            r"""Returns a list of all active agent IDs.

            Returns:
                dict: A dictionary containing all registered agent IDs.
            """
            return {"agent_ids": list(self.agents.keys())}

        @router.post("/delete/{agent_id}")
        def delete_agent(agent_id: str):
            r"""Deletes an agent from the server.

            Args:
                agent_id (str): The ID of the agent to delete.

            Returns:
                dict: A confirmation message upon successful deletion.
            """
            if agent_id not in self.agents:
                raise HTTPException(status_code=404, detail="Agent not found.")

            del self.agents[agent_id]
            return {"message": f"Agent {agent_id} deleted."}

        @router.post("/step/{agent_id}")
        def step_agent(agent_id: str, request: StepRequest):
            r"""Runs one step of synchronous agent response.

            Args:
                agent_id (str): The ID of the target agent.
                request (StepRequest): The input message.

            Returns:
                dict: The model response in serialized form.
            """
            if agent_id not in self.agents:
                raise HTTPException(status_code=404, detail="Agent not found.")

            agent = self.agents[agent_id]
            input_message = self._parse_input_message_for_step(
                request.input_message
            )
            format_cls = self._resolve_response_format_for_step(
                request.response_format
            )
            try:
                response = agent.step(
                    input_message=input_message, response_format=format_cls
                )
                return response.model_dump()
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Unexpected error during step: {e!s}",
                )

        @router.post("/reset/{agent_id}")
        def reset_agent(agent_id: str):
            r"""Clears memory for a specific agent.

            Args:
                agent_id (str): The ID of the agent to reset.

            Returns:
                dict: A message confirming reset success.
            """
            if agent_id not in self.agents:
                raise HTTPException(status_code=404, detail="Agent not found.")
            self.agents[agent_id].reset()
            return {"message": f"Agent {agent_id} reset."}

        @router.get("/history/{agent_id}")
        def get_agent_chat_history(agent_id: str):
            r"""Returns the chat history of an agent.

            Args:
                agent_id (str): The ID of the agent to query.

            Returns:
                list: The list of conversation messages.
            """
            if agent_id not in self.agents:
                raise HTTPException(
                    status_code=404, detail=f"Agent {agent_id} not found."
                )
            return self.agents[agent_id].chat_history

        # Register all routes to the main FastAPI app
        self.app.include_router(router)

    def get_app(self) -> FastAPI:
        r"""Returns the FastAPI app instance.

        Returns:
            FastAPI: The wrapped application object.
        """
        return self.app
