import pandas as pd

from tau2.data_model.simulation import Results, RewardInfo, RewardType
from tau2.environment.toolkit import ToolType
from tau2.metrics.agent_metrics import is_successful
from tau2.registry import registry


def get_write_tools(domain):
    env = registry.get_env_constructor(domain)()
    user_write_tools = []
    agent_write_tools = []

    for tool in env.tools.get_tools():
        tool_type = getattr(env.tools, tool).__tool_type__
        if tool_type == ToolType.WRITE:
            agent_write_tools.append(tool)

    if env.user_tools:
        for tool in env.user_tools.get_tools():
            tool_type = getattr(env.user_tools, tool).__tool_type__
            if tool_type == ToolType.WRITE:
                user_write_tools.append(tool)
    return set(agent_write_tools), set(user_write_tools)


def analyze_reward(
    reward_info: RewardInfo, agent_write_tools: set[str], user_write_tools: set[str]
):
    """
    Analyze the reward breakdown.
    """
    reward_breakdown = reward_info.reward_breakdown
    try:
        if RewardType.COMMUNICATE in reward_info.reward_basis:
            communicate_success = (
                is_successful(reward_breakdown[RewardType.COMMUNICATE])
                if reward_breakdown is not None
                else 0
            )
        else:
            communicate_success = None
        if RewardType.ENV_ASSERTION in reward_info.reward_basis:
            env_success = (
                is_successful(reward_breakdown[RewardType.ENV_ASSERTION])
                if reward_breakdown is not None
                else 0
            )
        else:
            env_success = None
        if RewardType.DB in reward_info.reward_basis:
            db_success = (
                is_successful(reward_breakdown[RewardType.DB])
                if reward_breakdown is not None
                else 0
            )
        else:
            db_success = None
    except Exception as e:
        print("failure")
        print(reward_info)
        raise e

    write_checks = []
    if reward_info.action_checks is not None:
        for action_check in reward_info.action_checks:
            if action_check.action.requestor == "assistant":
                if action_check.action.name in agent_write_tools:
                    write_checks.append(action_check)
            else:
                if action_check.action.name in user_write_tools:
                    write_checks.append(action_check)

    num_write_checks = len(write_checks)
    num_successful_write_checks = sum(1 for check in write_checks if check.action_match)
    reward_analysis = {
        "success": is_successful(reward_info.reward),
        "communication": communicate_success,
        "environment": env_success,
        "database": db_success,
        "num_correct_write_action": num_successful_write_checks,
        "num_write_action": num_write_checks,
    }
    return reward_analysis


def analyze_reward_actions(reward_info: RewardInfo) -> pd.DataFrame:
    """
    Analyze the actions taken by the agent and the user.
    """
    reward_breakdown = reward_info.reward_breakdown
    if reward_breakdown is None:
        return None
    rows = []
    if reward_info.action_checks is None:
        return None
    for action_check in reward_info.action_checks:
        row = {
            "requestor": action_check.action.requestor,
            "action_name": action_check.action.name,
            "action": action_check.action.get_func_format(),
            "action_match": action_check.action_match,
        }
        rows.append(row)
    return pd.DataFrame(rows)


def result_reward_analysis(results: Results):
    """
    Analyze the reward breakdown.
    """
    rows = []
    agent_write_tools, user_write_tools = get_write_tools(
        results.info.environment_info.domain_name
    )
    for simulation in results.simulations:
        reward_analysis = analyze_reward(
            simulation.reward_info, agent_write_tools, user_write_tools
        )
        reward_analysis["task_id"] = simulation.task_id
        reward_analysis["trial"] = simulation.trial
        rows.append(reward_analysis)
    return pd.DataFrame(rows)


def result_reward_actions_analysis(results: Results):
    """
    Analyze the actions taken by the agent and the user.
    """
    dfs = []
    for simulation in results.simulations:
        reward_actions_analysis = analyze_reward_actions(simulation.reward_info)
        if reward_actions_analysis is None:
            continue
        reward_actions_analysis["task_id"] = simulation.task_id
        reward_actions_analysis["trial"] = simulation.trial
        dfs.append(reward_actions_analysis)
    return pd.concat(dfs)
