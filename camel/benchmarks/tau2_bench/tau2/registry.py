import json
from typing import Callable, Dict, Optional, Type

from loguru import logger
from pydantic import BaseModel

from tau2.agent.base import BaseAgent
from tau2.agent.llm_agent import LLMAgent, LLMGTAgent, LLMSoloAgent
from tau2.data_model.tasks import Task
from tau2.domains.airline.environment import (
    get_environment as airline_domain_get_environment,
)
from tau2.domains.airline.environment import get_tasks as airline_domain_get_tasks
from tau2.domains.airline.environment import (
    get_tasks_split as airline_domain_get_tasks_split,
)
from tau2.domains.mock.environment import get_environment as mock_domain_get_environment
from tau2.domains.mock.environment import get_tasks as mock_domain_get_tasks
from tau2.domains.retail.environment import (
    get_environment as retail_domain_get_environment,
)
from tau2.domains.retail.environment import get_tasks as retail_domain_get_tasks
from tau2.domains.retail.environment import (
    get_tasks_split as retail_domain_get_tasks_split,
)
from tau2.domains.telecom.environment import (
    get_environment_manual_policy as telecom_domain_get_environment_manual_policy,
)
from tau2.domains.telecom.environment import (
    get_environment_workflow_policy as telecom_domain_get_environment_workflow_policy,
)
from tau2.domains.telecom.environment import get_tasks as telecom_domain_get_tasks
from tau2.domains.telecom.environment import (
    get_tasks_full as telecom_domain_get_tasks_full,
)
from tau2.domains.telecom.environment import (
    get_tasks_small as telecom_domain_get_tasks_small,
)
from tau2.domains.telecom.environment import (
    get_tasks_split as telecom_domain_get_tasks_split,
)
from tau2.environment.environment import Environment
from tau2.user.base import BaseUser
from tau2.user.user_simulator import DummyUser, UserSimulator


class RegistryInfo(BaseModel):
    """Options for the registry"""

    domains: list[str]
    agents: list[str]
    users: list[str]
    task_sets: list[str]


class Registry:
    """Registry for Users, Agents, and Domains"""

    def __init__(self):
        self._users: Dict[str, Type[BaseUser]] = {}
        self._agents: Dict[str, Type[BaseAgent]] = {}
        self._domains: Dict[str, Callable[[], Environment]] = {}
        self._tasks: Dict[str, Callable[[Optional[str]], list[Task]]] = {}
        self._task_splits: Dict[str, Callable[[], dict[str, list[str]]]] = {}

    def register_user(
        self,
        user_constructor: type[BaseUser],
        name: Optional[str] = None,
    ):
        """Decorator to register a new User implementation"""
        try:
            if not issubclass(user_constructor, BaseUser):
                raise TypeError(f"{user_constructor.__name__} must implement UserBase")
            key = name or user_constructor.__name__
            if key in self._users:
                raise ValueError(f"User {key} already registered")
            self._users[key] = user_constructor
        except Exception as e:
            logger.error(f"Error registering user {name}: {str(e)}")
            raise

    def register_agent(
        self,
        agent_constructor: type[BaseAgent],
        name: Optional[str] = None,
    ):
        """Decorator to register a new Agent implementation"""
        if not issubclass(agent_constructor, BaseAgent):
            raise TypeError(f"{agent_constructor.__name__} must implement AgentBase")
        key = name or agent_constructor.__name__
        if key in self._agents:
            raise ValueError(f"Agent {key} already registered")
        self._agents[key] = agent_constructor

    def register_domain(
        self,
        get_environment: Callable[[], Environment],
        name: str,
    ):
        """Register a new Domain implementation"""
        try:
            if name in self._domains:
                raise ValueError(f"Domain {name} already registered")
            self._domains[name] = get_environment
        except Exception as e:
            logger.error(f"Error registering domain {name}: {str(e)}")
            raise

    def register_tasks(
        self,
        get_tasks: Callable[[Optional[str]], list[Task]],
        name: str,
        get_task_splits: Optional[Callable[[], dict[str, list[str]]]] = None,
    ):
        """Register a new Domain implementation.
        Args:
            get_tasks: A function that returns a list of tasks for the domain. If a task split name is provided, it returns the tasks for that split.
            name: The name of the domain.
            get_task_splits: A function that returns a dictionary of task splits for the domain.
        """
        try:
            if name in self._tasks:
                raise ValueError(f"Tasks {name} already registered")
            self._tasks[name] = get_tasks
            if get_task_splits is not None:
                self._task_splits[name] = get_task_splits
        except Exception as e:
            logger.error(f"Error registering tasks {name}: {str(e)}")
            raise

    def get_user_constructor(self, name: str) -> Type[BaseUser]:
        """Get a registered User implementation by name"""
        if name not in self._users:
            raise KeyError(f"User {name} not found in registry")
        return self._users[name]

    def get_agent_constructor(self, name: str) -> Type[BaseAgent]:
        """Get a registered Agent implementation by name"""
        if name not in self._agents:
            raise KeyError(f"Agent {name} not found in registry")
        return self._agents[name]

    def get_env_constructor(self, name: str) -> Callable[[], Environment]:
        """Get a registered Domain by name"""
        if name not in self._domains:
            raise KeyError(f"Domain {name} not found in registry")
        return self._domains[name]

    def get_tasks_loader(self, name: str) -> Callable[[Optional[str]], list[Task]]:
        """Get a registered Task Set by name.
        Args:
            name: The name of the task set.
        Returns:
            A function that takes an optional task_split_name parameter and returns the corresponding tasks.
            Can be called as: func() or func(task_split_name="base") or func("base").
        """
        if name not in self._tasks:
            raise KeyError(f"Task Set {name} not found in registry")
        return self._tasks[name]

    def get_task_splits_loader(
        self, name: str
    ) -> Optional[Callable[[], dict[str, list[str]]]]:
        """Get a registered task split dict loader."""
        if name not in self._task_splits:
            return None
        return self._task_splits[name]

    def get_users(self) -> list[str]:
        """Get all registered Users"""
        return list(self._users.keys())

    def get_agents(self) -> list[str]:
        """Get all registered Agents"""
        return list(self._agents.keys())

    def get_domains(self) -> list[str]:
        """Get all registered Domains"""
        return list(self._domains.keys())

    def get_task_sets(self) -> list[str]:
        """Get all registered Task Sets"""
        return list(self._tasks.keys())

    def get_info(self) -> RegistryInfo:
        """
        Returns information about the registry.
        """
        try:
            info = RegistryInfo(
                users=self.get_users(),
                agents=self.get_agents(),
                domains=self.get_domains(),
                task_sets=self.get_task_sets(),
            )
            return info
        except Exception as e:
            logger.error(f"Error getting registry info: {str(e)}")
            raise


# Create a global registry instance
try:
    registry = Registry()
    logger.debug("Registering default components...")
    registry.register_user(UserSimulator, "user_simulator")
    registry.register_user(DummyUser, "dummy_user")
    registry.register_agent(LLMAgent, "llm_agent")
    registry.register_agent(LLMGTAgent, "llm_agent_gt")
    registry.register_agent(LLMSoloAgent, "llm_agent_solo")

    registry.register_domain(mock_domain_get_environment, "mock")
    registry.register_tasks(mock_domain_get_tasks, "mock")

    registry.register_domain(airline_domain_get_environment, "airline")
    registry.register_tasks(
        airline_domain_get_tasks,
        "airline",
        get_task_splits=airline_domain_get_tasks_split,
    )

    registry.register_domain(retail_domain_get_environment, "retail")
    registry.register_tasks(
        retail_domain_get_tasks,
        "retail",
        get_task_splits=retail_domain_get_tasks_split,
    )

    registry.register_domain(telecom_domain_get_environment_manual_policy, "telecom")
    registry.register_domain(
        telecom_domain_get_environment_workflow_policy, "telecom-workflow"
    )
    registry.register_tasks(telecom_domain_get_tasks_full, "telecom_full")
    registry.register_tasks(telecom_domain_get_tasks_small, "telecom_small")
    registry.register_tasks(
        telecom_domain_get_tasks,
        "telecom",
        get_task_splits=telecom_domain_get_tasks_split,
    )
    registry.register_tasks(
        telecom_domain_get_tasks,
        "telecom-workflow",
        get_task_splits=telecom_domain_get_tasks_split,
    )

    logger.debug(
        f"Default components registered successfully. Registry info: {json.dumps(registry.get_info().model_dump(), indent=2)}"
    )
except Exception as e:
    logger.error(f"Error initializing registry: {str(e)}")
