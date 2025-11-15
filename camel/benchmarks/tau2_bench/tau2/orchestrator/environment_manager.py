import uuid
from typing import Dict, Optional

from fastapi import FastAPI
from pydantic import BaseModel

from tau2.data_model.message import AssistantMessage, Message, ToolCall, ToolMessage
from tau2.data_model.tasks import Action, EnvFunctionCall, InitializationData
from tau2.environment.environment import Environment, EnvironmentInfo
from tau2.orchestrator.utils import is_valid_environment_message
from tau2.registry import registry


class StartEnvironmentRequest(BaseModel):
    domain: str
    env_id: Optional[str] = None


class StatusResponse(BaseModel):
    status: str


class EnvironmentResponse(BaseModel):
    env_id: str


class SetStateRequest(BaseModel):
    actions: list[Action]
    message_history: list[Message]


class GetTrajectoryResponse(BaseModel):
    trajectory: list[Message]


class EnvironmentManager:
    """
    A FastAPI server that manages multiple environment instances and exposes their tools as HTTP endpoints.

    The EnvironmentManager provides HTTP endpoints for creating, controlling, and interacting with multiple
    environment instances. Each environment is assigned a unique ID and has its own set of tool endpoints.

    HTTP Endpoints:
        - POST /start_environment/
            Start a new environment of the specified domain type
            Body: {
                "domain_name": str,
                "env_id": Optional[str]
            }
            Returns: {"env_id": "<uuid>"}

        - POST /{env_id}/stop_environment
            Stop and cleanup the specified environment
            Returns: {"status": "success"}

        - POST /{env_id}/set_state
            Set the state of an environment by providing actions and message history
            Body: {
                "actions": [list of Action objects],
                "message_history": [list of Message objects]
            }
            Returns: {"status": "success"}

        - GET /{env_id}/trajectory
            Get the message history for the specified environment
            Returns: {"trajectory": [list of Message objects]}

        - GET /{env_id}/info
            Get information about the environment including available tools
            Returns: Environment info and tool specifications

        - POST /{env_id}/tools/{tool_name}
            Execute a tool in the specified environment
            Body: {
                "tool_name": str,
                "tool_args": dict
            }
            Returns: Tool execution results as a ToolMessage

        - GET /status
            Health check endpoint
            Returns: {"status": "ok"}

    Example Usage:
        ```python
        # Start a new environment
        POST /start_environment
        {
            "domain_name": "mock"
        }
        > {"env_id": "1234-5678-90ab"}

        # Set environment state
        POST /1234-5678-90ab/set_state
        {
            "actions": [...],
            "message_history": [...]
        }
        > {"status": "success"}

        # Call a tool in the environment
        POST /1234-5678-90ab/tools/get_users
        {
            "tool_name": "get_users",
            "tool_args": {}
        }
        > {"role": "tool", ...}

        # Get environment history
        GET /1234-5678-90ab/trajectory
        > {"trajectory": [...]}

        # Stop the environment when done
        POST /1234-5678-90ab/stop_environment
        ```

    Args:
        host (str, optional): The host address to bind the server to. Defaults to "localhost".
        port (int, optional): The port number to run the server on. Defaults to 8000.

    Attributes:
        environments (Dict[str, Environment]): Dictionary mapping environment IDs to Environment instances
        trajectories (Dict[str, list[Message]]): Dictionary storing message histories for each environment
        routes (Dict[str, list]): Dictionary mapping environment IDs to their FastAPI route handlers
        app (FastAPI): The FastAPI application instance
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8000,
    ):
        self.environments: Dict[str, Environment] = {}
        self.host = host
        self.port = port
        self.app = FastAPI()
        self.routes: Dict[str, list] = {}
        self.trajectories: Dict[str, list[ToolMessage | AssistantMessage]] = {}

        # Add routes
        @self.app.get("/status")
        async def status():
            """Health check endpoint"""
            return {"status": "ok"}

        @self.app.post("/start_environment")
        async def start_env(request: StartEnvironmentRequest) -> EnvironmentResponse:
            env_id = self.start_environment(
                domain=request.domain, env_id=request.env_id
            )
            return EnvironmentResponse(env_id=env_id)

        @self.app.post("/{env_id}/set_state")
        async def set_state(env_id: str, request: SetStateRequest) -> StatusResponse:
            self.set_environment_state(env_id, request.actions, request.message_history)
            return StatusResponse(status="success")

        @self.app.post("/{env_id}/stop_environment")
        async def stop_env(env_id: str) -> StatusResponse:
            self.stop_environment(env_id)
            return StatusResponse(status="success")

        @self.app.get("/{env_id}/trajectory")
        async def get_trajectory(env_id: str) -> GetTrajectoryResponse:
            return GetTrajectoryResponse(trajectory=self.get_trajectory(env_id))

        @self.app.get("/{env_id}/info")
        async def get_info(env_id: str) -> EnvironmentInfo:
            return self.get_environment_info(env_id)

        @self.app.post("/{env_id}/tools/{tool_name}")
        async def execute_tool(
            env_id: str, tool_name: str, request: ToolCall
        ) -> ToolMessage:
            return self.execute_tool(env_id=env_id, tool_call=request)

    def get_environment_id(self) -> str:
        """
        Get a unique ID for the environment.
        """
        return str(uuid.uuid4())

    def get_environment_info(self, env_id: str) -> EnvironmentInfo:
        """
        Get information about the environment.
        """
        return self.environments[env_id].get_info()

    def start_environment(self, domain: str, env_id: Optional[str] = None):
        """
        Start a new environment.
        """
        global registry
        if env_id is None:
            env_id = self.get_environment_id()
        if env_id in self.environments:
            raise ValueError(f"Environment {env_id} already exists")
        self.environments[env_id] = registry.get_env_constructor(domain)()
        self.trajectories[env_id] = []
        return env_id

    def set_environment_state(
        self,
        env_id: str,
        initialization_data: InitializationData,
        initialization_actions: list[EnvFunctionCall],
        message_history: list[tuple[str, Message]],
    ):
        """
        Set the state of an environment.
        """

        self.environments[env_id].set_state(
            initialization_data, initialization_actions, message_history
        )
        self.trajectories[env_id] = [
            msg for msg in message_history if is_valid_environment_message(msg)
        ]

    def stop_environment(self, env_id: str):
        """
        Stop an environment and remove its routes.
        """
        if env_id in self.routes:
            # Get the router instance
            router = self.app.router
            # Filter out the routes we want to remove
            router.routes = [
                route for route in router.routes if route not in self.routes[env_id]
            ]
            del self.routes[env_id]

        if env_id in self.environments:
            del self.environments[env_id]
        if env_id in self.trajectories:
            del self.trajectories[env_id]

    def get_trajectory(self, env_id: str) -> list[Message]:
        """
        Get the trajectory for an environment.
        """
        return self.trajectories[env_id]

    def execute_tool(self, env_id: str, tool_call: ToolCall):
        """
        Execute a tool in an environment.
        """
        assert isinstance(tool_call, ToolCall)
        assistant_message = AssistantMessage(
            role="assistant",
            tool_calls=[tool_call],
        )
        self.trajectories[env_id].append(assistant_message)
        tool_message = self.environments[env_id].get_response(tool_call)
        self.trajectories[env_id].append(tool_message)
        return tool_message

    def run(self):
        """Runs the server"""
        import uvicorn

        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info",  # Add logging to help debug startup issues
        )
        server = uvicorn.Server(config)
        return server.serve()
