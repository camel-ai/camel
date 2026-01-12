import time
import uuid
from copy import deepcopy
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

from camel.logger import get_logger

logger = get_logger(__name__)

from tau2.agent.base import AgentError, BaseAgent, is_valid_agent_history_message
from tau2.agent.llm_agent import LLMSoloAgent
from tau2.data_model.message import (
    AssistantMessage,
    Message,
    MultiToolMessage,
    ToolMessage,
    UserMessage,
)
from tau2.data_model.simulation import SimulationRun, TerminationReason
from tau2.data_model.tasks import EnvFunctionCall, InitializationData, Task
from tau2.environment.environment import Environment, EnvironmentInfo
from tau2.user.base import BaseUser, UserError, is_valid_user_history_message
from tau2.user.user_simulator import DummyUser, UserSimulator, UserState
from tau2.utils.utils import format_time, get_now


class Role(str, Enum):
    AGENT = "agent"
    USER = "user"
    ENV = "env"


DEFAULT_FIRST_AGENT_MESSAGE = AssistantMessage(
    role="assistant", content="Hi! How can I help you today?", cost=0.0
)


class Orchestrator:
    """
    Orchestrator for the simulation given a task.
    Passes messages between the Agent, User, and Environment.

    Communication Protocol:
        The orchestrator manages message flow between three roles: AGENT, USER, and ENV(ironment).
        Messages are passed in a turn-based manner following these rules:

        Message Types:
            - AssistantMessage: Sent by the agent
            - UserMessage: Sent by the user
            - ToolMessage: Sent by the environment in response to tool calls
            - MultiToolMessage: Wraps multiple tool messages when multiple tool calls are made

        Message Content Rules:
            1. Messages must contain EITHER text content OR tool calls, never both
            2. Messages cannot be empty (must have either text or tool calls)
            3. Tool calls must be followed by corresponding tool messages from the environment

        Communication Flow:
            - AGENT -> USER: Agent sends text response to user
            - AGENT -> ENV: Agent makes tool call(s) to environment
            - USER -> AGENT: User sends text message to agent
            - USER -> ENV: User makes tool call(s) to environment
            - ENV -> AGENT: Environment returns tool results to agent (after agent's tool call)
            - ENV -> USER: Environment returns tool results to user (after user's tool call)

        Solo Mode:
            In solo mode, the user is replaced by a DummyUser and the agent operates autonomously:
            - Agent can ONLY send tool calls (no text messages to user)
            - Exception: Agent can send stop signal (###STOP###) to end simulation
            - Agent interacts exclusively with the environment until completion

        Termination:
            Simulation ends when:
            - Agent sends stop signal (###STOP###)
            - User sends stop signal
            - Maximum steps (max_steps) reached
            - Maximum errors (max_errors) reached
            - Communication protocol violation detected (if validate_communication=True)
    """

    def __init__(
        self,
        domain: str,
        agent: BaseAgent,
        user: BaseUser,
        environment: Environment,
        task: Task,
        max_steps: int = 100,
        max_errors: int = 10,
        seed: Optional[int] = None,
        solo_mode: bool = False,
        validate_communication: bool = False,
    ):
        """
        Initialize the Orchestrator for managing simulation between Agent, User, and Environment.

        Args:
            domain: The domain name of the simulation (e.g., 'airline', 'retail', 'telecom').
            agent: The agent instance that will respond to user requests and make tool calls.
            user: The user instance that interacts with the agent (can be UserSimulator or DummyUser).
            environment: The environment instance that handles tool execution and maintains state.
            task: The task specification containing initial state, goals, and evaluation criteria.
            max_steps: Maximum number of simulation steps before termination. Defaults to 100.
            max_errors: Maximum number of tool execution errors before termination. Defaults to 10.
            seed: Optional random seed for reproducibility of agent and user behavior. Defaults to None.
            solo_mode: If True, agent operates without user interaction (only tool calls allowed).
                      Requires agent to be LLMSoloAgent or GymAgent, and user to be DummyUser.
                      Defaults to False.
            validate_communication: If True, validates communication protocol rules (e.g., no mixed
                                   messages with both text and tool calls). Defaults to False.
        """

        self.domain = domain
        self.agent = agent
        self.user = user
        self.environment = environment
        self.task = task
        self.seed = seed
        self.solo_mode = solo_mode
        self.validate_communication = validate_communication
        self.agent_state: Optional[Any] = None
        self.user_state: Optional[UserState] = None
        self.trajectory: list[Message] = []
        self.max_steps = max_steps
        self.max_errors = max_errors
        self.step_count = 0
        self.done = False
        self.termination_reason: Optional[TerminationReason] = None
        self.num_errors = 0
        self.from_role: Optional[Role] = None
        self.to_role: Optional[Role] = None
        self.message: Optional[Message] = None

    def initialize(self):
        """
        Initialize the orchestrator.
        - If the tasks specifies an initial state, use it to initialize the environment.
        - Initialize the agent and user states.
        - Send the first message (default message from the agent to the user).
        """
        initial_state = self.task.initial_state
        initialization_data = (
            initial_state.initialization_data if initial_state is not None else None
        )
        initialization_actions = (
            initial_state.initialization_actions if initial_state is not None else None
        )
        message_history = (
            deepcopy(initial_state.message_history)
            if initial_state is not None and initial_state.message_history is not None
            else []
        )
        for msg in message_history:
            msg.turn_idx = None

        # Add timestamps to the message history
        message_history = self._add_timestamps(message_history)

        if self.solo_mode:
            assert self.environment.solo_mode, "Environment should be in solo mode"
            assert (
                isinstance(self.agent, LLMSoloAgent)
                or self.agent.__class__.__name__ == "GymAgent"
            ), "Agent must be a LLMSoloAgent or GymAgent in solo mode"
            assert isinstance(
                self.user, DummyUser
            ), "User must be a DummyUser in solo mode"

        # Initialize Environment state
        self._initialize_environment(
            initialization_data=initialization_data,
            initialization_actions=initialization_actions,
            message_history=message_history,
        )

        # Set seeds for the agent, user
        if self.seed is not None:
            self.agent.set_seed(self.seed)
            self.user.set_seed(self.seed)

        # Initialize the agent and user states
        if len(message_history) > 0:
            self.validate_message_history(message_history)

            last_message = message_history[-1]
            # Last message is an assistant message
            if isinstance(last_message, AssistantMessage):
                self.from_role = Role.AGENT
                if not last_message.is_tool_call():  # Last message is for the user
                    self.to_role = Role.USER
                else:  # Last message is for the environment
                    self.to_role = Role.ENV
                self.agent_state = self.agent.get_init_state(
                    message_history=[
                        msg
                        for msg in message_history
                        if is_valid_agent_history_message(msg)
                    ]
                )
                self.user_state = self.user.get_init_state(
                    message_history=[
                        msg
                        for msg in message_history[:-1]
                        if is_valid_user_history_message(msg)
                    ]
                )
                self.message = last_message
                if self.agent.is_stop(last_message):
                    self.done = True
                    self.termination_reason = TerminationReason.AGENT_STOP
            # Last message is a user message
            elif isinstance(last_message, UserMessage):
                self.from_role = Role.USER
                if not last_message.is_tool_call():  # Last message is for the agent
                    self.to_role = Role.AGENT
                else:  # Last message is for the environment
                    self.to_role = Role.ENV
                self.user_state = self.user.get_init_state(
                    message_history=[
                        msg
                        for msg in message_history
                        if is_valid_user_history_message(msg)
                    ]
                )
                self.agent_state = self.agent.get_init_state(
                    message_history=[
                        msg
                        for msg in message_history[:-1]
                        if is_valid_agent_history_message(msg)
                    ]
                )
                self.message = last_message
                self.done = UserSimulator.is_stop(last_message)
                if self.done:
                    self.termination_reason = TerminationReason.USER_STOP
            # Last message is a tool message
            elif isinstance(last_message, ToolMessage):
                self.from_role = Role.ENV
                if last_message.requestor == "assistant":
                    self.to_role = Role.AGENT
                    self.agent_state = self.agent.get_init_state(
                        message_history=[
                            msg
                            for msg in message_history[:-1]
                            if is_valid_agent_history_message(msg)
                        ]
                    )
                    self.user_state = self.user.get_init_state(
                        message_history=[
                            msg
                            for msg in message_history
                            if is_valid_user_history_message(msg)
                        ]
                    )
                else:
                    self.to_role = Role.USER
                    self.agent_state = self.agent.get_init_state(
                        message_history=[
                            msg
                            for msg in message_history
                            if is_valid_agent_history_message(msg)
                        ]
                    )
                    self.user_state = self.user.get_init_state(
                        message_history=[
                            msg
                            for msg in message_history[:-1]
                            if is_valid_user_history_message(msg)
                        ]
                    )
                self.message = last_message
            else:
                raise ValueError(
                    f"Last message should be of type AssistantMessage, UserMessage, or ToolMessage, got {type(last_message)}"
                )
            self.trajectory = message_history
        else:
            self.user_state = self.user.get_init_state()
            if not self.solo_mode:
                first_message = deepcopy(DEFAULT_FIRST_AGENT_MESSAGE)
                first_message.timestamp = get_now()
                self.agent_state = self.agent.get_init_state(
                    message_history=[first_message]
                )
                self.trajectory = [first_message]
                self.message = first_message
                self.from_role = Role.AGENT
                self.to_role = Role.USER
            else:
                self.agent_state = self.agent.get_init_state()
                first_message, self.agent_state = self.agent.generate_next_message(
                    None, self.agent_state
                )
                self.trajectory = [first_message]
                self.message = first_message
                # In solo mode, there is no user, so if the message is not a tool call, then we end and report an agent error
                if not first_message.is_tool_call():
                    self.from_role = Role.AGENT
                    self.to_role = Role.USER
                    self.done = True
                    if self.agent.is_stop(first_message):
                        # If the agent is stopping (###STOP###)
                        self.termination_reason = TerminationReason.AGENT_STOP
                    else:
                        self.termination_reason = TerminationReason.AGENT_ERROR
                else:
                    self.from_role = Role.AGENT
                    self.to_role = Role.ENV
                    self.done = self.agent.is_stop(first_message)
                    if self.done:
                        self.to_role = (
                            Role.USER
                        )  # FIXIT: For now, we assume last message cannot be to the environment
                        self.termination_reason = TerminationReason.AGENT_STOP
        if self.validate_communication:
            self.check_communication_error()
        self.environment.sync_tools()

    def check_communication_error(self) -> None:
        """
        Check the orchestrator state for communication errors and handle them appropriately.

        Communication errors occur when agents or users violate the communication protocol rules:
        - Empty messages (no text content and no tool calls)
        - Mixed messages (both text content and tool calls in the same message)
        - Solo mode violations (agents sending text content instead of tool calls)

        When a communication error is detected:
        - Sets `self.done = True` to terminate the simulation
        - Sets `self.termination_reason` to either `AGENT_ERROR` or `USER_ERROR`
        - Re-raises any other exceptions that are not communication-related
        """
        try:
            self._check_communication_error()
        except AgentError:
            self.done = True
            self.termination_reason = TerminationReason.AGENT_ERROR
        except UserError:
            self.done = True
            self.termination_reason = TerminationReason.USER_ERROR
        except Exception:
            # Re-raise all other exceptions
            raise

    def _check_communication_error(self) -> None:
        """
        Check the orchestrator state for communication protocol violations.

        Validates that messages follow the communication rules:
        1. Messages must have either text content OR tool calls, not both
        2. Messages cannot be empty (no text content and no tool calls)
        3. In solo mode, agents can only send tool calls (except for stop messages)

        Raises:
            AgentError: When the agent violates communication rules
            UserError: When the user violates communication rules
            ValueError: When from_role is invalid
        """
        if self.from_role == Role.ENV:
            return
        if self.from_role == Role.USER:
            exception_type = UserError
        elif self.from_role == Role.AGENT:
            exception_type = AgentError
        else:
            raise ValueError(f"Invalid from role: {self.from_role}")
        # Check if the message is empty
        if not self.message.is_tool_call() and not self.message.has_text_content():
            raise exception_type(
                f"{self.from_role.value} sent an empty message. {self.message}"
            )
        # Check if the message has both text content and tool calls
        if self.message.is_tool_call() and self.message.has_text_content():
            raise exception_type(
                f"{self.from_role.value} sent both text content and tool calls. {self.message}"
            )

        # Check if the agent is allowed to send a message to the user
        if self.from_role == Role.AGENT and self.solo_mode:
            if self.message.has_text_content() and not self.agent.is_stop(self.message):
                raise exception_type(
                    f"{self.from_role.value} can only send tool calls. {self.message}"
                )

    def run(self) -> SimulationRun:
        """
        Run the simulation.

        Returns:
            SimulationRun: The simulation run.
        """
        start_time = get_now()
        start = time.perf_counter()
        self.initialize()
        while not self.done:
            self.step()
            # Checking for maximum steps and errors only if the last message is not to the environment
            if self.to_role == Role.ENV:
                continue
            if self.step_count >= self.max_steps and self.to_role != Role.ENV:
                self.done = True
                self.termination_reason = TerminationReason.MAX_STEPS
            if self.num_errors >= self.max_errors and self.to_role != Role.ENV:
                self.done = True
                self.termination_reason = TerminationReason.TOO_MANY_ERRORS
        # Send stop signal to the agent, user, and environment
        has_error = self.termination_reason in [
            TerminationReason.USER_ERROR,
            TerminationReason.AGENT_ERROR,
        ]
        last_msg_to_agent = None
        last_msg_to_user = None
        if self.to_role == Role.AGENT:
            last_msg_to_agent = self.message
        elif self.to_role == Role.USER:
            last_msg_to_user = self.message
        elif self.to_role == Role.ENV and not has_error:
            raise ValueError(
                "Environment should not receive the last message. Last message: "
                + str(self.message)
            )
        self.agent.stop(last_msg_to_agent, self.agent_state)
        self.user.stop(last_msg_to_user, self.user_state)

        # Wrap up the simulation
        duration = time.perf_counter() - start
        messages = self.get_trajectory()
        agent_usage = self._get_token_usage_summary(self.agent)
        user_usage = self._get_token_usage_summary(self.user)

        simulation_run = SimulationRun(
            id=str(uuid.uuid4()),
            task_id=self.task.id,
            start_time=start_time,
            end_time=get_now(),
            duration=duration,
            termination_reason=self.termination_reason.value,
            reward_info=None,
            user_cost=self._extract_total_tokens(user_usage),
            agent_cost=self._extract_total_tokens(agent_usage),
            agent_token_usage=agent_usage,
            user_token_usage=user_usage,
            messages=messages,
            seed=self.seed,
        )
        return simulation_run

    def step(self):
        """
        Perform one step of the simulation.
        Sends self.message from self.from_role to self.to_role
        This can either be a message from agent to user/environment, environment to agent, or user to agent
        Updates self.trajectory
        """
        if self.done:
            raise ValueError("Simulation is done")
        logger.debug(
            f"Step {self.step_count}. Sending message from {self.from_role} to {self.to_role}"
        )
        logger.debug(
            f"Step {self.step_count}.\nFrom role: {self.from_role}\nTo role: {self.to_role}\nMessage: {self.message}"
        )
        # AGENT/ENV -> USER
        if self.from_role in [Role.AGENT, Role.ENV] and self.to_role == Role.USER:
            user_msg, self.user_state = self.user.generate_next_message(
                self.message, self.user_state
            )
            user_msg.validate()
            if UserSimulator.is_stop(user_msg):
                self.done = True
                self.termination_reason = TerminationReason.USER_STOP
            self.trajectory.append(user_msg)
            self.message = user_msg
            self.from_role = Role.USER
            if user_msg.is_tool_call():
                self.to_role = Role.ENV
            else:
                self.to_role = Role.AGENT
        # USER/ENV -> AGENT
        elif (
            self.from_role == Role.USER or self.from_role == Role.ENV
        ) and self.to_role == Role.AGENT:
            agent_msg, self.agent_state = self.agent.generate_next_message(
                self.message, self.agent_state
            )
            agent_msg.validate()
            if self.agent.is_stop(agent_msg):
                self.done = True
                self.termination_reason = TerminationReason.AGENT_STOP
            self.trajectory.append(agent_msg)
            self.message = agent_msg
            self.from_role = Role.AGENT
            if agent_msg.is_tool_call():
                self.to_role = Role.ENV
            else:
                self.to_role = Role.USER
                # In solo mode, there is no user, so if the message is not a tool call and not a stop, then we end and report an agent error
                if self.solo_mode and not self.agent.is_stop(agent_msg):
                    self.done = True
                    self.termination_reason = TerminationReason.AGENT_ERROR
        # AGENT/USER -> ENV
        elif self.from_role in [Role.AGENT, Role.USER] and self.to_role == Role.ENV:
            if not self.message.is_tool_call():
                raise ValueError("Agent or User should send tool call to environment")
            tool_msgs = []
            for tool_call in self.message.tool_calls:
                tool_msg = self.environment.get_response(tool_call)
                if tool_msg.error:
                    self.num_errors += 1
                tool_msgs.append(tool_msg)
            assert len(self.message.tool_calls) == len(
                tool_msgs
            ), "Number of tool calls and tool messages should be the same"
            self.trajectory.extend(tool_msgs)
            if (
                len(tool_msgs) > 1
            ):  # Packaging multiple tool messages into a MultiToolMessage
                self.message = MultiToolMessage(
                    role="tool",
                    tool_messages=tool_msgs,
                )
            else:
                self.message = tool_msgs[0]
            self.to_role = self.from_role
            self.from_role = Role.ENV
        else:
            raise ValueError(
                f"Invalid role combination. From role: {self.from_role}, To role: {self.to_role}"
            )
        if self.validate_communication:
            self.check_communication_error()
        self.step_count += 1
        self.environment.sync_tools()

    @staticmethod
    def _get_token_usage_summary(participant) -> Optional[dict[str, int]]:
        getter = getattr(participant, "get_token_usage", None)
        if callable(getter):
            usage = getter()
            if usage:
                return usage
        return None

    @staticmethod
    def _extract_total_tokens(
        usage: Optional[dict[str, int]]
    ) -> Optional[float]:
        if not usage:
            return None
        total = usage.get("total_tokens")
        if total is not None:
            return float(total)
        prompt = usage.get("prompt_tokens")
        completion = usage.get("completion_tokens")
        if prompt is None and completion is None:
            return None
        return float((prompt or 0) + (completion or 0))

    def get_trajectory(self) -> list[Message]:
        """
        Get the trajectory of the simulation.
        The trajectory is sorted by timestamp, turn_idx are added to messages, trajectory is returned.
        """
        messages: list[Message] = sorted(
            deepcopy(self.trajectory),
            key=lambda x: x.timestamp,
        )
        trajectory = []
        for i, msg in enumerate(messages):
            msg = deepcopy(msg)
            msg.turn_idx = i
            trajectory.append(msg)
        return trajectory

    @classmethod
    def validate_message_history(cls, message_history: list[Message]):
        """
        Validate a message history.
            - Should only contain AssistantMessage, UserMessage, ToolMessage
            - All assistant/user messages should be either to user or tool call, not both.
            - If n tool calls are made by a participant, exactly n tool messages should follow with requestor matching the participant.
        """
        num_expected_tool_messages = 0
        requestor = None
        for msg in message_history:
            if isinstance(msg, AssistantMessage) or isinstance(msg, UserMessage):
                msg.validate()
                if msg.is_tool_call():
                    if num_expected_tool_messages > 0:
                        raise ValueError(
                            f"{num_expected_tool_messages} tool messages are missing. Got {msg.role} message."
                        )
                    num_expected_tool_messages = len(msg.tool_calls)
                    requestor = msg.role
                else:
                    num_expected_tool_messages == 0
                    requestor = None
            elif isinstance(msg, ToolMessage):
                if num_expected_tool_messages == 0 or requestor is None:
                    raise ValueError("No tool messages expected.")
                if requestor != msg.requestor:
                    raise ValueError(
                        f"Got tool message from {msg.requestor}, expected {requestor}."
                    )
                num_expected_tool_messages -= 1
            else:
                raise ValueError(f"Invalid message type: {type(msg)}")

    def _initialize_environment(
        self,
        initialization_data: Optional[InitializationData],
        initialization_actions: Optional[list[EnvFunctionCall]],
        message_history: list[Message],
    ):
        """
        Initialize the environment.
        """
        self.environment.set_state(
            initialization_data=initialization_data,
            initialization_actions=initialization_actions,
            message_history=message_history,
        )

    def _get_environment_info(self) -> EnvironmentInfo:
        """
        Get the environment info.
        """
        return self.environment.get_info()

    def _count_errors(self, message_history: list[Message]) -> int:
        """
        Count the number of errors in the message history.
        """
        return sum(
            1 for msg in message_history if isinstance(msg, ToolMessage) and msg.error
        )

    def _add_timestamps(
        self, message_history: list[Message]
    ) -> list[tuple[str, Message]]:
        """
        Add timestamps to the message history.
        This is used to sort the messages by timestamp.
        """
        time_offset = datetime.now() - timedelta(seconds=len(message_history))
        for i, msg in enumerate(message_history):
            msg.timestamp = format_time(time_offset + timedelta(seconds=i))
        return message_history
