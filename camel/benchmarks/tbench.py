import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from terminal_bench.agents.base_agent import AgentResult, BaseAgent
from terminal_bench.handlers.asciinema_handler import AsciinemaHandler
from terminal_bench.handlers.trial_handler import TrialHandler
from terminal_bench.harness import Harness
from terminal_bench.harness.models import (
    BenchmarkResults,
    FailureMode,
    RunMetadata,
    TrialResults,
)
from terminal_bench.terminal.terminal import spin_up_terminal
from terminal_bench.terminal.tmux_session import TmuxSession
from terminal_bench.utils.logger import logger

from camel.agents import ChatAgent

from .base import BaseBenchmark


class TerminalBench(Harness):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _execute_single_trial(
        self,
        trial_name: str,
        task_path: Path,
        BaseAgent: BaseAgent,
    ) -> TrialResults:
        """Execute a single task and return its results.

        Args:
            task_path: Path to the task directory

        Returns:
            TrialResults: The results of the trial execution
        """
        trial_handler = TrialHandler(
            trial_name=trial_name,
            input_path=task_path,
            output_path=self._run_path,
        )

        try:
            trial_results = self._run_trial(trial_handler, BaseAgent)

            trial_handler.trial_paths.results_path.write_text(
                trial_results.model_dump_json(indent=4)
            )

            return trial_results

        except Exception as e:
            logger.error(
                f"Harness execution failed for {task_path}: {e}",
                exc_info=True,
            )
            trial_results = TrialResults(
                trial_name=trial_name,
                task_id=trial_handler.task_id,
                instruction=trial_handler.instruction,
                failure_mode=FailureMode.UNKNOWN_AGENT_ERROR,
            )
            return trial_results

    def _run_trial(
        self,
        trial_handler: TrialHandler,
        BaseAgent: BaseAgent,
    ) -> TrialResults:
        self._logger.debug(f"Running task: {trial_handler.task_id}")

        results = TrialResults(
            trial_name=trial_handler.trial_name,
            task_id=trial_handler.task_id,
            instruction=trial_handler.instruction,
        )

        results.trial_started_at = datetime.now(timezone.utc).isoformat()

        with spin_up_terminal(
            client_container_name=trial_handler.client_container_name,
            client_image_name=trial_handler.client_image_name,
            docker_image_name_prefix=trial_handler.docker_image_name_prefix,
            docker_compose_path=trial_handler.task_paths.docker_compose_path,
            sessions_logs_path=trial_handler.trial_paths.sessions_path,
            agent_logs_path=trial_handler.trial_paths.agent_logging_dir,
            commands_path=trial_handler.trial_paths.commands_path,
            no_rebuild=self._no_rebuild,
            cleanup=self._cleanup,
            livestream=self._livestream,
            disable_recording=trial_handler.task.disable_asciinema,
        ) as terminal:
            session = terminal.create_session(
                "agent",
                is_active_stream=self._livestream,
                as_configured_user=True,
            )

            pre_agent_pane = session.capture_pane(capture_entire=True)
            trial_handler.trial_paths.pre_agent_pane_path.write_text(
                pre_agent_pane
            )

            results.agent_started_at = datetime.now(timezone.utc).isoformat()

            agent_result, agent_failure_mode = self._run_agent(
                session=session,
                agent=BaseAgent,
                trial_handler=trial_handler,
            )

            results.agent_ended_at = datetime.now(timezone.utc).isoformat()

            post_agent_pane = session.capture_pane(capture_entire=True)
            trial_handler.trial_paths.post_agent_pane_path.write_text(
                post_agent_pane
            )

            if agent_failure_mode == FailureMode.AGENT_TIMEOUT:
                results.failure_mode = agent_failure_mode
                self._logger.debug(
                    f"Agent failed with mode {agent_failure_mode}, continuing"
                    " with test execution"
                )

            elif agent_failure_mode != FailureMode.NONE:
                results.failure_mode = agent_failure_mode

            if agent_result is not None:
                results.total_input_tokens = agent_result.total_input_tokens
                results.total_output_tokens = agent_result.total_output_tokens

            if not trial_handler.task.run_tests_in_same_shell:
                session = terminal.create_session(
                    "tests",
                    is_active_stream=self._livestream,
                    as_configured_user=False,
                )

            results.test_started_at = datetime.now(timezone.utc).isoformat()

            test_failure_mode = self._run_tests(
                terminal=terminal,
                session=session,
                trial_handler=trial_handler,
            )

            results.test_ended_at = datetime.now(timezone.utc).isoformat()

            post_test_pane = session.capture_pane(capture_entire=True)
            trial_handler.trial_paths.post_test_pane_path.write_text(
                post_test_pane
            )

            if not trial_handler.task.disable_asciinema:
                agent_recording_path = (
                    trial_handler.trial_paths.sessions_path / "agent.cast"
                )

                results.recording_path = str(
                    agent_recording_path.relative_to(self._output_path)
                )

                if agent_result is not None:
                    asciinema_handler = AsciinemaHandler(
                        markers=agent_result.timestamped_markers,
                        recording_path=agent_recording_path,
                    )
                    asciinema_handler.merge_markers()

            if (
                test_failure_mode != FailureMode.NONE
                and results.failure_mode == FailureMode.UNSET
            ):
                results.failure_mode = test_failure_mode
                results.trial_ended_at = datetime.now(timezone.utc).isoformat()
                return results

        parser_results, parse_failure_mode = self._parse_results(
            trial_handler=trial_handler,
            post_test_pane=post_test_pane,
        )

        if parse_failure_mode != FailureMode.NONE:
            results.failure_mode = parse_failure_mode
            results.trial_ended_at = datetime.now(timezone.utc).isoformat()
            return results

        results.parser_results = parser_results
        results.is_resolved = self._is_resolved(parser_results)

        if results.is_resolved:
            self._logger.debug(f"Resolved task {trial_handler.task_id}")
        else:
            self._logger.debug(f"Unresolved task {trial_handler.task_id}")

        results.trial_ended_at = datetime.now(timezone.utc).isoformat()

        return results

    def _execute_tasks(self, BaseAgent: BaseAgent):
        results = BenchmarkResults()

        # Load previous results if resuming from a run
        if self._is_resuming:
            previous_results = self._load_previous_results()
            if previous_results:
                results.results = previous_results.results
                self._logger.info(
                    f"Loaded {len(previous_results.results)} results from previous run "
                    f"{self._run_id}"
                )

        # Check if there are any tasks to run
        if len(self._dataset) == 0:
            self._logger.info(
                "No tasks remaining to run. All tasks completed in previous run."
            )
            # Write the loaded results to the file since no new tasks will trigger
            # writes
            self._write_results(results)
            return results

        max_workers = min(len(self._dataset), self._n_concurrent_trials)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {}
            for task_path in self._dataset:
                for attempt in range(1, self._n_attempts + 1):
                    trial_name = self._get_trial_name(task_path, attempt)
                    future = executor.submit(
                        self._execute_single_trial,
                        trial_name=trial_name,
                        task_path=task_path,
                        BaseAgent=BaseAgent,
                    )
                    future_to_task[future] = (trial_name, attempt)

            total_tasks = len(self._dataset) * self._n_attempts

            if self._livestream:
                for future in as_completed(future_to_task):
                    trial_results = future.result()
                    results.results.append(trial_results)

                    self._write_results(results)
            else:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    TimeElapsedColumn(),
                ) as progress:
                    task = progress.add_task(
                        f"Running tasks (0/{total_tasks}, "
                        f"Accuracy: {results.accuracy:.2%})",
                        total=total_tasks,
                    )

                    for future in as_completed(future_to_task):
                        trial_results = future.result()

                        # Check for duplicates before adding
                        trial_key = (
                            trial_results.task_id,
                            trial_results.trial_name,
                        )
                        existing_trial_keys = {
                            (r.task_id, r.trial_name) for r in results.results
                        }

                        if trial_key not in existing_trial_keys:
                            results.results.append(trial_results)
                        else:
                            # Replace existing result with new one (in case of re-run)
                            for i, existing_result in enumerate(
                                results.results
                            ):
                                if (
                                    existing_result.task_id,
                                    existing_result.trial_name,
                                ) == trial_key:
                                    results.results[i] = trial_results
                                    break

                        self._write_results(results)

                        task_name = trial_results.task_id
                        status = "✓" if trial_results.is_resolved else "✗"

                        completed_tasks = len(results.results)

                        progress.update(
                            task,
                            advance=1,
                            description=(
                                f"Running tasks ({completed_tasks}/{total_tasks}, "
                                f"Accuracy: {results.accuracy:.2%}) - "
                                f"Last: {task_name} {status}"
                            ),
                        )

        return results

    def _write_run_metadata(self) -> None:
        resumed_at = (
            datetime.now(timezone.utc).isoformat()
            if self._is_resuming
            else None
        )

        metadata = RunMetadata(
            run_id=self._run_id,
            dataset_path=(
                str(self._dataset.config.path.absolute())
                if self._dataset.config.path
                else None
            ),
            dataset_name=self._dataset.config.name,
            dataset_version=self._dataset.config.version,
            output_path=str(self._output_path.absolute()),
            agent_name="TerminalBenchAgent",
            no_rebuild=self._no_rebuild,
            cleanup=self._cleanup,
            log_level=self._log_level,
            task_ids=self._dataset.task_ids,
            exclude_task_ids=self._exclude_task_ids,
            n_tasks=self._n_tasks,
            n_concurrent_trials=self._n_concurrent_trials,
            n_attempts=self._n_attempts,
            dataset_size=len(self._dataset),
            model_name=self._model_name,
            commit_hash=self._get_git_commit_hash(),
            username=self._get_user(),
            start_time=datetime.now(timezone.utc).isoformat(),
            s3_bucket=self._s3_bucket if self._s3_bucket else None,
            resumed_at=resumed_at,
        )
        self._run_uuid = metadata.uuid

        # Write metadata using simple JSON write
        self._run_metadata_output_path.write_text(
            metadata.model_dump_json(indent=4)
        )

    def run(self, BaseAgent: BaseAgent):
        """Run the harness.

        Returns:
            BenchmarkResults: The results of the harness run.
        """
        logger.info("Starting harness run")
        logger.info(f"Run ID: {self._run_id}")

        # Only write metadata and lock files if not resuming
        if not self._is_resuming:
            self._write_run_metadata()
            # self._create_run_lock()

        results = self._execute_tasks(BaseAgent)

        # Only update metadata on end if not resuming
        if not self._is_resuming:
            self._update_metadata_on_end(results=results)

        self._handle_results_upload(results)

        return results


from typing import List, Tuple

from camel.toolkits import TerminalToolkit


class CustomBaseAgent(BaseAgent):
    def __init__(self, ChatAgent: ChatAgent = None, *args, **kwargs):
        self.ChatAgent = ChatAgent
        self.logging_dir = os.getenv("CAMEL_LOG_DIR", None)

        super().__init__(*args, **kwargs)

    @staticmethod
    def name() -> str:
        return "CustomBaseAgent"

    def perform_task(
        self,
        instruction: str,
        session: TmuxSession,
        logging_dir: Path | None = None,
    ) -> AgentResult:
        container_name = session.container.name
        if not container_name:
            raise ValueError("Container name is required for DockerExecutor")

        run_id = 0
        while True:
            if os.path.exists(
                f"{self.logging_dir}/{container_name}_run{run_id:02d}"
            ):
                run_id += 1
            else:
                break
        session_logs_dir = (
            f"{self.logging_dir}/{container_name}_run{run_id}/session_logs/"
        )
        os.makedirs(session_logs_dir, exist_ok=True)
        working_dir = (
            f"{self.logging_dir}/{container_name}_run{run_id}/CAMEL_WORKDIR/"
        )
        os.makedirs(working_dir, exist_ok=True)

        if ChatAgent is None:
            raise ValueError("ChatAgent is required")

        self.ChatAgent.reset()
        terminal_toolkit_kwargs = {
            'timeout': 20.0,
            'working_directory': None,
            'use_docker_backend': True,
            'docker_container_name': container_name,
            'session_logs_dir': session_logs_dir,
            'safe_mode': False,
        }
        self.ChatAgent.add_tools(
            [*TerminalToolkit(**terminal_toolkit_kwargs).get_tools()]
        )

        usr_msg = f"{instruction}\n"

        # Get response information
        # Define a user message for creating logs directory
        usr_msg = f"Task instruction: {instruction}"
        print(f"User message: {usr_msg}")
        # Get response information
        response = self.ChatAgent.step(usr_msg)
        print(str(response.info['tool_calls'])[:1000])

        total_input_tokens = response.info['usage']['prompt_tokens']
        total_output_tokens = response.info['usage']['completion_tokens']

        memory_list = (
            self.ChatAgent._memory._chat_history_block.storage.memory_list
        )

        def create_timestamped_marker_from_memory(
            records: List[dict],
        ) -> Tuple[float, str]:
            """Create a timestamped marker from memory records."""
            results = []
            print(f"Total records: {len(records)}")
            for record in records:
                if 'func_name' in record['message'].keys():
                    timestamp = record['timestamp']
                    func_name = record['message']['func_name']
                    args = record['message'].get('args', {})
                    if args:
                        command = args.get('command', '')
                    else:
                        command = ''
                    results.append(
                        (
                            timestamp,
                            f"Called tool: {func_name} with args: {command}",
                        )
                    )
            return results

        timestamped_markers = create_timestamped_marker_from_memory(
            memory_list
        )

        print(f"Total input tokens: {total_input_tokens}")
        print(f"Total output tokens: {total_output_tokens}")
        print(f"Timestamped markers: {timestamped_markers}")

        del self.ChatAgent

        return AgentResult(
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            failure_mode=FailureMode.NONE,
            timestamped_markers=timestamped_markers,
        )


class TBench(BaseBenchmark):
    def __init__(
        self,
        name: str,
        data_dir: str,
        save_to: str,
        processes: int = 1,
        *args,
        **kwargs,
    ):
        super().__init__(name, data_dir, save_to, processes, *args, **kwargs)

        # os.makedirs(self.save_to, exist_ok=True)

        self.harness = TerminalBench(
            output_path=Path(self.save_to),
            run_id=datetime.now().strftime("%Y-%m-%d__%H-%M-%S"),
            dataset_name="terminal-bench-core".strip(),
            dataset_version="0.1.1",
            task_ids=["hello-world"],
        )

    def download(self) -> "BaseBenchmark":
        pass

    def load(self, force_download: bool = False):
        pass

    def run(self, agent: ChatAgent):
        BaseAgent = CustomBaseAgent(ChatAgent=agent)
        return self.harness.run(BaseAgent)
