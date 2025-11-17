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

from typing import TYPE_CHECKING, List, Literal, Optional

from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.utils import AgentOpsMeta, Constants, with_timeout

if TYPE_CHECKING:
    from camel.agents import ChatAgent


logger = get_logger(__name__)


class BaseToolkit(metaclass=AgentOpsMeta):
    r"""Base class for toolkits.

    Args:
        timeout (Optional[float]): The timeout for the toolkit.
    """

    from mcp.server import FastMCP

    mcp: FastMCP
    timeout: Optional[float] = Constants.TIMEOUT_THRESHOLD

    def __init__(self, timeout: Optional[float] = Constants.TIMEOUT_THRESHOLD):
        # check if timeout is a positive number
        if timeout is not None and timeout <= 0:
            raise ValueError("Timeout must be a positive number.")
        self.timeout = timeout

    # Add timeout to all callable methods in the toolkit
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        for attr_name, attr_value in cls.__dict__.items():
            if callable(attr_value) and not attr_name.startswith("__"):
                # Skip methods that have manual timeout management
                if not getattr(attr_value, '_manual_timeout', False):
                    setattr(cls, attr_name, with_timeout(attr_value))

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        raise NotImplementedError("Subclasses must implement this method.")

    def run_mcp_server(
        self, mode: Literal["stdio", "sse", "streamable-http"]
    ) -> None:
        r"""Run the MCP server in the specified mode.

        Args:
            mode (Literal["stdio", "sse", "streamable-http"]): The mode to run
                the MCP server in.
        """
        self.mcp.run(mode)


class RegisteredAgentToolkit:
    r"""Mixin class for toolkits that need to register a ChatAgent.

    This mixin provides a standard interface for toolkits that require
    a reference to a ChatAgent instance. The ChatAgent will check if a
    toolkit has this mixin and automatically register itself.
    """

    def __init__(self):
        self._agent: Optional["ChatAgent"] = None

    @property
    def agent(self) -> Optional["ChatAgent"]:
        r"""Get the registered ChatAgent instance.

        Returns:
            Optional[ChatAgent]: The registered agent, or None if not
                registered.

        Note:
            If None is returned, it means the toolkit has not been registered
            with a ChatAgent yet. Make sure to pass this toolkit to a ChatAgent
            via the toolkits parameter during initialization.
        """
        if self._agent is None:
            logger.warning(
                f"{self.__class__.__name__} does not have a "
                f"registered ChatAgent. "
                f"Please ensure this toolkit is passed to a ChatAgent via the "
                f"'toolkits_to_register_agent' parameter during ChatAgent "
                f"initialization if you want to use the tools that require a "
                f"registered agent."
            )
        return self._agent

    def register_agent(self, agent: "ChatAgent") -> None:
        r"""Register a ChatAgent with this toolkit.

        This method allows registering an agent after initialization. The
        ChatAgent will automatically call this method if the toolkit to
        register inherits from RegisteredAgentToolkit.

        Args:
            agent (ChatAgent): The ChatAgent instance to register.
        """
        self._agent = agent
        logger.info(f"Agent registered with {self.__class__.__name__}")
