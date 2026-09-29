# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========


import hmac
import secrets
import threading
from typing import Any, Dict, List, Optional, Type, Union

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

from camel.agents.chat_agent import ChatAgent
from camel.logger import get_logger
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.toolkits import FunctionTool
from camel.types import RoleType

logger = get_logger(__name__)


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

    Authentication and ownership: every request must present one of the
    configured API keys (``Authorization: Bearer <key>`` or
    ``X-API-Key: <key>``). An agent belongs to the key that created it:
    its history, memory resets, message steps, and deletion are only
    reachable by that key, and ``list_agent_ids`` only reports the
    caller's own agents. When ``api_keys`` is not provided, one ephemeral
    key is generated and exposed as :attr:`api_key`, so deployments are
    authenticated by default; pass a non-empty list to provision your
    own keys (multi-tenant), or an empty list to explicitly run without
    authentication (single-user, trusted-network deployments only).
    """

    def __init__(
        self,
        tool_registry: Optional[Dict[str, List[FunctionTool]]] = None,
        response_format_registry: Optional[Dict[str, Type[BaseModel]]] = None,
        api_keys: Optional[List[str]] = None,
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
            api_keys (Optional[List[str]]): API keys clients must present.
                :obj:`None` (default) generates one ephemeral key exposed as
                :attr:`api_key`; a non-empty list enables multi-tenant
                ownership (agents are private to the key that created
                them); an empty list explicitly disables authentication.
        """

        # Initialize FastAPI app and agent
        self.app = FastAPI(title="CAMEL OpenAPI-compatible Server")
        self.agents: Dict[str, ChatAgent] = {}
        self.tool_registry = tool_registry or {}
        self.response_format_registry = response_format_registry or {}

        if api_keys is None:
            api_keys = [secrets.token_urlsafe(32)]
        elif not api_keys:
            logger.warning(
                "ChatAgentOpenAPIServer started with authentication "
                "disabled (api_keys=[]); every caller shares one "
                "identity. Use only in single-user, trusted-network "
                "deployments."
            )
        self.api_keys: List[str] = list(api_keys)
        self.api_key: Optional[str] = (
            self.api_keys[0] if self.api_keys else None
        )
        # agent_id -> key that created the agent. The configured keys are
        # already held in memory for authentication, so ownership stores
        # the key itself; agent-scoped comparisons run in constant time.
        self._agent_owners: Dict[str, str] = {}
        # Serialises /init's check -> create -> register sequence: the
        # model construction between the existence check and the registry
        # write takes long enough for concurrent inits of the same
        # agent_id to double-register across owners.
        self._registry_lock = threading.Lock()
        self._setup_routes()

    @staticmethod
    def _owner_id(presented_key: str) -> str:
        r"""Returns the owner identity for a presented API key.

        Args:
            presented_key (str): The validated API key.

        Returns:
            str: The owner identity recorded for agents created by this
                key.
        """
        return presented_key

    def _verify_api_key(
        self,
        x_api_key: Optional[str] = Header(default=None),
        authorization: Optional[str] = Header(default=None),
    ) -> str:
        r"""FastAPI dependency resolving and validating the caller.

        Args:
            x_api_key (Optional[str]): Value of the ``X-API-Key`` header.
            authorization (Optional[str]): Value of the ``Authorization``
                header; a ``Bearer <key>`` scheme is accepted.

        Returns:
            str: The caller's internal key id used for ownership checks.
                When authentication is disabled (``api_keys=[]``), a
                single shared owner id is returned for every caller.

        Raises:
            HTTPException: 401 when no valid key is presented.
        """
        if not self.api_keys:
            # Authentication explicitly disabled: every caller shares one
            # anonymous identity (single-user, trusted-network mode).
            return "anonymous"

        presented: Optional[str] = None
        if authorization:
            scheme, _, value = authorization.partition(" ")
            if scheme.lower() == "bearer" and value.strip():
                presented = value.strip()
        if presented is None and x_api_key:
            presented = x_api_key.strip()

        if presented is None:
            raise HTTPException(
                status_code=401,
                detail="Missing API key. Pass it via 'Authorization: "
                "Bearer <key>' or 'X-API-Key: <key>'.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        presented_bytes = presented.encode("utf-8")
        for key in self.api_keys:
            if hmac.compare_digest(key.encode("utf-8"), presented_bytes):
                return self._owner_id(key)
        raise HTTPException(
            status_code=401,
            detail="Invalid API key.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    def _get_owned_agent(self, agent_id: str, caller: str) -> ChatAgent:
        r"""Returns the requested agent when it belongs to the caller.

        Args:
            agent_id (str): The ID of the target agent.
            caller (str): The caller's key id.

        Returns:
            ChatAgent: The agent registered under ``agent_id``.

        Raises:
            HTTPException: 404 when the agent does not exist or belongs
                to a different key (existence is not disclosed across
                owners).
        """
        agent = self.agents.get(agent_id)
        owner = self._agent_owners.get(agent_id)
        if (
            agent is None
            or owner is None
            or not hmac.compare_digest(owner, caller)
        ):
            raise HTTPException(status_code=404, detail="Agent not found.")
        return agent

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
        def init_agent(
            request: InitRequest,
            caller: str = Depends(self._verify_api_key),
        ):
            r"""Initializes a ChatAgent instance with a model,
            system message, and optional tools.

            Args:
                request (InitRequest): The agent config including
                    model, tools, system message, and agent ID.
                caller (str): The caller's key id (from the dependency).

            Returns:
                dict: A message with the agent ID and status.
            """

            agent_id = request.agent_id
            with self._registry_lock:
                if agent_id in self.agents:
                    owner = self._agent_owners.get(agent_id)
                    if owner is None or not hmac.compare_digest(owner, caller):
                        raise HTTPException(
                            status_code=409,
                            detail=(
                                f"Agent id {agent_id!r} is already taken "
                                "by another client."
                            ),
                        )
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
                                detail=f"Tool '{name}' "
                                f"not found in registry",
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
                self._agent_owners[agent_id] = caller
            return {"agent_id": agent_id, "message": "Agent initialized."}

        @router.post("/astep/{agent_id}")
        async def astep_agent(
            agent_id: str,
            request: StepRequest,
            caller: str = Depends(self._verify_api_key),
        ):
            r"""Runs one async step of agent response.

            Args:
                agent_id (str): The ID of the target agent.
                request (StepRequest): The input message.
                caller (str): The caller's key id (from the dependency).

            Returns:
                dict: The model response in serialized form.
            """

            agent = self._get_owned_agent(agent_id, caller)
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
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Unexpected error during async step: {e!s}",
                )

        @router.get("/list_agent_ids")
        def list_agent_ids(caller: str = Depends(self._verify_api_key)):
            r"""Returns the list of agent IDs owned by the caller.

            Args:
                caller (str): The caller's key id (from the dependency).

            Returns:
                dict: A dictionary containing the caller's agent IDs.
            """
            return {
                "agent_ids": [
                    agent_id
                    for agent_id, owner in list(self._agent_owners.items())
                    if hmac.compare_digest(owner, caller)
                ]
            }

        @router.post("/delete/{agent_id}")
        def delete_agent(
            agent_id: str,
            caller: str = Depends(self._verify_api_key),
        ):
            r"""Deletes an agent from the server.

            Args:
                agent_id (str): The ID of the agent to delete.
                caller (str): The caller's key id (from the dependency).

            Returns:
                dict: A confirmation message upon successful deletion.
            """
            self._get_owned_agent(agent_id, caller)

            self.agents.pop(agent_id, None)
            self._agent_owners.pop(agent_id, None)
            return {"message": f"Agent {agent_id} deleted."}

        @router.post("/step/{agent_id}")
        def step_agent(
            agent_id: str,
            request: StepRequest,
            caller: str = Depends(self._verify_api_key),
        ):
            r"""Runs one step of synchronous agent response.

            Args:
                agent_id (str): The ID of the target agent.
                request (StepRequest): The input message.
                caller (str): The caller's key id (from the dependency).

            Returns:
                dict: The model response in serialized form.
            """
            agent = self._get_owned_agent(agent_id, caller)
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
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Unexpected error during step: {e!s}",
                )

        @router.post("/reset/{agent_id}")
        def reset_agent(
            agent_id: str,
            caller: str = Depends(self._verify_api_key),
        ):
            r"""Clears memory for a specific agent.

            Args:
                agent_id (str): The ID of the agent to reset.
                caller (str): The caller's key id (from the dependency).

            Returns:
                dict: A message confirming reset success.
            """
            agent = self._get_owned_agent(agent_id, caller)
            agent.reset()
            return {"message": f"Agent {agent_id} reset."}

        @router.get("/history/{agent_id}")
        def get_agent_chat_history(
            agent_id: str,
            caller: str = Depends(self._verify_api_key),
        ):
            r"""Returns the chat history of an agent.

            Args:
                agent_id (str): The ID of the agent to query.
                caller (str): The caller's key id (from the dependency).

            Returns:
                list: The list of conversation messages.
            """
            agent = self._get_owned_agent(agent_id, caller)
            return agent.chat_history

        # Register all routes to the main FastAPI app
        self.app.include_router(router)

    def get_app(self) -> FastAPI:
        r"""Returns the FastAPI app instance.

        Returns:
            FastAPI: The wrapped application object.
        """
        return self.app
