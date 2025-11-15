import json
import multiprocessing
import random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

from loguru import logger

from tau2.agent.llm_agent import LLMAgent, LLMGTAgent, LLMSoloAgent
from tau2.data_model.simulation import (
    AgentInfo,
    Info,
    Results,
    RunConfig,
    SimulationRun,
    UserInfo,
)
from tau2.data_model.tasks import Task
from tau2.environment.environment import Environment, EnvironmentInfo
from tau2.evaluator.evaluator import EvaluationType, evaluate_simulation
try:  # pragma: no cover - optional dependency
    from tau2.gym.gym_agent import GymAgent
except ImportError:  # pragma: no cover - optional dependency
    GymAgent = None  # type: ignore[assignment]
from tau2.metrics.agent_metrics import compute_metrics
from tau2.orchestrator.orchestrator import Orchestrator
from tau2.registry import RegistryInfo, registry
from tau2.user.user_simulator import DummyUser, get_global_user_sim_guidelines
from tau2.utils.display import ConsoleDisplay, Text
from tau2.utils.pydantic_utils import get_pydantic_hash
from tau2.utils.utils import DATA_DIR, get_commit_hash, get_now, show_dict_diff


def get_options() -> RegistryInfo:
    """
    Returns options for the simulator.
    """
    return registry.get_info()


def get_environment_info(
    domain_name: str, include_tool_info: bool = False
) -> EnvironmentInfo:
    """Get information about the environment for a registered Domain"""
    global registry
    env_constructor = registry.get_env_constructor(domain_name)
    return env_constructor().get_info(include_tool_info=include_tool_info)


def load_task_splits(task_set_name: str) -> Optional[dict[str, list[str]]]:
    """
    Loads the task splits for the given domain.
    """
    global registry
    task_split_loader = registry.get_task_splits_loader(task_set_name)
    if task_split_loader is None:
        return None
    return task_split_loader()


def load_tasks(task_set_name: str, task_split_name: Optional[str] = None) -> list[Task]:
    """
    Loads the tasks for the given domain.
    """
    global registry
    task_loader = registry.get_tasks_loader(task_set_name)
    tasks = task_loader(task_split_name=task_split_name)
    return tasks


def get_tasks(
    task_set_name: str,
    task_split_name: Optional[str] = None,
    task_ids: Optional[list[str]] = None,
    num_tasks: Optional[int] = None,
) -> list[Task]:
    """
    Loads the tasks for the given domain.
    """
    if task_ids is None:
        tasks = load_tasks(task_set_name=task_set_name, task_split_name=task_split_name)
    else:
        tasks = [
            task
            for task in load_tasks(
                task_set_name=task_set_name, task_split_name=task_split_name
            )
            if task.id in task_ids
        ]
    if task_ids is not None and len(tasks) != len(task_ids):
        missing_tasks = set(task_ids) - set([task.id for task in tasks])
        raise ValueError(
            f"Not all tasks were found for task set {task_set_name} - {task_split_name}: {missing_tasks}"
        )
    if num_tasks is not None:
        tasks = tasks[:num_tasks]
    return tasks


def make_run_name(config: RunConfig) -> str:
    """
    Make a run name from the run config
    """
    clean_llm_agent_name = [x for x in config.llm_agent.split("/") if x][-1]
    agent_name = f"{config.agent}_{clean_llm_agent_name}"

    clean_llm_user_name = [x for x in config.llm_user.split("/") if x][-1]
    user_name = f"{config.user}_{clean_llm_user_name}"

    return f"{get_now()}_{config.domain}_{agent_name}_{user_name}"


def run_domain(config: RunConfig) -> Results:
    """
    Run simulations for a domain
    """
    config.validate()
    ConsoleDisplay.display_run_config(config)
    if config.task_set_name is None:
        task_set_name = config.domain
    else:
        task_set_name = config.task_set_name
    tasks = get_tasks(
        task_set_name=task_set_name,
        task_split_name=config.task_split_name,
        task_ids=config.task_ids,
        num_tasks=config.num_tasks,
    )
    if "gt" in config.agent:
        total_num_tasks = len(tasks)
        tasks = [task for task in tasks if LLMGTAgent.check_valid_task(task)]
        num_tasks = len(tasks)
        console_text = Text(
            text=f"Running {num_tasks} out of {total_num_tasks} tasks for GT agent.",
            style="bold green",
        )
        ConsoleDisplay.console.print(console_text)
    if "solo" in config.agent:
        total_num_tasks = len(tasks)
        tasks = [task for task in tasks if LLMSoloAgent.check_valid_task(task)]
        num_tasks = len(tasks)
        console_text = Text(
            text=f"Running {num_tasks} out of {total_num_tasks} tasks for solo agent.",
            style="bold green",
        )
        ConsoleDisplay.console.print(console_text)

    num_trials = config.num_trials
    save_to = config.save_to
    if save_to is None:
        save_to = make_run_name(config)
    save_to = DATA_DIR / "simulations" / f"{save_to}.json"
    simulation_results = run_tasks(
        domain=config.domain,
        tasks=tasks,
        agent=config.agent,
        user=config.user,
        llm_agent=config.llm_agent,
        llm_args_agent=config.llm_args_agent,
        llm_user=config.llm_user,
        llm_args_user=config.llm_args_user,
        num_trials=num_trials,
        max_steps=config.max_steps,
        max_errors=config.max_errors,
        save_to=save_to,
        console_display=True,
        evaluation_type=EvaluationType.ALL,
        max_concurrency=config.max_concurrency,
        seed=config.seed,
        log_level=config.log_level,
        enforce_communication_protocol=config.enforce_communication_protocol,
    )
    metrics = compute_metrics(simulation_results)
    ConsoleDisplay.display_agent_metrics(metrics)

    return simulation_results


def run_tasks(
    domain: str,
    tasks: list[Task],
    agent: str,
    user: str,
    llm_agent: Optional[str] = None,
    llm_args_agent: Optional[dict] = None,
    llm_user: Optional[str] = None,
    llm_args_user: Optional[dict] = None,
    num_trials: int = 1,
    max_steps: int = 100,
    max_errors: int = 10,
    save_to: Optional[str | Path] = None,
    console_display: bool = True,
    evaluation_type: EvaluationType = EvaluationType.ALL,
    max_concurrency: int = 1,
    seed: Optional[int] = 300,
    log_level: Optional[str] = "INFO",
    enforce_communication_protocol: bool = False,
) -> Results:
    """
    Runs tasks for a given domain.
    If llm_as_judge is True, the LLM will be used to annotate the simulation run.
    Calculates the reward for the simulation run.
    Args:
        domain (str): The domain to run the simulation on.
        tasks (list[Task]): The tasks to run.
        agent (str): The agent to run the simulation on.
        user (str): The user to run the simulation on.
        llm_agent (str): The model to use for the agent.
        llm_args_agent (dict): The arguments to pass to the LLM for the agent.
        llm_user (str): The model to use for the user.
        llm_args_user (dict): The arguments to pass to the LLM for the user.
        max_steps (int): The maximum number of steps to run the simulation.
        max_errors (int): The maximum number of errors to allow in the simulation.
        save_to (str | Path): The path to json file where to save the simulation results. If the file already exists, it will try to resume the run.
        evaluation_type (EvaluationType): The type of evaluation to use.
        max_concurrency (int): The maximum number of concurrent simulations to run.
        seed (int): The seed to use for the simulation.
        log_level (str): The log level to use.
        enforce_communication_protocol (bool): Whether to enforce communication protocol rules.
    Returns:
        The simulation results and the annotations (if llm_review is True).
    """
    if isinstance(save_to, str):
        save_to = Path(save_to)
    # Set log level from config
    logger.remove()
    logger.add(lambda msg: print(msg), level=log_level)
    if len(tasks) == 0:
        raise ValueError("No tasks to run")
    if num_trials <= 0:
        raise ValueError("Number of trials must be greater than 0")
    if max_steps <= 0:
        raise ValueError("Max steps must be greater than 0")
    if max_errors <= 0:
        raise ValueError("Max errors must be greater than 0")

    random.seed(seed)

    seeds = [random.randint(0, 1000000) for _ in range(num_trials)]
    if "seed" in llm_args_agent:
        logger.warning("Each trial will modify the seed for the agent")

    if "seed" in llm_args_user:
        logger.warning("Each trial will modify the seed for the user")

    lock = multiprocessing.Lock()

    info = get_info(
        domain=domain,
        agent=agent,
        user=user,
        llm_agent=llm_agent,
        llm_args_agent=llm_args_agent,
        llm_user=llm_user,
        llm_args_user=llm_args_user,
        num_trials=num_trials,
        max_steps=max_steps,
        max_errors=max_errors,
        seed=seed,
    )
    simulation_results = Results(
        info=info,
        tasks=tasks,
        simulations=[],
    )
    done_runs = set()
    if save_to is not None:
        # If save_to already exists, check if the user wants to resume the run.
        if save_to.exists():
            response = (
                ConsoleDisplay.console.input(
                    "[yellow]File [bold]{}[/bold] already exists. Do you want to resume the run? (y/n)[/yellow] ".format(
                        save_to
                    )
                )
                .lower()
                .strip()
            )
            if response != "y":
                raise FileExistsError(
                    f"File {save_to} already exists. Please delete it or use a different save_to name."
                )
            with open(save_to, "r") as fp:
                prev_simulation_results = Results.model_validate_json(fp.read())
                # Check if the run config has changed
                if get_pydantic_hash(prev_simulation_results.info) != get_pydantic_hash(
                    simulation_results.info
                ):
                    diff = show_dict_diff(
                        prev_simulation_results.info.model_dump(),
                        simulation_results.info.model_dump(),
                    )
                    ConsoleDisplay.console.print(
                        f"The run config has changed.\n\n{diff}\n\nDo you want to resume the run? (y/n)"
                    )
                    response = (
                        ConsoleDisplay.console.input(
                            "[yellow]File [bold]{}[/bold] already exists. Do you want to resume the run? (y/n)[/yellow] ".format(
                                save_to
                            )
                        )
                        .lower()
                        .strip()
                    )
                    if response != "y":
                        raise ValueError(
                            "The run config has changed. Please delete the existing file or use a different save_to name."
                        )
                # Check if the task set has changed
                if not all(
                    get_pydantic_hash(task) == get_pydantic_hash(prev_task)
                    for task, prev_task in zip(
                        sorted(simulation_results.tasks, key=lambda x: x.id),
                        sorted(prev_simulation_results.tasks, key=lambda x: x.id),
                    )
                ):
                    raise ValueError(
                        "The task set has changed. Please delete the existing file or use a different save_to name."
                    )
                # Check which of the runs have already been done
                done_runs = set(
                    [
                        (sim.trial, sim.task_id, sim.seed)
                        for sim in prev_simulation_results.simulations
                    ]
                )
                simulation_results = prev_simulation_results
                console_text = Text(
                    text=f"Resuming run from {len(done_runs)} runs. {len(tasks) * num_trials - len(done_runs)} runs remaining.",
                    style="bold yellow",
                )
                ConsoleDisplay.console.print(console_text)
        # Create new save file
        else:
            # Check if save_to exists and create parent directories if needed
            if not save_to.parent.exists():
                save_to.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"Saving simulation batch to {save_to}")
            with open(save_to, "w") as fp:
                fp.write(simulation_results.model_dump_json(indent=2))

    def _save(simulation: SimulationRun):
        if save_to is None:
            return
        with lock:
            with open(save_to, "r") as fp:
                ckpt = json.load(fp)
            ckpt["simulations"].append(simulation.model_dump())
            with open(save_to, "w") as fp:
                json.dump(ckpt, fp, indent=2)

    def _run(task: Task, trial: int, seed: int, progress_str: str) -> SimulationRun:
        console_text = Text(
            text=f"{progress_str}. Running task {task.id}, trial {trial + 1}",
            style="bold green",
        )
        ConsoleDisplay.console.print(console_text)
        try:
            simulation = run_task(
                domain=domain,
                task=task,
                agent=agent,
                user=user,
                llm_agent=llm_agent,
                llm_args_agent=llm_args_agent,
                llm_user=llm_user,
                llm_args_user=llm_args_user,
                max_steps=max_steps,
                max_errors=max_errors,
                evaluation_type=evaluation_type,
                seed=seed,
                enforce_communication_protocol=enforce_communication_protocol,
            )
            simulation.trial = trial
            if console_display:
                ConsoleDisplay.display_simulation(simulation, show_details=False)
            _save(simulation)
        except Exception as e:
            logger.error(f"Error running task {task.id}, trial {trial}: {e}")
            raise e
        return simulation

    args = []
    for trial in range(num_trials):
        for i, task in enumerate(tasks):
            if (trial, task.id, seeds[trial]) in done_runs:
                console_text = Text(
                    text=f"Skipping task {task.id}, trial {trial} because it has already been run.",
                    style="bold yellow",
                )
                ConsoleDisplay.console.print(console_text)
                continue
            progress_str = f"{i}/{len(tasks)} (trial {trial + 1}/{num_trials})"
            args.append((task, trial, seeds[trial], progress_str))

    with ThreadPoolExecutor(max_workers=max_concurrency) as executor:
        res = list(executor.map(_run, *zip(*args)))
        simulation_results.simulations.extend(res)
    ConsoleDisplay.console.print(
        "\n✨ [bold green]Successfully completed all simulations![/bold green]\n"
        "To review the simulations, run: [bold blue]tau2 view[/bold blue]"
    )
    return simulation_results


def run_task(
    domain: str,
    task: Task,
    agent: str,
    user: str,
    llm_agent: Optional[str] = None,
    llm_args_agent: Optional[dict] = None,
    llm_user: Optional[str] = None,
    llm_args_user: Optional[dict] = None,
    max_steps: int = 100,
    max_errors: int = 10,
    evaluation_type: EvaluationType = EvaluationType.ALL,
    seed: Optional[int] = None,
    enforce_communication_protocol: bool = False,
) -> SimulationRun:
    """
    Runs tasks for a given domain.
     If llm_as_judge is True, the LLM will be used to annotate the simulation run.
     Calculates the reward for the simulation run.
     Args:
         domain (str): The domain to run the simulation on.
         task (Task): The task to run.
         agent (str): The agent to run the simulation on.
         user (str): The user to run the simulation on.
         llm_agent (str): The model to use for the agent.
         llm_args_agent (dict): The arguments to pass to the LLM for the agent.
         llm_user (str): The model to use for the user.
         llm_args_user (dict): The arguments to pass to the LLM for the user.
         max_steps (int): The maximum number of steps to run the simulation.
         max_errors (int): The maximum number of errors to allow in the simulation.
         evaluation_type (EvaluationType): The type of evaluation to use.
         seed (int): The seed to use for the simulation.
         enforce_communication_protocol (bool): Whether to enforce communication protocol rules.
     Returns:
         The simulation run.
    """

    if max_steps <= 0:
        raise ValueError("Max steps must be greater than 0")
    if max_errors <= 0:
        raise ValueError("Max errors must be greater than 0")
    global registry
    logger.info(
        f"STARTING SIMULATION: Domain: {domain}, Task: {task.id}, Agent: {agent}, User: {user}"
    )
    environment_constructor = registry.get_env_constructor(domain)
    environment = environment_constructor()
    AgentConstructor = registry.get_agent_constructor(agent)

    solo_mode = False
    if issubclass(AgentConstructor, LLMAgent):
        agent = AgentConstructor(
            tools=environment.get_tools(),
            domain_policy=environment.get_policy(),
            llm=llm_agent,
            llm_args=llm_args_agent,
        )
    elif issubclass(AgentConstructor, LLMGTAgent):
        agent = AgentConstructor(
            tools=environment.get_tools(),
            domain_policy=environment.get_policy(),
            llm=llm_agent,
            llm_args=llm_args_agent,
            task=task,
        )
    elif issubclass(AgentConstructor, LLMSoloAgent):
        solo_mode = True
        environment: Environment = environment_constructor(solo_mode=True)
        user_tools = environment.get_user_tools() if environment.user_tools else []
        agent = AgentConstructor(
            tools=environment.get_tools() + user_tools,
            domain_policy=environment.get_policy(),
            llm=llm_agent,
            llm_args=llm_args_agent,
            task=task,
        )
    elif GymAgent is not None and issubclass(AgentConstructor, GymAgent):
        agent = AgentConstructor(
            tools=environment.get_tools(),
            domain_policy=environment.get_policy(),
        )
    else:
        raise ValueError(
            f"Unknown agent type: {AgentConstructor}. Should be LLMAgent or LLMSoloAgent"
        )
    try:
        user_tools = environment.get_user_tools()
    except Exception:
        user_tools = None

    UserConstructor = registry.get_user_constructor(user)
    if issubclass(UserConstructor, DummyUser):
        assert isinstance(
            agent, LLMSoloAgent
        ), "Dummy user can only be used with solo agent"

    user = UserConstructor(
        tools=user_tools,
        instructions=str(task.user_scenario),
        llm=llm_user,
        llm_args=llm_args_user,
    )

    orchestrator = Orchestrator(
        domain=domain,
        agent=agent,
        user=user,
        environment=environment,
        task=task,
        max_steps=max_steps,
        max_errors=max_errors,
        seed=seed,
        solo_mode=solo_mode,
        validate_communication=enforce_communication_protocol,
    )
    simulation = orchestrator.run()

    reward_info = evaluate_simulation(
        domain=domain,
        task=task,
        simulation=simulation,
        evaluation_type=evaluation_type,
        solo_mode=solo_mode,
    )

    simulation.reward_info = reward_info

    logger.info(
        f"FINISHED SIMULATION: Domain: {domain}, Task: {task.id}, Agent: {agent.__class__.__name__}, User: {user.__class__.__name__}. Reward: {reward_info.reward}"
    )
    return simulation


def get_info(
    domain: str,
    agent: str,
    user: str,
    llm_agent: Optional[str] = None,
    llm_args_agent: Optional[dict] = None,
    llm_user: Optional[str] = None,
    llm_args_user: Optional[dict] = None,
    num_trials: int = 1,
    max_steps: int = 100,
    max_errors: int = 10,
    seed: Optional[int] = None,
) -> Info:
    user_info = UserInfo(
        implementation=user,
        llm=llm_user,
        llm_args=llm_args_user,
        global_simulation_guidelines=get_global_user_sim_guidelines(),
    )
    agent_info = AgentInfo(
        implementation=agent,
        llm=llm_agent,
        llm_args=llm_args_agent,
    )
    environment_info = get_environment_info(
        domain, include_tool_info=False
    )  # NOTE: Not saving tool info to avoid clutter.
    return Info(
        git_commit=get_commit_hash(),
        num_trials=num_trials,
        max_steps=max_steps,
        max_errors=max_errors,
        user_info=user_info,
        agent_info=agent_info,
        environment_info=environment_info,
        seed=seed,
    )
