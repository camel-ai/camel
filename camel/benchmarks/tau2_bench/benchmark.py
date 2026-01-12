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
r"""τ²-Bench integration that reuses CAMEL ``ChatAgent`` instances."""

from __future__ import annotations

import logging
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from tau2.data_model.simulation import Results, SimulationRun
from tau2.data_model.tasks import Task, UserScenario
from tau2.evaluator.evaluator import EvaluationType, evaluate_simulation
from tau2.metrics.agent_metrics import compute_metrics
from tau2.orchestrator.orchestrator import Orchestrator
from tau2.registry import registry
from tau2.run import get_info, get_tasks
from tau2.agent.llm_agent import AGENT_INSTRUCTION, SYSTEM_PROMPT
from tau2.user.user_simulator import (
    SYSTEM_PROMPT as USER_SYSTEM_PROMPT,
)
from tau2.user.user_simulator import (
    get_global_user_sim_guidelines,
)

from camel.agents import ChatAgent
from camel.benchmarks.base import BaseBenchmark
from camel.benchmarks.tau2_bench.adapters import CamelTau2Agent, CamelTau2User
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

logger = logging.getLogger(__name__)

DEFAULT_DATA_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_SAVE_DIR = Path("./results/tau2_bench")


def _toolkit_to_schemas(toolkit: Sequence) -> List[dict]:
    schemas: List[dict] = []
    for tool in toolkit:
        try:
            schema = dict(tool.openai_schema)
            function_block = schema.get("function", {})
            schema.setdefault("name", function_block.get("name"))
            schemas.append(schema)
        except AttributeError:
            logger.warning("Skipping tool without OpenAI schema: %s", tool)
    return schemas


class Tau2BenchBenchmark(BaseBenchmark):
    r"""Benchmark wrapper that proxies τ² runs through CAMEL agents."""

    def __init__(
        self,
        domain: str = "airline",
        data_dir: Path | str = DEFAULT_DATA_DIR,
        save_to: Path | str = DEFAULT_SAVE_DIR,
        processes: int = 1,
        user_model: ModelType | str = ModelType.GPT_4O_MINI,
        user_model_platform: (
            ModelPlatformType | str
        ) = ModelPlatformType.OPENAI,
        user_model_config: Optional[Dict] = None,
        task_set_name: Optional[str] = None,
    ):
        super().__init__(
            name="tau2_bench",
            data_dir=str(data_dir),
            save_to=str(save_to),
            processes=processes,
        )
        self.domain = domain
        self.task_set_name: Optional[str] = task_set_name
        self._tasks_by_split: Dict[str, List[Task]] = {}
        self._tau2_results: Optional[Results] = None
        self._last_results_path: Optional[Path] = None
        self.user_model_type = self._resolve_model_type(user_model)
        self.user_model_platform = self._resolve_model_platform(
            user_model_platform
        )
        default_user_config = {"temperature": 0.0}
        self.user_model_config = dict(user_model_config or default_user_config)

    @staticmethod
    def _resolve_model_type(value: ModelType | str) -> ModelType:
        if isinstance(value, ModelType):
            return value
        return ModelType(value)

    @staticmethod
    def _resolve_model_platform(
        value: ModelPlatformType | str,
    ) -> ModelPlatformType:
        if isinstance(value, ModelPlatformType):
            return value
        return ModelPlatformType(value)

    def download(self) -> "Tau2BenchBenchmark":
        logger.info(
            "τ²-Bench data is vendored with CAMEL; nothing to download."
        )
        return self

    def load(self, force_download: bool = False) -> "Tau2BenchBenchmark":
        tasks = self._ensure_tasks(split_name="base")
        self._data = {
            "train": tasks,
            "valid": tasks[: min(10, len(tasks))],
            "test": tasks,
        }
        return self

    def set_task_set_name(self, task_set_name: Optional[str]) -> None:
        r"""Override the task set used for loading tasks.

        Args:
            task_set_name: Name registered in τ²'s registry. ``None`` means
                defaulting to the benchmark domain (current behavior).
        """
        if task_set_name == self.task_set_name:
            return
        self.task_set_name = task_set_name
        self._tasks_by_split.clear()

    def _resolve_task_set(self) -> str:
        return self.task_set_name or self.domain

    def _ensure_tasks(self, split_name: str) -> List[Task]:
        if split_name not in self._tasks_by_split:
            self._tasks_by_split[split_name] = get_tasks(
                task_set_name=self._resolve_task_set(),
                task_split_name=split_name,
            )
        return self._tasks_by_split[split_name]

    def run(
        self,
        agent: ChatAgent,
        on: str = "test",
        randomize: bool = False,
        subset: Optional[int] = None,
        task_split_name: str = "base",
        task_set_name: Optional[str] = None,
        task_ids: Optional[List[str]] = None,
        num_trials: int = 1,
        num_tasks: Optional[int] = None,
        max_steps: int = 100,
        max_errors: int = 10,
        seed: Optional[int] = 300,
        enforce_communication_protocol: bool = False,
        evaluation_type: str = "all",
        save_to: Optional[str] = None,
        user_model: Optional[str] = None,
        user_model_platform: Optional[str] = None,
        user_model_config: Optional[Dict] = None,
        max_concurrency: int = 1,
    ) -> "Tau2BenchBenchmark":
        del on  # present for BaseBenchmark compatibility

        if task_set_name is not None:
            self.set_task_set_name(task_set_name)

        tasks = self._ensure_tasks(task_split_name)
        selected_tasks = self._select_tasks(
            tasks=tasks,
            task_ids=task_ids,
            limit=num_tasks or subset,
            randomize=randomize,
            seed=seed,
        )
        if not selected_tasks:
            raise ValueError("No tasks selected for τ²-Bench run.")

        eval_type = EvaluationType(evaluation_type.lower())
        rng = random.Random(seed or 0)
        trial_seeds = [rng.randint(0, 1_000_000) for _ in range(num_trials)]

        user_model_type = self._resolve_model_type(
            user_model or self.user_model_type
        )
        user_model_platform = self._resolve_model_platform(
            user_model_platform or self.user_model_platform
        )
        user_model_cfg = dict(self.user_model_config)
        if user_model_config:
            user_model_cfg.update(user_model_config)

        info = get_info(
            domain=self.domain,
            agent="camel_chat_agent",
            user="camel_chat_user_simulator",
            llm_agent=self._infer_model_name(agent),
            llm_args_agent={},
            llm_user=user_model_type.value,
            llm_args_user=deepcopy(user_model_cfg),
            num_trials=num_trials,
            max_steps=max_steps,
            max_errors=max_errors,
            seed=seed,
        )
        self._tau2_results = Results(
            info=info,
            tasks=selected_tasks,
            simulations=[],
        )
        self._results = []

        jobs = [
            (trial_idx, task, trial_seeds[trial_idx])
            for trial_idx in range(num_trials)
            for task in selected_tasks
        ]
        if max_concurrency <= 0:
            max_concurrency = 1

        def _submit_job(trial_idx: int, task: Task, seed_value: int):
            logger.info(
                "Running τ² task %s (trial %s/%s)",
                task.id,
                trial_idx + 1,
                num_trials,
            )
            return self._run_single_task(
                base_agent=agent,
                task=task,
                trial_index=trial_idx,
                seed=seed_value,
                max_steps=max_steps,
                max_errors=max_errors,
                enforce_protocol=enforce_communication_protocol,
                eval_type=eval_type,
                user_model_type=user_model_type,
                user_model_platform=user_model_platform,
                user_model_config=dict(user_model_cfg),
            )

        if max_concurrency == 1:
            for job in jobs:
                simulation = _submit_job(*job)
                self._record_simulation(simulation)
        else:
            with ThreadPoolExecutor(max_workers=max_concurrency) as executor:
                future_to_job = {
                    executor.submit(_submit_job, *job): job for job in jobs
                }
                for future in as_completed(future_to_job):
                    simulation = future.result()
                    self._record_simulation(simulation)

        self._persist_results(save_to)
        return self

    def _record_simulation(self, simulation: SimulationRun) -> None:
        if not self._tau2_results:
            return
        self._tau2_results.simulations.append(simulation)
        reward = (
            simulation.reward_info.reward if simulation.reward_info else 0.0
        )
        termination_reason = (
            simulation.termination_reason.value
            if hasattr(simulation.termination_reason, "value")
            else simulation.termination_reason
        )
        self._results.append(
            {
                "task_id": simulation.task_id,
                "trial": simulation.trial,
                "reward": reward,
                "termination_reason": termination_reason,
            }
        )

    def _select_tasks(
        self,
        tasks: Iterable[Task],
        task_ids: Optional[List[str]],
        limit: Optional[int],
        randomize: bool,
        seed: Optional[int],
    ) -> List[Task]:
        if task_ids:
            lookup = {str(tid) for tid in task_ids}
            filtered = [task for task in tasks if str(task.id) in lookup]
            missing = lookup - {str(task.id) for task in filtered}
            if missing:
                raise ValueError(f"Unknown task ids: {sorted(missing)}")
        else:
            filtered = list(tasks)

        if randomize:
            rng = random.Random(seed or 0)
            rng.shuffle(filtered)

        if limit is not None:
            filtered = filtered[: min(limit, len(filtered))]
        return filtered

    def _run_single_task(
        self,
        base_agent: ChatAgent,
        task: Task,
        trial_index: int,
        seed: int,
        max_steps: int,
        max_errors: int,
        enforce_protocol: bool,
        eval_type: EvaluationType,
        user_model_type: ModelType,
        user_model_platform: ModelPlatformType,
        user_model_config: Dict,
    ) -> SimulationRun:
        env_constructor = registry.get_env_constructor(self.domain)
        environment = env_constructor()
        assistant_tools = _toolkit_to_schemas(environment.get_tools())
        try:
            user_tools = _toolkit_to_schemas(environment.get_user_tools())
        except Exception:
            user_tools = []

        agent_clone, agent_system_prompt = self._clone_agent_with_policy(
            base_agent=base_agent,
            policy_text=environment.get_policy(),
        )
        agent_adapter = CamelTau2Agent(
            chat_agent=agent_clone,
            tool_schemas=assistant_tools,
            system_prompt=agent_system_prompt,
        )
        self._ensure_agent_model_config(agent_clone, bool(assistant_tools))
        user_adapter = self._build_user_adapter(
            scenario=task.user_scenario,
            user_tools=user_tools,
            model_type=user_model_type,
            model_platform=user_model_platform,
            model_config=user_model_config,
        )

        orchestrator = Orchestrator(
            domain=self.domain,
            agent=agent_adapter,
            user=user_adapter,
            environment=environment,
            task=task,
            max_steps=max_steps,
            max_errors=max_errors,
            seed=seed,
            validate_communication=enforce_protocol,
        )
        simulation = orchestrator.run()
        reward_info = evaluate_simulation(
            simulation=simulation,
            task=task,
            evaluation_type=eval_type,
            solo_mode=False,
            domain=self.domain,
        )
        simulation.reward_info = reward_info
        simulation.trial = trial_index
        simulation.seed = seed
        return simulation

    def _build_user_adapter(
        self,
        scenario: UserScenario,
        user_tools: Sequence[dict],
        model_type: ModelType,
        model_platform: ModelPlatformType,
        model_config: Dict,
    ) -> CamelTau2User:
        system_prompt = self._build_user_system_prompt(
            scenario=scenario,
            has_tools=bool(user_tools),
        )
        if model_config.get("tool_choice") is None and user_tools:
            model_config["tool_choice"] = "auto"
        user_model = ModelFactory.create(
            model_platform=model_platform,
            model_type=model_type,
            model_config_dict=dict(model_config),
        )
        chat_agent = ChatAgent(
            system_message=system_prompt,
            model=user_model,
        )
        return CamelTau2User(
            chat_agent=chat_agent,
            tool_schemas=user_tools,
            system_prompt=system_prompt,
        )

    def _build_user_system_prompt(
        self,
        scenario: UserScenario,
        has_tools: bool,
    ) -> str:
        guidelines = get_global_user_sim_guidelines(use_tools=has_tools)
        return USER_SYSTEM_PROMPT.format(
            global_user_sim_guidelines=guidelines,
            instructions=str(scenario),
        )

    def _clone_agent_with_policy(
        self,
        base_agent: ChatAgent,
        policy_text: str,
    ) -> tuple[ChatAgent, str]:
        r"""Clone agent with policy and return both clone and system prompt.

        Returns:
            Tuple of (cloned ChatAgent, system prompt string)
        """
        agent_clone = base_agent.clone(with_memory=False)
        policy_body = policy_text.strip()
        combined = SYSTEM_PROMPT.format(
            domain_policy=policy_body, agent_instruction=AGENT_INSTRUCTION
        )
        system_prompt = combined.strip()
        system_message = BaseMessage.make_assistant_message(
            role_name="System",
            content=system_prompt,
        )
        agent_clone._system_message = system_message  # type: ignore[attr-defined]
        agent_clone._original_system_message = system_message  # type: ignore[attr-defined]
        agent_clone.reset()
        return agent_clone, system_prompt

    def _ensure_agent_model_config(
        self, agent: ChatAgent, has_tools: bool
    ) -> None:
        backend = getattr(agent, "model_backend", None)
        if backend is None:
            return
        config = dict(getattr(backend, "model_config_dict", {}))
        if config.get("temperature") is None:
            config["temperature"] = 0.0
        if has_tools and config.get("tool_choice") is None:
            config["tool_choice"] = "auto"
        backend.model_config_dict = config

    def _infer_model_name(self, agent: ChatAgent) -> str:
        backend = getattr(agent, "model_backend", None)
        model_type = getattr(backend, "model_type", None)
        if isinstance(model_type, ModelType):
            return model_type.value
        if isinstance(model_type, str):
            return model_type
        return getattr(backend, "model_name", "unknown")

    def _persist_results(self, override: Optional[str]) -> None:
        if not self._tau2_results:
            return
        save_root = Path(override or self.save_to)
        if save_root.is_dir() or not save_root.suffix:
            save_root.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            output_path = save_root / f"{timestamp}_{self.domain}.json"
        else:
            save_root.parent.mkdir(parents=True, exist_ok=True)
            output_path = save_root

        output_path.write_text(self._tau2_results.model_dump_json(indent=2))
        self._last_results_path = output_path
        logger.info("Saved τ²-Bench results to %s", output_path)

    def evaluate(self) -> Dict[str, float]:
        if not self._tau2_results or not self._tau2_results.simulations:
            logger.warning("No τ²-Bench runs to evaluate.")
            return {}
        metrics = compute_metrics(self._tau2_results)
        return metrics.as_dict()
