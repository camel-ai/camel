# Copyright Sierra

import json
import textwrap
import uuid
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field
from typing_extensions import Annotated

from tau2.data_model.message import Message, ToolCall, ToolRequestor


class StructuredUserInstructions(BaseModel):
    """
    User instructions. This information defines the specific situation the user is in and the tasks they are trying to complete.
    """

    domain: Annotated[str, Field(description="The domain of the task.")]
    reason_for_call: Annotated[
        str, Field(description="The reason for the user to call the agent.")
    ]
    known_info: Annotated[
        Optional[str],
        Field(description="Known information about the user.", default=None),
    ]
    unknown_info: Annotated[
        Optional[str],
        Field(description="Unknown information about the user.", default=None),
    ]
    task_instructions: Annotated[str, Field(description="Instructions for the User.")]

    def __str__(self) -> str:
        lines = []
        tab = "\t"
        lines.append(f"Domain: {self.domain}")
        lines.append(f"Reason for call:\n{textwrap.indent(self.reason_for_call, tab)}")
        if self.known_info is not None:
            lines.append(f"Known info:\n{textwrap.indent(self.known_info, tab)}")
        if self.unknown_info is not None:
            lines.append(f"Unknown info:\n{textwrap.indent(self.unknown_info, tab)}")
        lines.append(
            f"Task instructions:\n{textwrap.indent(self.task_instructions, tab)}"
        )
        return "\n".join(lines)


UserInstructions = StructuredUserInstructions | str


class UserScenario(BaseModel):
    """
    User scenario. All the information that will be sent to the user simulator.
    """

    persona: Annotated[
        Optional[str],
        Field(
            description="User's persona. This information defines the user in general, not the specific situation they are in.",
            default=None,
        ),
    ]
    instructions: Annotated[
        UserInstructions,
        Field(
            description="Instructions for the User. This information defines the specific situation the user is in and the tasks they are trying to complete."
        ),
    ]

    def __str__(self) -> str:
        lines = []
        if self.persona is not None:
            lines.append("Persona:")
            lines.append(textwrap.indent(self.persona, "\t"))
        lines.append("Instructions:")
        lines.append(textwrap.indent(str(self.instructions), "\t"))
        return "\n".join(lines)


class Description(BaseModel):
    """
    Description of a scenario. This can be sent to the evaluator.
    """

    purpose: Annotated[
        Optional[str],
        Field(description="Explains what the scenario is testing.", default=None),
    ]
    relevant_policies: Annotated[
        Optional[str],
        Field(
            description="The part of the policy that is relevant to the scenario.",
            default=None,
        ),
    ]
    notes: Annotated[
        Optional[str],
        Field(
            description="Any additional information about the scenario that is not covered by the other fields.",
            default=None,
        ),
    ]

    def __str__(self) -> str:
        lines = []
        if self.purpose is not None:
            lines.append(f"Purpose: {self.purpose}")
        if self.relevant_policies is not None:
            lines.append(f"Relevant Policies: {self.relevant_policies}")
        if self.notes is not None:
            lines.append(f"Notes: {self.notes}")
        return "\n".join(lines)


class Action(BaseModel):
    """
    An Agent/User action.
    Example:
      {
      "action_id": "get_user_details_1",
      "requestor": "assistant",
      "name": "get_user_details",
      "arguments": { "user_id": "sophia_silva_7557", "note": "I need to get the user details for user_id: sophia_silva_7557" },
      "compare_args": ["user_id"]
    },
    A tool call can be compared with an action by comparing the arguments in compare_args.
    If compare_args is None, will check all the arguments.
    """

    action_id: str = Field(
        description="The unique identifier for the action within a scenario."
    )
    requestor: ToolRequestor = Field(
        description="The requestor of the action.",
        default="assistant",
    )
    name: str = Field(description="The name of the action.")
    arguments: dict = Field(description="The arguments for the action.")
    info: Optional[str] = Field(
        description="Information about the action.", default=None
    )
    compare_args: Optional[list[str]] = Field(
        description="The arguments to check in tool call. If None, will check all the arguments.",
        default=None,
    )

    def __str__(self) -> str:
        lines = []
        lines.append(f"Action ID: {self.action_id}")
        lines.append(f"Requestor: {self.requestor}")
        lines.append(f"Name: {self.name}")
        lines.append(f"Arguments:\n{json.dumps(self.arguments, indent=2)}")
        if self.info is not None:
            lines.append(f"Info:\n{textwrap.indent(self.info, '    ')}")
        return "\n".join(lines)

    def get_func_format(self) -> str:
        """
        Get the function format of the action.
        """
        return (
            f"{self.name}({', '.join([f'{k}={v}' for k, v in self.arguments.items()])})"
        )

    def compare_with_tool_call(self, tool_call: ToolCall) -> bool:
        """
        Compare the action with a tool call.
        If the name is not the same, return False.
        If compare_args is None, will check all the arguments.
        Otherwise, will check only the arguments in compare_args.
        """
        if self.name != tool_call.name:
            return False
        if self.compare_args is None:
            compare_args = tool_call.arguments.keys()
        else:
            compare_args = self.compare_args
        if len(compare_args) == 0:
            return True
        tool_args = {k: v for k, v in tool_call.arguments.items() if k in compare_args}
        action_args = {k: v for k, v in self.arguments.items() if k in compare_args}
        return tool_args == action_args


class EnvFunctionCall(BaseModel):
    """
    A function call on the agent or user environment.
    """

    env_type: Annotated[
        ToolRequestor,
        Field(description="The type of environment to call the function on."),
    ]
    func_name: Annotated[str, Field(description="The name of the function to call.")]
    arguments: Annotated[
        dict, Field(description="The arguments to pass to the function.")
    ]

    def __str__(self) -> str:
        lines = []
        lines.append(f"Env Type: {self.env_type}")
        lines.append(f"Func Name: {self.func_name}")
        lines.append(f"Arguments:\n{json.dumps(self.arguments, indent=2)}")
        return "\n".join(lines)


class EnvAssertion(EnvFunctionCall):
    """
    An assertion on the agent or user environment.
    """

    assert_value: Annotated[
        bool, Field(default=True, description="The value to assert on.")
    ]
    message: Annotated[
        Optional[str],
        Field(
            description="A message to display to the user if the assertion fails.",
            default=None,
        ),
    ]


class RewardType(str, Enum):
    DB = "DB"
    ENV_ASSERTION = "ENV_ASSERTION"
    NL_ASSERTION = "NL_ASSERTION"
    ACTION = "ACTION"
    COMMUNICATE = "COMMUNICATE"


class EvaluationCriteria(BaseModel):
    """
    Evaluation criteria for a particular task. This will be sent to the evaluator.
    """

    actions: Annotated[
        Optional[list[Action]],
        Field(
            description="The actions that the agent should take to complete the task.",
            default=None,
        ),
    ]

    env_assertions: Annotated[
        Optional[list[EnvAssertion]],
        Field(
            description="List of assertions on the agent or user environment.",
            default=None,
        ),
    ]

    communicate_info: Annotated[  # TODO: Deprecate this
        Optional[list[str]],
        Field(
            description="List of information that the agent should communicate to the user.",
            default=None,
        ),
    ]

    nl_assertions: Annotated[
        Optional[list[str]],
        Field(
            description="List of assertions for the task, in natural language.",
            default=None,
        ),
    ]

    reward_basis: Annotated[
        list[RewardType],
        Field(
            description="The basis of the reward. This will be used to determine the reward for the task.",
            default_factory=lambda: [RewardType.DB, RewardType.COMMUNICATE],
        ),
    ]

    def __str__(self) -> str:
        lines = []
        if self.actions is not None:
            lines.append("Actions:")
            lines.extend(
                [textwrap.indent(str(action), "\t") for action in self.actions]
            )
        if self.env_assertions is not None:
            lines.append("Env Assertions:")
            lines.extend(
                [
                    textwrap.indent(str(assertion), "\t")
                    for assertion in self.env_assertions
                ]
            )
        if self.communicate_info is not None:
            lines.append("Communicate Info:")
            lines.extend(
                [textwrap.indent(info, "\t") for info in self.communicate_info]
            )
        if self.nl_assertions is not None:
            lines.append("NL Assertions:")
            lines.extend(
                [textwrap.indent(assertion, "\t") for assertion in self.nl_assertions]
            )
        return "\n".join(lines)

    def info(self) -> dict:
        num_agent_actions = (
            len([action for action in self.actions if action.requestor == "assistant"])
            if self.actions is not None
            else 0
        )
        num_user_actions = (
            len([action for action in self.actions if action.requestor == "user"])
            if self.actions is not None
            else 0
        )
        num_env_assertions = (
            len(self.env_assertions) if self.env_assertions is not None else 0
        )
        num_nl_assertions = (
            len(self.nl_assertions) if self.nl_assertions is not None else 0
        )
        return {
            "num_agent_actions": num_agent_actions,
            "num_user_actions": num_user_actions,
            "num_env_assertions": num_env_assertions,
            "num_nl_assertions": num_nl_assertions,
        }


class InitializationData(BaseModel):
    """
    Updates default data for the agent and the user.
    """

    agent_data: Annotated[
        Optional[dict],
        Field(description="Agent env update data.", default=None),
    ]
    user_data: Annotated[
        Optional[dict],
        Field(description="User env update data.", default=None),
    ]


class InitialState(BaseModel):
    """
    Initial state of the task.
    This will be used to set the initial state of the environment and of the orchestrator.
    """

    initialization_data: Annotated[
        Optional[InitializationData],
        Field(description="Initial env update data.", default=None),
    ]
    initialization_actions: Annotated[
        Optional[list[EnvFunctionCall]],
        Field(
            description="Initial actions to be taken on the environment.", default=None
        ),
    ]
    message_history: Annotated[
        Optional[list[Message]],
        Field(
            default=None,
            description="Messages that have already been exchanged between the user, the agent and the environment. This will be used to set the initial state of the environment and of the orchestrator. Last messages must be from the user or the agent.",
        ),
    ]

    def __str__(self) -> str:
        lines = []
        if self.initialization_data is not None:
            lines.append("Initialization Data:")
            lines.extend(
                [
                    textwrap.indent(
                        self.initialization_data.model_dump_json(indent=2), "\t"
                    )
                ]
            )
        if self.initialization_actions is not None:
            lines.append("Initialization Actions:")
            lines.extend(
                [
                    textwrap.indent(str(action), "\t")
                    for action in self.initialization_actions
                ]
            )
        if self.message_history is not None:
            lines.append("Message History:")
            lines.extend(
                [
                    textwrap.indent(str(message), "\t")
                    for message in self.message_history
                ]
            )
        return "\n".join(lines)


class Task(BaseModel):
    """
    A task for a particular domain. This will be sent to the user simulator, the environment and the evaluator.
    """

    id: str = Field(description="The unique identifier for the task.")
    description: Annotated[
        Optional[Description],
        Field(
            description="Description of the task. This can be sent to the evaluator.",
            default=None,
        ),
    ]
    user_scenario: Annotated[
        UserScenario,
        Field(
            description="User scenario. This information will be sent to the user simulator."
        ),
    ]
    ticket: Annotated[
        Optional[str],
        Field(
            description="Task in ticket format for solo agent solving.",
            default=None,
        ),
    ]
    initial_state: Annotated[
        Optional[InitialState],
        Field(
            description="Initial state of the task. This will be used to set the initial state of the environment and of the orchestrator.",
            default=None,
        ),
    ]
    evaluation_criteria: Annotated[
        Optional[EvaluationCriteria],
        Field(
            description="Evaluation criteria for the task. This will be sent to the evaluator.",
            default=None,
        ),
    ]

    def __str__(self) -> str:
        lines = []
        lines.append(f"ID: {self.id}")
        if self.description is not None:
            lines.append("Description:")
            lines.append(textwrap.indent(str(self.description), "\t"))
        lines.append("User Scenario:")
        lines.append(textwrap.indent(str(self.user_scenario), "\t"))
        if self.initial_state is not None:
            lines.append("Initial State:")
            lines.append(textwrap.indent(str(self.initial_state), "\t"))
        if self.evaluation_criteria is not None:
            lines.append("Evaluation Criteria:")
            lines.append(textwrap.indent(str(self.evaluation_criteria), "\t"))
        return "\n".join(lines)


def make_task_id() -> str:
    """
    Make a task id.
    """
    return str(uuid.uuid4())


def make_task(
    user_instructions: str,
    eval_criteria: EvaluationCriteria,
    initialization_data: Optional[InitializationData] = None,
    initialization_actions: Optional[list[EnvFunctionCall]] = None,
    message_history: Optional[list[Message]] = None,
) -> Task:
    """
    Make a task from a user instruction, an evaluation criteria and a message history.
    """

    user_scenario = UserScenario(instructions=user_instructions)
    evaluation_criteria = eval_criteria
    initial_state = None
    if message_history is not None:
        # Patch to consider empty list of tool calls as None.
        for message in message_history:
            if (
                message.role == "assistant"
                and isinstance(message.tool_calls, list)
                and len(message.tool_calls) == 0
            ):
                message.tool_calls = None

        initial_state = InitialState(
            initialization_data=initialization_data,
            initialization_actions=initialization_actions,
            message_history=message_history,
        )
    return Task(
        id=make_task_id(),
        user_scenario=user_scenario,
        evaluation_criteria=evaluation_criteria,
        initial_state=initial_state,
    )
