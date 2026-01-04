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

import inspect
from pathlib import Path
from typing import TYPE_CHECKING, Callable, List, Literal, Optional, TypeVar

from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.utils import AgentOpsMeta, Constants, with_timeout

if TYPE_CHECKING:
    from camel.agents import ChatAgent

F = TypeVar('F', bound=Callable)

logger = get_logger(__name__)


def manual_timeout(func: F) -> F:
    r"""Decorator to mark a function as having manual timeout handling.

    Use this decorator on toolkit methods that manage their own timeout logic
    internally but don't have a `timeout` parameter in their signature.
    This prevents the automatic `with_timeout` wrapper from being applied
    by `BaseToolkit`.

    Note:
        Methods with a `timeout` parameter in their signature are
        automatically detected and skipped, so they don't need this
        decorator.

    Args:
        func (F): The function to mark as having manual timeout handling.

    Returns:
        F: The same function with `_manual_timeout` attribute set to True.

    Example:
        >>> class MyToolkit(BaseToolkit):
        ...     @manual_timeout
        ...     def long_running_task(self, max_wait: int = 30):
        ...         # This method manages timeout internally using max_wait
        ...         # but doesn't use 'timeout' as the parameter name
        ...         pass
    """
    func._manual_timeout = True  # type: ignore[attr-defined]
    return func


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
                if getattr(attr_value, '_manual_timeout', False):
                    continue
                # Auto-detect: skip methods that have 'timeout' in signature
                try:
                    sig = inspect.signature(attr_value)
                    if 'timeout' in sig.parameters:
                        continue
                except (ValueError, TypeError):
                    # Some built-in functions don't have signatures
                    pass
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

    def to_skill(
        self,
        path: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        instructions: Optional[str] = None,
    ) -> Path:
        r"""Export this toolkit instance as a Claude Agent Skill.

        Generates a skill directory containing SKILL.md and executable Python
        scripts for each tool. The skill follows the Claude Agent Skills
        specification and includes automatic state management.

        Args:
            path (str): The directory path where the skill will be created.
                The skill folder will be created inside this path.
            name (Optional[str]): The skill name (lowercase letters, numbers,
                and hyphens only, max 64 chars). If not provided, derived
                from the toolkit class name.
            description (Optional[str]): The skill description (max 1024
                chars). If not provided, extracted from the toolkit's
                docstring.
            instructions (Optional[str]): Custom instructions for the skill.
                If not provided, auto-generated from tool docstrings.

        Returns:
            Path: The path to the created skill directory.

        Example:
            >>> from camel.toolkits import MathToolkit
            >>> toolkit = MathToolkit()
            >>> skill_path = toolkit.to_skill(
            ...     path="./skills",
            ...     name="math",
            ...     description="Perform mathematical operations",
            ... )
            >>> print(skill_path)
            PosixPath('skills/math')
        """
        from camel.toolkits.skill_generator import SkillGenerator

        generator = SkillGenerator(self)
        return generator.generate(
            path=path,
            name=name,
            description=description,
            instructions=instructions,
        )


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
