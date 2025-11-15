from typing import Optional

from tau2.data_model.message import ToolCall
from tau2.data_model.tasks import EnvAssertion, EnvFunctionCall
from tau2.domains.telecom.environment import TelecomEnvironment
from tau2.domains.telecom.tasks.const import TOOL_CALL_GROUNDING, TOOL_CALL_INFO_CHECK
from tau2.domains.telecom.tasks.manager import TaskManager
from tau2.domains.telecom.tasks.service_issues import airplane_mode_issues
from tau2.domains.telecom.tasks.utils import BaseTask, SelectionSet
from tau2.domains.telecom.user_data_model import NetworkModePreference

expected_internet_speed = 200
expected_internet_desc = "excellent"
invalid_internet_desc = "poor, fair or good"


### Check solve
def get_env_assertions(expected_success: bool) -> list[EnvAssertion]:
    """
    Get the environment assertions for the mobile data issue task.
    """
    if expected_success:
        expected_data_enabled = True
        expected_speed = expected_internet_speed
        expected_desc = expected_internet_desc
    else:
        expected_data_enabled = False
        expected_speed = 0
        expected_desc = None
    return [
        EnvAssertion(
            env_type="user",
            func_name="assert_mobile_data_status",
            arguments={"expected_status": expected_data_enabled},
        ),
        EnvAssertion(
            env_type="user",
            func_name="assert_internet_speed",
            arguments={
                "expected_speed": expected_speed,
                "expected_desc": expected_desc,
            },
        ),
    ]


def is_fixed(env: TelecomEnvironment):
    """
    Check if the mobile data issue is fixed.
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
    Set the user info for the mobile data issue task.
    User info is expected to be "John Smith" and "555-123-2002".
    """
    return [
        EnvFunctionCall(
            env_type="user",
            func_name="set_user_info",
            arguments={"name": "John Smith", "phone_number": "555-123-2002"},
        )
    ]


def set_abroad(*args, **kwargs) -> list[EnvFunctionCall]:
    """
    Set the user location for the mobile data issue task.
    User location is expected to be abroad.
    """
    return [
        EnvFunctionCall(
            env_type="user",
            func_name="set_user_location",
            arguments={"abroad": True},
        )
    ]


def allow_roaming(env: TelecomEnvironment, *args, **kwargs) -> list[EnvFunctionCall]:
    """
    Allow roaming for the user.
    """
    line = env.tools._get_line_by_phone(env.user_tools.db.surroundings.phone_number)
    user = env.tools.get_customer_by_phone(env.user_tools.db.surroundings.phone_number)
    return [
        EnvFunctionCall(
            env_type="assistant",
            func_name="enable_roaming",
            arguments={"customer_id": user.customer_id, "line_id": line.line_id},
        )
    ]


def disallow_roaming(env: TelecomEnvironment, *args, **kwargs) -> list[EnvFunctionCall]:
    """
    Disallow roaming for the user.
    """
    line = env.tools._get_line_by_phone(env.user_tools.db.surroundings.phone_number)
    user = env.tools.get_customer_by_phone(env.user_tools.db.surroundings.phone_number)
    return [
        EnvFunctionCall(
            env_type="assistant",
            func_name="disable_roaming",
            arguments={"customer_id": user.customer_id, "line_id": line.line_id},
        ),
        EnvFunctionCall(
            env_type="user",
            func_name="simulate_network_search",
            arguments={},
        ),
        EnvAssertion(
            env_type="user",
            func_name="assert_internet_speed",
            arguments={"expected_speed": 0, "expected_desc": "No Connection"},
        ),
    ]


def data_mode_off(env: TelecomEnvironment):
    """
    Turn off data mode.
    """
    return [
        EnvFunctionCall(
            env_type="user",
            func_name="turn_data_off",
            arguments={},
        ),
        EnvAssertion(
            env_type="user",
            func_name="assert_mobile_data_status",
            arguments={"expected_status": False},
        ),
    ]


def data_roaming_off(env: TelecomEnvironment):
    """
    Turn off data roaming.
    """
    return [
        EnvFunctionCall(
            env_type="user",
            func_name="turn_roaming_off",
            arguments={},
        ),
        EnvAssertion(
            env_type="user",
            func_name="assert_mobile_roaming_status",
            arguments={"expected_status": False},
        ),
    ]


def data_roaming_on(env: TelecomEnvironment):
    """
    Turn on data roaming.
    """
    return [
        EnvFunctionCall(
            env_type="user",
            func_name="turn_roaming_on",
            arguments={},
        ),
        EnvAssertion(
            env_type="user",
            func_name="assert_mobile_roaming_status",
            arguments={"expected_status": True},
        ),
    ]


def data_saver_mode_on(env: TelecomEnvironment):
    """
    Turn on data saver mode.
    """
    return [
        EnvFunctionCall(
            env_type="user",
            func_name="turn_data_saver_mode_on",
            arguments={},
        ),
        EnvAssertion(
            env_type="user",
            func_name="assert_mobile_data_saver_mode_status",
            arguments={"expected_status": True},
        ),
    ]


def set_bad_network_preference_slow_speed(env: TelecomEnvironment):
    """
    Set the network mode preference to a bad network preference.
    """
    bad_mode = NetworkModePreference.TWO_G_ONLY
    return [
        EnvFunctionCall(
            env_type="user",
            func_name="set_network_mode_preference",
            arguments={"mode": bad_mode.value},
        ),
    ]


def set_vpn_slow_speed(env: TelecomEnvironment):
    """
    Set the VPN to a slow speed.
    """
    return [
        EnvFunctionCall(
            env_type="user",
            func_name="break_vpn",
            arguments={},
        ),
        EnvAssertion(
            env_type="user",
            func_name="assert_internet_not_excellent",
            arguments={},
        ),
    ]


def set_data_usage_exceeded(env: TelecomEnvironment):
    return [
        EnvFunctionCall(
            env_type="assistant",
            func_name="set_data_usage",
            arguments={
                "customer_id": "C1001",
                "line_id": "L1002",
                "data_used_gb": 15.1,
            },
        ),
        EnvAssertion(
            env_type="user",
            func_name="assert_mobile_data_usage_exceeded",
            arguments={"expected_status": True},
        ),
    ]


def set_data_usage_exceeded_no_refuel(env: TelecomEnvironment):
    return [
        EnvFunctionCall(
            env_type="assistant",
            func_name="refuel_data",
            arguments={"customer_id": "C1001", "line_id": "L1002", "gb_amount": 2.0},
        ),
        EnvFunctionCall(
            env_type="assistant",
            func_name="set_data_usage",
            arguments={
                "customer_id": "C1001",
                "line_id": "L1002",
                "data_used_gb": 17.1,
            },
        ),
        EnvAssertion(
            env_type="user",
            func_name="assert_mobile_data_usage_exceeded",
            arguments={"expected_status": True},
        ),
    ]


### Fix Functions
def fix_airplane_mode_on(env: TelecomEnvironment):
    """
    Fix the airplane mode on issue.
    """
    return [
        ToolCall(
            requestor="user",
            name="toggle_airplane_mode",
            arguments={},
        )
    ]


def fix_data_mode_off(env: TelecomEnvironment):
    """
    Fix the data mode off issue.
    """
    return [
        ToolCall(
            requestor="user",
            name="toggle_data",
            arguments={},
        )
    ]


def fix_data_roaming_off(env: TelecomEnvironment):
    """
    Fix the data roaming off issue.
    """
    return [
        ToolCall(
            requestor="user",
            name="toggle_roaming",
            arguments={},
        )
    ]


def fix_data_saver_mode_on(env: TelecomEnvironment):
    """
    Fix the data saver mode on issue.
    """
    return [
        ToolCall(
            requestor="user",
            name="toggle_data_saver_mode",
            arguments={},
        )
    ]


def fix_set_bad_network_preference_slow_speed(env: TelecomEnvironment):
    """
    Fix the set bad network preference slow speed issue.
    """
    return [
        ToolCall(
            requestor="user",
            name="set_network_mode_preference",
            arguments={"mode": NetworkModePreference.FOUR_G_5G_PREFERRED.value},
        )
    ]


def fix_set_vpn_slow_speed(env: TelecomEnvironment):
    """
    Fix the set VPN slow speed issue.
    """
    return [
        ToolCall(
            requestor="user",
            name="disconnect_vpn",
            arguments={},
        )
    ]


def fix_data_usage_exceeded(env: TelecomEnvironment):
    return [
        ToolCall(
            requestor="assistant",
            name="refuel_data",
            arguments={"customer_id": "C1001", "line_id": "L1002", "gb_amount": 2.0},
        )
    ]


def fix_disallow_roaming(env: TelecomEnvironment):
    """
    Fix the disallow roaming issue.
    """
    user = env.tools.get_customer_by_phone(env.user_tools.db.surroundings.phone_number)
    line = env.tools._get_line_by_phone(env.user_tools.db.surroundings.phone_number)
    return [
        ToolCall(
            requestor="assistant",
            name="enable_roaming",
            arguments={"customer_id": user.customer_id, "line_id": line.line_id},
        )
    ]


### Extra Env Assertions
def assert_data_refueling_amount(env: TelecomEnvironment) -> list[EnvAssertion]:
    user = env.tools.get_customer_by_phone(env.user_tools.db.surroundings.phone_number)
    line = env.tools._get_line_by_phone(env.user_tools.db.surroundings.phone_number)
    original_data_refueling_gb = line.data_refueling_gb
    # Assume the environment has not been modified by fix functions
    return [
        EnvAssertion(
            env_type="assistant",
            func_name="assert_data_refueling_amount",
            arguments={
                "customer_id": user.customer_id,
                "line_id": line.line_id,
                "expected_amount": original_data_refueling_gb + 2.0,
            },
        )
    ]


### Base Tasks
user_abroad_roaming_enabled_off_task = BaseTask(
    name="user_abroad_roaming_enabled_off",
    description="User is abroad and roaming is off",
    init_funcs=[set_abroad, data_roaming_off, allow_roaming],
    fix_funcs=[fix_data_roaming_off],
)
user_abroad_roaming_disabled_on_task = BaseTask(
    name="user_abroad_roaming_disabled_on",
    description="User is abroad and roaming is off",
    init_funcs=[set_abroad, data_roaming_on, disallow_roaming],
    fix_funcs=[fix_disallow_roaming],
)

user_abroad_roaming_disabled_off_task = BaseTask(
    name="user_abroad_roaming_disabled_off",
    description="User is abroad and roaming is off",
    init_funcs=[set_abroad, data_roaming_off, disallow_roaming],
    fix_funcs=[fix_disallow_roaming, fix_data_roaming_off],
)

data_mode_off_task = BaseTask(
    name="data_mode_off",
    description="Data mode is off",
    init_funcs=[data_mode_off],
    fix_funcs=[fix_data_mode_off],
)

data_saver_mode_on_task = BaseTask(
    name="data_saver_mode_on",
    description="Data saver mode is on",
    init_funcs=[data_saver_mode_on],
    fix_funcs=[fix_data_saver_mode_on],
)

bad_network_preference_task = BaseTask(
    name="bad_network_preference",
    description="Bad network preference",
    init_funcs=[set_bad_network_preference_slow_speed],
    fix_funcs=[fix_set_bad_network_preference_slow_speed],
)

bad_vpn_task = BaseTask(
    name="bad_vpn",
    description="Bad vpn",
    init_funcs=[set_vpn_slow_speed],
    fix_funcs=[fix_set_vpn_slow_speed],
)

data_usage_exceeded_task = BaseTask(
    name="data_usage_exceeded",
    description="Data usage exceeded",
    init_funcs=[set_data_usage_exceeded],
    fix_funcs=[fix_data_usage_exceeded],
    extra_env_assertions=[assert_data_refueling_amount],
)


data_usage_exceeded_no_refuel_task = BaseTask(
    name="data_usage_exceeded_no_refuel",
    description="Data usage exceeded",
    init_funcs=[set_data_usage_exceeded_no_refuel],
    fix_funcs=[None],
)


### Selection Sets

# Path 2.1: No Mobile Data
# Requires workflow Step 2.1.1
# -> service_issues_sample_sets
service_issues_sample_sets = [
    airplane_mode_issues,
]

# Requires workflow Step 2.1.2
roaming_issues = SelectionSet(
    tasks=[
        user_abroad_roaming_enabled_off_task,
        user_abroad_roaming_disabled_on_task,
        user_abroad_roaming_disabled_off_task,
    ]
)
# Requires workflow Step 2.1.3
data_mode_issues = SelectionSet(tasks=[data_mode_off_task])

# Path 2.2: Slow Mobile Data
# Requires workflow Step 2.2.1
data_usage_exceeded_issues = SelectionSet(
    tasks=[data_usage_exceeded_task, data_usage_exceeded_no_refuel_task]
)

# Requires workflow Step 2.2.2
data_saver_mode_issues = SelectionSet(tasks=[data_saver_mode_on_task])

# Requires workflow Step 2.2.3
network_preference_issues = SelectionSet(tasks=[bad_network_preference_task])

# Requires workflow Step 2.2.4
vpn_issues = SelectionSet(tasks=[bad_vpn_task])

mobile_data_issues_selection_sets = [
    roaming_issues,
    data_mode_issues,
    data_saver_mode_issues,
    network_preference_issues,
    vpn_issues,
    data_usage_exceeded_issues,
]


selection_sets = service_issues_sample_sets + mobile_data_issues_selection_sets


def task_validator(tasks: list[Optional[BaseTask]]):
    """
    Validate that the tasks to ensure at least one mobile data issue is included.
    """
    # num_tasks_service_issues = len(
    #     [task for task in tasks[: len(service_issues_sample_sets)] if task is not None]
    # )
    num_tasks_mobile_data_issues = len(
        [task for task in tasks[len(service_issues_sample_sets) :] if task is not None]
    )
    return num_tasks_mobile_data_issues > 0


### Task Manager
mobile_data_task_manager = TaskManager(
    name="mobile_data_issue",
    purpose="Test resolution path: Mobile Data/Slow Internet Issues.",
    task_instructions=f"If the agent suggests actions that don't immediately fix the issue, follow their guidance but express mild frustration after the first unsuccessful attempt. You will consider the issue resolved only when speed test returns {expected_internet_desc} internet speed and nothing else. If it returns {invalid_internet_desc}, you will not consider the issue resolved. You are willing to refuel 2.0 GB of data if necessary, but you do not want to change your mobile data plan. {TOOL_CALL_INFO_CHECK} {TOOL_CALL_GROUNDING}",
    reason_for_call=f"You mobile data is not working properly. It either stops working or is very slow. You want to fix it and absolutely want to get {expected_internet_desc} internet speed on your phone. You are not willing to accept any other internet speed ({invalid_internet_desc}). You do not have access to wifi.",
    known_info="You are {name} with phone number {phone_number}. You are currently {location}.",
    ticket=f"The user is experiencing issues with their mobile data. They are unable to use their phone to browse the internet, and the status bar shows 'No Service'. Customer name: {{name}}, phone number: {{phone_number}}, current location: {{location}}. They will consider the issue resolved when speed test returns {expected_internet_desc} internet speed. They will not change their mobile data plan but they will refuel 2.0 GB of data if necessary.",
    selection_sets=selection_sets,
    get_env_assertions=get_env_assertions,
    set_surrounding=set_surrounding,
    is_fixed=is_fixed,
    task_validator=task_validator,
    domain="telecom",
)

if __name__ == "__main__":
    tasks = mobile_data_task_manager.create_tasks(save_tasks=False)
    print(f"Number of tasks: {len(tasks)}")
