from typing import Optional

from tau2.data_model.message import ToolCall
from tau2.data_model.tasks import EnvAssertion, EnvFunctionCall
from tau2.domains.telecom.environment import TelecomEnvironment
from tau2.domains.telecom.tasks.const import TOOL_CALL_GROUNDING, TOOL_CALL_INFO_CHECK
from tau2.domains.telecom.tasks.manager import TaskManager
from tau2.domains.telecom.tasks.mobile_data_issues import (
    data_mode_issues,
    data_usage_exceeded_issues,
    network_preference_issues,
    roaming_issues,
)
from tau2.domains.telecom.tasks.service_issues import (
    airplane_mode_issues,
    unseat_sim_card_issues,
)
from tau2.domains.telecom.tasks.utils import BaseTask, SelectionSet


### Check solve
def get_env_assertions(expected_success: bool) -> list[EnvFunctionCall]:
    """
    Get the environment assertions for the mms issue task.
    If expected success is True:
    - Can send mms is expected to be True
    If expected success is False:
    - Can send mms is expected to be False
    """
    return [
        EnvAssertion(
            env_type="user",
            func_name="assert_can_send_mms",
            arguments={"expected_status": expected_success},
        ),
    ]


def is_fixed(env: TelecomEnvironment):
    """
    Check if the mms issue is fixed.
    """
    assertions = get_env_assertions(expected_success=True)
    success = True
    for assertion in assertions:
        success = success and env.run_env_assertion(
            assertion,
            raise_assertion_error=False,
        )
    return success


### Init Functions
def set_surrounding(*args, **kwargs) -> list[EnvFunctionCall]:
    """
    Set the user info for the mms issue task.
    User info is expected to be "John Smith" and "555-123-2002".
    """
    return [
        EnvFunctionCall(
            env_type="user",
            func_name="set_user_info",
            arguments={"name": "John Smith", "phone_number": "555-123-2002"},
        )
    ]


def set_wifi_calling_on(*args, **kwargs) -> list[EnvFunctionCall]:
    """
    Set the wifi calling on for the mms issue task.
    """
    return [
        EnvFunctionCall(
            env_type="user",
            func_name="set_wifi_calling",
            arguments={"enabled": True, "mms_over_wifi": True},
            # MMS over WIFI need to be True to make mms over mobile data not working
        )
    ]


def break_apn_mms_setting(*args, **kwargs) -> list[EnvFunctionCall]:
    """
    Break the apn mms setting for the mms issue task.
    """
    return [
        EnvFunctionCall(
            env_type="user",
            func_name="break_apn_mms_setting",
            arguments={},
        )
    ]


def _get_remove_app_permission_actions(
    app_name: str = "messaging", permission: str = "sms"
):
    """
    Get the remove app permission actions for the mms issue task.
    """
    return EnvFunctionCall(
        env_type="user",
        func_name="remove_app_permission",
        arguments={"app_name": app_name, "permission": permission},
    )


def break_app_sms_permission(*args, **kwargs) -> list[EnvFunctionCall]:
    """
    Break the app sms permission for the mms issue task.
    """
    return [_get_remove_app_permission_actions(app_name="messaging", permission="sms")]


def break_app_storage_permission(*args, **kwargs) -> list[EnvFunctionCall]:
    """
    Break the app storage permission for the mms issue task.
    """
    return [
        _get_remove_app_permission_actions(app_name="messaging", permission="storage")
    ]


def break_app_both_permissions(*args, **kwargs) -> list[EnvFunctionCall]:
    """
    Break the app both permissions for the mms issue task.
    """
    return [
        _get_remove_app_permission_actions(app_name="messaging", permission="sms"),
        _get_remove_app_permission_actions(app_name="messaging", permission="storage"),
    ]


### Fix Functions
def fix_set_wifi_calling_on(*args, **kwargs) -> list[ToolCall]:
    """
    Fix the set wifi calling on issue.
    """
    return [
        ToolCall(
            requestor="user",
            name="toggle_wifi_calling",
            arguments={},
        )
    ]


def fix_break_apn_mms_setting(*args, **kwargs) -> list[ToolCall]:
    """
    Fix the break apn mms setting issue.
    """
    return [
        ToolCall(
            requestor="user",
            name="reset_apn_settings",
            arguments={},
        ),
        ToolCall(
            requestor="user",
            name="reboot_device",
            arguments={},
        ),
    ]


def _get_grant_app_permission_actions(
    app_name: str = "messaging", permission: str = "sms"
) -> ToolCall:
    """
    Get the grant app permission actions for the mms issue task.
    """
    return ToolCall(
        requestor="user",
        name="grant_app_permission",
        arguments={"app_name": app_name, "permission": permission},
    )


def fix_break_app_sms_permission(*args, **kwargs) -> list[ToolCall]:
    """
    Fix the break app sms permission issue.
    """
    return [_get_grant_app_permission_actions(app_name="messaging", permission="sms")]


def fix_break_app_storage_permission(*args, **kwargs) -> list[ToolCall]:
    """
    Fix the break app storage permission issue.
    """
    return [
        _get_grant_app_permission_actions(app_name="messaging", permission="storage")
    ]


def fix_break_app_both_permissions(*args, **kwargs) -> list[ToolCall]:
    """
    Fix the break app both permissions issue.
    """
    return [
        _get_grant_app_permission_actions(app_name="messaging", permission="sms"),
        _get_grant_app_permission_actions(app_name="messaging", permission="storage"),
    ]


### Base Tasks
bad_wifi_calling_task = BaseTask(
    name="bad_wifi_calling",
    description="Bad wifi calling",
    init_funcs=[set_wifi_calling_on],
    fix_funcs=[fix_set_wifi_calling_on],
)
break_apn_mms_setting_task = BaseTask(
    name="break_apn_mms_setting",
    description="Break apn mms setting",
    init_funcs=[break_apn_mms_setting],
    fix_funcs=[fix_break_apn_mms_setting],
)

break_app_sms_permission_task = BaseTask(
    name="break_app_sms_permission",
    description="Break app sms permission",
    init_funcs=[break_app_sms_permission],
    fix_funcs=[fix_break_app_sms_permission],
)
break_app_storage_permission_task = BaseTask(
    name="break_app_storage_permission",
    description="Break app storage permission",
    init_funcs=[break_app_storage_permission],
    fix_funcs=[fix_break_app_storage_permission],
)
break_app_both_permissions_task = BaseTask(
    name="break_app_both_permissions",
    description="Break app both permissions",
    init_funcs=[break_app_both_permissions],
    fix_funcs=[fix_break_app_both_permissions],
)

### Selection Sets


# Requires workflow Step 3.1
# -> service_issues_sample_sets
service_issues_sample_sets: list[SelectionSet] = [
    airplane_mode_issues,
    unseat_sim_card_issues,
]

# Requires workflow Step 3.2
# -> mobile_data_issues_sample_sets
mobile_data_issues_sample_sets = [
    data_mode_issues,
    data_usage_exceeded_issues,
    roaming_issues,
]


# Requires workflow Step 3.4
wifi_calling_issues = SelectionSet(tasks=[bad_wifi_calling_task])

# Requires workflow Step 3.5
app_permission_issues = SelectionSet(
    tasks=[
        break_app_sms_permission_task,
        break_app_storage_permission_task,
        break_app_both_permissions_task,
    ]
)

# Requires workflow Step 3.6
apn_mms_issues = SelectionSet(tasks=[break_apn_mms_setting_task])


mms_issues_selection_sets = [
    network_preference_issues,  # Step3.3
    wifi_calling_issues,  # Step3.4
    apn_mms_issues,  # Step3.6
    app_permission_issues,  # Step3.5
]

selection_sets = (
    service_issues_sample_sets
    + mobile_data_issues_sample_sets
    + mms_issues_selection_sets
)


def task_validator(tasks: list[Optional[BaseTask]]):
    """
    Validate that the tasks to ensure at least one mms issue is included.
    """
    # num_tasks_service_issues = len(
    #     [task for task in tasks[: len(service_issues_sample_sets)] if task is not None]
    # )
    # num_tasks_mobile_data_issues = len(
    #     [
    #         task
    #         for task in tasks[
    #             len(service_issues_sample_sets) : len(service_issues_sample_sets)
    #             + len(mobile_data_issues_sample_sets)
    #         ]
    #         if task is not None
    #     ]
    # )
    num_tasks_mms_issues = len(
        [
            task
            for task in tasks[
                len(service_issues_sample_sets) + len(mobile_data_issues_sample_sets) :
            ]
            if task is not None
        ]
    )
    return num_tasks_mms_issues > 0


### Task Manager
mms_issue_task_manager = TaskManager(
    name="mms_issue",
    purpose="Test resolution path: MMS (Picture/Group Messaging) Issues.",
    task_instructions=f"If the agent suggests actions that don't immediately fix the issue, follow their guidance but express mild frustration after the first unsuccessful attempt. You are willing to refuel 2.0 GB of data if necessary, but you do not want to change your mobile data plan. {TOOL_CALL_INFO_CHECK} {TOOL_CALL_GROUNDING}",
    reason_for_call="You are unable to send MMS messages using your messaging app for the past few hours. You want to fix it and successfully send an MMS message.",
    known_info="You are {name} with phone number {phone_number}. You are currently {location}.",
    ticket="The user has been unable to send MMS messages using their messaging app for the past few hours. Customer name: {name}, phone number: {phone_number}, current location: {location}. They will consider the issue resolved when an MMS message can be successfully sent.",
    selection_sets=selection_sets,
    get_env_assertions=get_env_assertions,
    set_surrounding=set_surrounding,
    is_fixed=is_fixed,
    domain="telecom",
    task_validator=task_validator,
)

if __name__ == "__main__":
    tasks = mms_issue_task_manager.create_tasks(save_tasks=False)
    print(f"Number of tasks: {len(tasks)}")
    tasks = mms_issue_task_manager.create_tasks(save_tasks=False)
    print(f"Number of tasks: {len(tasks)}")
    print(f"Number of tasks: {len(tasks)}")
    tasks = mms_issue_task_manager.create_tasks(save_tasks=False)
    print(f"Number of tasks: {len(tasks)}")
