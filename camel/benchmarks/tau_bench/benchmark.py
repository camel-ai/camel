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
"""Tau-Bench: Tool-Agent-User interaction benchmark.

This module provides a clean interface to the original Tau-Bench benchmark,
allowing easy evaluation of CAMEL agents on complex service scenarios while
reusing the CAMEL ``ChatAgent`` runtime.

Reference:
    https://github.com/sierra-research/tau-bench
    https://arxiv.org/abs/2406.12045
"""

import json
import logging
import random
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from math import comb
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from camel.agents import ChatAgent
from camel.benchmarks.base import BaseBenchmark
from camel.benchmarks.tau_bench.types import AgentStrategy, TaskResult
from camel.messages import BaseMessage
from camel.toolkits import FunctionTool

from .types import RESPOND_ACTION_NAME, Action

logger = logging.getLogger(__name__)


class TauBenchBenchmark(BaseBenchmark):
    r"""Tau-Bench benchmark for evaluating tool-agent-user interaction.

    This benchmark tests agents on realistic customer service scenarios where
    they must use domain-specific tools, follow policies, and interact with
    simulated users to complete tasks.

    Supports two domains:
    - airline: Flight booking, changes, cancellations
    - retail: Order management, returns, address updates

    Args:
        data_dir (str): Directory for tau-bench data (embedded; no download).
        save_to (str): Directory to store results
            (default: "./results/tau_bench").
        domain (str): Target domain, either "airline" or "retail".
        user_strategy (str): User simulation strategy to load.
        user_model (str): Model identifier for the user simulator.
        user_provider (str): Provider for the user simulator.
        processes (int): Number of parallel processes to use.
    """

    def __init__(
        self,
        data_dir: str = "./data/tau_bench",
        save_to: str = "./results/tau_bench",
        domain: str = "airline",
        user_strategy: str = "llm",
        user_model: str = "gpt-4.1",
        user_provider: str = "openai",
        processes: int = 1,
        user_temperature: float = 0.0,
    ):
        r"""Initialize Tau-Bench benchmark.

        Args:
            data_dir: Data directory (not used, kept for compatibility)
            save_to: Results save directory
            domain: 'airline' or 'retail'
            user_strategy: User simulation strategy
            user_model: Model for user agent
            user_provider: Provider for user model (openai, anthropic, etc.)
            processes: Number of parallel processes
            user_temperature: Sampling temperature for the user simulator LLM
        """
        super().__init__(
            name="tau_bench",
            data_dir=data_dir,
            save_to=save_to,
            processes=processes,
        )

        if domain not in ["airline", "retail"]:
            message = f"Domain must be 'airline' or 'retail', got {domain}"
            raise ValueError(message)

        self.domain = domain
        self.user_strategy = user_strategy
        self.user_model = user_model
        self.user_provider = user_provider
        self.user_temperature = user_temperature

        # Will be loaded in load()
        self.tau_bench_env = None
        self.tasks_list = []

    def download(self) -> "TauBenchBenchmark":
        r"""Download benchmark data.

        For Tau-Bench, data is embedded in the package, so this is a no-op.

        Returns:
            TauBenchBenchmark: self
        """
        logger.info(
            "Tau-Bench data is embedded in the package, no download needed."
        )
        return self

    def load(self, force_download: bool = False) -> "TauBenchBenchmark":
        r"""Load Tau-Bench environment and tasks.

        Args:
            force_download: Not used for Tau-Bench

        Returns:
            TauBenchBenchmark: self
        """
        logger.info(
            "Loading Tau-Bench environment for domain: %s",
            self.domain,
        )

        try:
            # Import original tau-bench code
            from tau_bench.envs import get_env

            # Create environment (this loads tasks internally)
            self.tau_bench_env = get_env(
                env_name=self.domain,
                user_strategy=self.user_strategy,
                user_model=self.user_model,
                user_provider=self.user_provider,
                task_split="test",  # Default to test split
                user_temperature=self.user_temperature,
            )

            # Get tasks
            self.tasks_list = self.tau_bench_env.tasks
            logger.info("Loaded %s tasks", len(self.tasks_list))

            # Populate data splits
            self._data = {
                "train": self.tasks_list,
                "valid": (
                    self.tasks_list[:10]
                    if len(self.tasks_list) > 10
                    else self.tasks_list
                ),
                "test": self.tasks_list,
            }

        except ImportError as e:
            logger.error(f"Failed to import tau_bench: {e}")
            logger.error("Make sure the envs directory is properly set up")
            raise

        return self

    def run(
        self,
        agent: ChatAgent,
        on: str = "test",  # Follows BaseBenchmark interface
        randomize: bool = False,  # Follows BaseBenchmark interface
        subset: Optional[int] = None,  # Follows BaseBenchmark interface
        task_split: Optional[str] = None,  # tau-bench data split (deprecated)
        start_index: int = 0,
        end_index: int = -1,
        task_ids: Optional[List[int]] = None,
        num_trials: int = 1,
        agent_strategy: str = "tool-calling",
        temperature: float = 0.0,
        max_steps: int = 30,
        max_concurrency: int = 1,
        seed: int = 10,
        shuffle: bool = False,
        model_name: Optional[str] = None,
        model_provider: Optional[str] = None,
        *args,
        **kwargs,
    ) -> "TauBenchBenchmark":
        r"""Run the benchmark and mirror the original τ-bench parameters.

        Args:
            agent: CAMEL ``ChatAgent`` to evaluate.
            on: BaseBenchmark split ("train", "valid", or "test").
            randomize: Whether to randomize task order (maps to shuffle).
            subset: Number of tasks to run (maps to ``end_index``).
            task_split: Legacy τ-bench split ("train", "test", or "dev").
            start_index: Start task index (inclusive).
            end_index: End task index (exclusive, ``-1`` for all).
            task_ids: Explicit task IDs to run (overrides indices).
            num_trials: Number of trials per task (for Pass@k).
            agent_strategy: "tool-calling", "act", or "react".
            temperature: Sampling temperature for the assistant LLM.
            max_steps: Maximum assistant turns per task.
            max_concurrency: Number of tasks to run in parallel.
            seed: Random seed used for shuffling logic.
            shuffle: Whether to shuffle task order.
            model_name: Optional model name for logging.
            model_provider: Optional model provider for logging.

        Returns:
            TauBenchBenchmark: self
        """
        # Map BaseBenchmark interface to τ-bench parameters.
        if task_split is None:
            task_split = on  # Use 'on' if task_split not provided
        if randomize:
            shuffle = True  # Map randomize to shuffle
        if subset is not None:
            end_index = start_index + subset  # Map subset to end_index

        if self.tau_bench_env is None:
            logger.info("Environment not loaded, loading now...")
            self.load()

        # Set random seed
        random.seed(seed)

        # Auto-detect model info
        if model_name is None:
            if hasattr(agent, "model_type"):
                model_name = str(agent.model_type).split(".")[-1]
            else:
                model_name = "unknown"
        if model_provider is None:
            model_provider = "openai"  # default

        # Generate checkpoint path (same format as original tau-bench)
        time_str = datetime.now().strftime("%m%d%H%M%S")
        model_short = model_name.split('/')[-1]
        ckpt_filename = (
            f"{agent_strategy}-{model_short}-{temperature}_"
            f"range_{start_index}-{end_index}_"
            f"user-{self.user_model}-{self.user_strategy}_{time_str}.json"
        )
        ckpt_path = Path(self.save_to) / ckpt_filename
        ckpt_path.parent.mkdir(parents=True, exist_ok=True)

        # Determine task range
        total_tasks = len(self.tasks_list)
        if end_index == -1:
            end_index = total_tasks
        else:
            end_index = min(end_index, total_tasks)

        # Print configuration (matching original format)
        logger.info("Loading user with strategy: %s", self.user_strategy)
        if task_ids and len(task_ids) > 0:
            logger.info(
                "Running tasks %s (checkpoint path: %s)",
                task_ids,
                ckpt_path,
            )
        else:
            logger.info(
                "Running tasks %s to %s (checkpoint path: %s)",
                start_index,
                end_index,
                ckpt_path,
            )

        try:
            strategy_enum = AgentStrategy(agent_strategy)
        except ValueError as exc:
            message = f"Unsupported agent_strategy '{agent_strategy}'"
            raise ValueError(message) from exc
        if strategy_enum is not AgentStrategy.TOOL_CALLING:
            not_impl_msg = (
                "TauBenchBenchmark currently supports only the tool-calling "
                "strategy when running through CAMEL ChatAgents."
            )
            raise NotImplementedError(not_impl_msg)

        if agent is None:
            msg = "A ChatAgent instance must be provided to run Tau-Bench."
            raise ValueError(msg)

        # Run trials
        results = []
        for trial_idx in range(num_trials):
            # Determine task indices for this trial
            if task_ids and len(task_ids) > 0:
                idxs = task_ids
            else:
                idxs = list(range(start_index, end_index))

            if shuffle:
                random.shuffle(idxs)

            # Define function to run single task
            def _run_task(
                task_idx: int,
                trial_index: int = trial_idx,
            ) -> TaskResult:
                logger.info("Running task %s", task_idx)
                try:
                    # Import tau-bench components
                    from tau_bench.envs import get_env

                    # Create fresh environment for this task
                    task_env = get_env(
                        env_name=self.domain,
                        user_strategy=self.user_strategy,
                        user_model=self.user_model,
                        user_provider=self.user_provider,
                        task_split=task_split,
                        task_index=task_idx,
                        user_temperature=self.user_temperature,
                    )

                    # Run task with CAMEL ChatAgent
                    solve_payload = self._solve_task_with_chat_agent(
                        base_agent=agent,
                        env=task_env,
                        task_index=task_idx,
                        max_num_steps=max_steps,
                        temperature=temperature,
                    )

                    task_result = TaskResult(
                        task_id=task_idx,
                        reward=solve_payload["reward"],
                        traj=solve_payload["traj"],
                        info=solve_payload["info"],
                        trial=trial_index,
                    )

                    # Print result (matching original format)
                    status = "✅" if task_result.reward == 1 else "❌"
                    logger.info(
                        "%s task_id=%s %s",
                        status,
                        task_idx,
                        task_result.info,
                    )
                    logger.info("-----")

                    return task_result

                except Exception as e:
                    error_info = {
                        "error": str(e),
                        "traceback": traceback.format_exc(),
                    }
                    logger.error("❌ task_id=%s %s", task_idx, error_info)
                    logger.info("-----")

                    return TaskResult(
                        task_id=task_idx,
                        reward=0.0,
                        traj=[],
                        info=error_info,
                        trial=trial_index,
                    )

            # Run tasks (with optional parallelism)
            if max_concurrency > 1:
                with ThreadPoolExecutor(
                    max_workers=max_concurrency,
                ) as executor:
                    trial_results = list(executor.map(_run_task, idxs))
            else:
                trial_results = [_run_task(idx) for idx in idxs]

            results.extend(trial_results)

            # Save incremental results after each trial
            self._save_checkpoint(ckpt_path, results)

        # Store results
        self._results = [vars(r) for r in results]

        # Display metrics (matching original format)
        self._display_metrics(results)

        # Save final results
        with open(ckpt_path, "w") as f:
            json.dump(self._results, f, indent=2)
        logger.info("Results saved to %s", ckpt_path)

        return self

    def _solve_task_with_chat_agent(
        self,
        base_agent: ChatAgent,
        env,
        task_index: int,
        max_num_steps: int,
        temperature: float,
    ) -> Dict[str, Any]:
        """Runs a single Tau-Bench task using the provided ChatAgent."""

        # Reset environment to obtain initial observation
        env_reset = env.reset(task_index=task_index)
        shared_state: Dict[str, Any] = {
            "info": env_reset.info.model_dump(),
            "reward": 0.0,
            "done": False,
        }

        traj: List[Dict[str, Any]] = [
            {"role": "system", "content": env.wiki},
            {"role": "user", "content": env_reset.observation},
        ]

        task_agent = self._prepare_task_agent(
            base_agent=base_agent,
            env=env,
            wiki=env.wiki,
            temperature=temperature,
            message_log=traj,
            state=shared_state,
        )

        observation = env_reset.observation
        for _ in range(max_num_steps):
            response = task_agent.step(observation)

            if shared_state["done"] or response.terminated:
                break

            assistant_msg = response.msg.content if response.msg else ""
            if not assistant_msg:
                break

            traj.append({"role": "assistant", "content": assistant_msg})
            env_response = env.step(
                Action(
                    name=RESPOND_ACTION_NAME,
                    kwargs={"content": assistant_msg},
                )
            )
            shared_state["info"] = {
                **shared_state["info"],
                **env_response.info.model_dump(),
            }

            if env_response.done:
                shared_state["done"] = True
                shared_state["reward"] = env_response.reward
                break

            observation = env_response.observation
            traj.append({"role": "user", "content": observation})

        run_info = dict(shared_state["info"]) if shared_state["info"] else {}

        return {
            "reward": shared_state["reward"],
            "traj": traj,
            "info": run_info,
        }

    def _prepare_task_agent(
        self,
        base_agent: ChatAgent,
        env,
        wiki: str,
        temperature: float,
        message_log: List[Dict[str, Any]],
        state: Dict[str, Any],
    ) -> ChatAgent:
        """Clone and configure the provided ChatAgent for a specific task."""
        task_agent = base_agent.clone(with_memory=False)

        system_message = BaseMessage.make_assistant_message(
            role_name="System",
            content=wiki,
        )
        task_agent._system_message = system_message  # type: ignore[attr-defined]
        task_agent._original_system_message = system_message  # type: ignore[attr-defined]

        if temperature is not None:
            model_config = dict(task_agent.model_backend.model_config_dict)
            model_config["temperature"] = temperature
            task_agent.model_backend.model_config_dict = model_config

        self._attach_env_tools(task_agent, env, message_log, state)
        task_agent.reset()
        return task_agent

    def _attach_env_tools(
        self,
        agent: ChatAgent,
        env,
        message_log: List[Dict[str, Any]],
        state: Dict[str, Any],
    ) -> None:
        """Replace the agent's tools with the environment's toolset."""
        existing_tools = list(agent.tool_dict.keys())
        if existing_tools:
            agent.remove_tools(existing_tools)

        tools = list(self._build_tool_functions(env, message_log, state))
        if tools:
            agent.add_tools(tools)

    def _build_tool_functions(
        self,
        env,
        message_log: List[Dict[str, Any]],
        state: Dict[str, Any],
    ) -> Iterable[FunctionTool]:
        """Yield FunctionTool wrappers backed by the Tau-Bench environment."""

        for tool_schema in env.tools_info:
            tool_name = tool_schema["function"]["name"]

            def _tool_callable_factory(name: str):
                def _tool_callable(**kwargs):
                    call_id = f"call_{uuid.uuid4().hex}"
                    arguments_json = json.dumps(kwargs, ensure_ascii=False)
                    message_log.append(
                        {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [
                                {
                                    "id": call_id,
                                    "type": "function",
                                    "function": {
                                        "name": name,
                                        "arguments": arguments_json,
                                    },
                                }
                            ],
                        }
                    )
                    try:
                        env_response = env.step(
                            Action(name=name, kwargs=kwargs)
                        )
                        state["info"] = {
                            **state["info"],
                            **env_response.info.model_dump(),
                        }
                        if env_response.done:
                            state["done"] = True
                            state["reward"] = env_response.reward
                        output = env_response.observation
                    except Exception as exc:  # pragma: no cover - defensive
                        output = f"Error: {exc}"
                    message_log.append(
                        {
                            "role": "tool",
                            "tool_call_id": call_id,
                            "name": name,
                            "content": output,
                        }
                    )
                    return output

                return _tool_callable

            yield FunctionTool(
                func=_tool_callable_factory(tool_name),
                openai_tool_schema=tool_schema,
            )

    def _save_checkpoint(self, ckpt_path: Path, results: List[TaskResult]):
        """Save checkpoint incrementally."""
        with open(ckpt_path, "w") as f:
            json.dump([vars(r) for r in results], f, indent=2)

    def _display_metrics(self, results: List[TaskResult]):
        """Display metrics in original tau-bench format."""

        def is_successful(reward: float) -> bool:
            return (1 - 1e-6) <= reward <= (1 + 1e-6)

        if not results:
            logger.info("No results to display")
            return

        # Calculate average reward
        rewards = [r.reward for r in results]
        avg_reward = sum(rewards) / len(rewards)

        # Calculate Pass^k using original formula
        num_trials = len({result.trial for result in results})
        c_per_task_id: Dict[int, int] = {}

        for result in results:
            if result.task_id not in c_per_task_id:
                c_per_task_id[result.task_id] = (
                    1 if is_successful(result.reward) else 0
                )
            else:
                c_per_task_id[result.task_id] += (
                    1 if is_successful(result.reward) else 0
                )

        pass_hat_ks: Dict[int, float] = {}
        for k in range(1, num_trials + 1):
            sum_task_pass_hat_k = 0
            for c in c_per_task_id.values():
                if comb(num_trials, k) > 0:
                    sum_task_pass_hat_k += comb(c, k) / comb(num_trials, k)
            pass_hat_ks[k] = sum_task_pass_hat_k / len(c_per_task_id)

        # Print metrics (matching original format)
        logger.info("🏆 Average reward: %s", avg_reward)
        logger.info("📈 Pass^k")
        for k, pass_hat_k in pass_hat_ks.items():
            logger.info("  k=%s: %s", k, pass_hat_k)

    def evaluate(self) -> Dict[str, float]:
        r"""Evaluate benchmark results.

        Returns:
            Dict with metrics: pass@1, pass@k, avg_reward, etc.
        """
        if not self._results:
            logger.warning("No results to evaluate")
            return {}

        def is_successful(reward: float) -> bool:
            return (1 - 1e-6) <= reward <= (1 + 1e-6)

        # Calculate Pass@1
        success_count = sum(
            1 for result in self._results if is_successful(result["reward"])
        )
        total_tasks = len({result["task_id"] for result in self._results})
        pass_at_1 = (
            success_count / len(self._results) if self._results else 0.0
        )

        # Calculate average reward
        reward_sum = sum(result["reward"] for result in self._results)
        avg_reward = reward_sum / len(self._results) if self._results else 0.0

        metrics = {
            "pass@1": pass_at_1,
            "avg_reward": avg_reward,
            "total_tasks": total_tasks,
            "total_runs": len(self._results),
            "successful_runs": success_count,
        }

        # Calculate Pass@k if multiple trials
        num_trials = len({result["trial"] for result in self._results})
        if num_trials > 1:
            c_per_task_id: Dict[int, int] = {}
            for r in self._results:
                task_id = r["task_id"]
                if task_id not in c_per_task_id:
                    c_per_task_id[task_id] = (
                        1 if is_successful(r["reward"]) else 0
                    )
                else:
                    c_per_task_id[task_id] += (
                        1 if is_successful(r["reward"]) else 0
                    )

            for k in range(1, num_trials + 1):
                sum_task_pass_hat_k = 0
                for c in c_per_task_id.values():
                    if comb(num_trials, k) > 0:
                        sum_task_pass_hat_k += comb(c, k) / comb(num_trials, k)
                pass_hat_k = sum_task_pass_hat_k / len(c_per_task_id)
                metrics[f"pass@{k}"] = pass_hat_k

        logger.info(f"Evaluation metrics: {metrics}")
        return metrics
