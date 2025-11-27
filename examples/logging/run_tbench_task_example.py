#!/usr/bin/env python3
r"""
Terminal Bench Task Runner with PromptLogger Integration (Example).

This script demonstrates how to integrate PromptLogger with CAMEL agents
in a real-world Terminal Bench evaluation scenario.

IMPORTANT: This is an example file showing how to use PromptLogger.
For actual Terminal Bench usage, adapt this pattern to your needs.

Key Integration Points:
1. Import PromptLogger (line 35-36)
2. Initialize logger before agent creation (line 105-107)
3. Monkey-patch ChatAgent to capture prompts (line 109-130)
4. Use agent normally - logging happens automatically (line 200+)
5. Convert to HTML after execution (mentioned in output, line 280+)

Usage:
    python run_tbench_task_example.py -t <task_name> -r <run_id>

After execution, convert the log to HTML:
    python llm_log_to_html.py <output_dir>/sessions/session_logs/llm_prompts.log
"""

from terminal_bench.handlers.trial_handler import TrialHandler
from terminal_bench.terminal.models import TerminalCommand
from terminal_bench.terminal.terminal import Terminal, spin_up_terminal
from terminal_bench.harness.models import FailureMode
from pathlib import Path
from strip_ansi import clean_text_file, clean_and_display_log
from camel.logger import get_logger
import sys
import json
import logging
import datetime

# ============================================================================
# INTEGRATION POINT 1: Import PromptLogger
# ============================================================================
from prompt_logger import PromptLogger

logger = get_logger(__name__)


class TeeLogger:
    r"""A context manager that captures stdout/stderr to both terminal and log.

    This class is useful for capturing all terminal output during task
    execution for later analysis.
    """

    class _TeeStream:
        r"""Internal class to handle the actual teeing of output."""

        def __init__(self, log_file, original_stream):
            self.log_file = log_file
            self.original_stream = original_stream

        def write(self, message):
            self.original_stream.write(message)
            self.original_stream.flush()
            self.log_file.write(message)
            self.log_file.flush()

        def flush(self):
            self.original_stream.flush()
            self.log_file.flush()

    def __init__(self, log_file_path):
        self.log_file_path = log_file_path
        self.log_file = None
        self.original_stdout = None
        self.original_stderr = None

    def __enter__(self):
        self.log_file = open(self.log_file_path, 'a', encoding='utf-8')
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        sys.stdout = self._TeeStream(self.log_file, self.original_stdout)
        sys.stderr = self._TeeStream(self.log_file, self.original_stderr)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print(
            f"\nAll terminal output has been logged to: "
            f"{self.log_file_path}"
        )
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        if self.log_file:
            self.log_file.close()
        return False


# ============================================================================
#               Set up the task
# ============================================================================
import argparse

parser = argparse.ArgumentParser(
    description="Run a TerminalBench task with PromptLogger integration."
)
parser.add_argument(
    "-t", "--task", default="play-zork", help="Task name from tbench-tasks"
)
parser.add_argument("-a", "--attempt", type=int, default=1,
                    help="Attempt number")
parser.add_argument(
    "-n", "--n_attempts", type=int, default=1, help="Total number of attempts"
)
parser.add_argument("-r", "--run_id", default="test_run",
                    help="Run identifier")
parser.add_argument(
    "-w",
    "--workforce",
    action="store_true",
    help="Use workforce agent (not used in this script)",
)
parser.add_argument(
    "--test_timeout",
    type=int,
    default=600,
    help="Test timeout in seconds (overrides default)",
)
args = parser.parse_args()

task_name = args.task
attempt = args.attempt
_n_attempts = args.n_attempts
_run_id = args.run_id

# Construct output paths
output_path = (
    Path(__file__).parent.resolve() / Path() / Path("output") / f"{_run_id}"
)
task_path = (
    Path(__file__).parent.parent.parent / "dataset" / "tbench-tasks" / task_name
)
trial_name = f"{task_path.name}.{attempt}-of-{_n_attempts}.{_run_id}"

print(f"Using task path: {task_path}")
# Check if the task path exists
if not task_path.exists():
    print(f"Task path {task_path} does not exist. Please check the path.")


trial_handler = TrialHandler(
    trial_name=trial_name,
    input_path=task_path,
    output_path=output_path,
)

# Set up session log directory and file path
session_log_dir = trial_handler.trial_paths.sessions_path / "session_logs"
session_log_dir.mkdir(parents=True, exist_ok=True)
session_log_path = session_log_dir / "terminal_output.log"

# ============================================================================
# INTEGRATION POINT 2: Initialize PromptLogger
# ============================================================================
prompt_log_path = session_log_dir / "llm_prompts.log"
prompt_logger = PromptLogger(str(prompt_log_path))
print(f"✅ LLM prompts will be logged to: {prompt_log_path}")
print(
    f"📝 After execution, convert to HTML with:\n"
    f"   python llm_log_to_html.py {prompt_log_path}"
)


# ============================================================================
# INTEGRATION POINT 3: Monkey-patch ChatAgent to capture all prompts
# ============================================================================
def patch_chat_agent_for_prompt_logging():
    r"""Patch ChatAgent's _get_model_response to log prompts.

    This function demonstrates how to intercept all LLM calls made by
    CAMEL ChatAgent and automatically log them using PromptLogger.

    The monkey-patching approach:
    1. Stores the original method
    2. Creates a wrapper that logs before calling the original
    3. Replaces the original method with the wrapper

    This pattern works for both sync and async methods.
    """
    from camel.agents.chat_agent import ChatAgent

    # Store original methods
    original_get_model_response = ChatAgent._get_model_response
    original_aget_model_response = ChatAgent._aget_model_response

    def logged_get_model_response(
        self,
        openai_messages,
        num_tokens,
        current_iteration=0,
        response_format=None,
        tool_schemas=None,
        prev_num_openai_messages=0,
    ):
        r"""Wrapper that logs prompts before calling original method."""
        if prompt_logger:
            model_info = f"{self.model_backend.model_type}"
            prompt_logger.log_prompt(
                openai_messages, model_info=model_info,
                iteration=current_iteration
            )
        return original_get_model_response(
            self,
            openai_messages,
            num_tokens,
            current_iteration,
            response_format,
            tool_schemas,
            prev_num_openai_messages,
        )

    async def logged_aget_model_response(
        self,
        openai_messages,
        num_tokens,
        current_iteration=0,
        response_format=None,
        tool_schemas=None,
        prev_num_openai_messages=0,
    ):
        r"""Async wrapper that logs prompts before calling original method."""
        if prompt_logger:
            model_info = f"{self.model_backend.model_type} (async)"
            prompt_logger.log_prompt(
                openai_messages, model_info=model_info,
                iteration=current_iteration
            )
        return await original_aget_model_response(
            self,
            openai_messages,
            num_tokens,
            current_iteration,
            response_format,
            tool_schemas,
            prev_num_openai_messages,
        )

    # Apply patches
    ChatAgent._get_model_response = logged_get_model_response
    ChatAgent._aget_model_response = logged_aget_model_response


# Apply the monkey patch
patch_chat_agent_for_prompt_logging()
print("✅ ChatAgent patched for automatic prompt logging")

# ============================================================================
# INTEGRATION POINT 4: Use agent normally - logging happens automatically
# ============================================================================
# Wrap the entire execution in TeeLogger to capture all terminal output
with TeeLogger(session_log_path):
    task_instruction = trial_handler.instruction
    print(f"Task instruction: {task_instruction}")
    working_dir = (
        trial_handler.trial_paths.sessions_path.parent / "CAMEL_WORKDIR"
    )
    import os

    os.environ["CAMEL_WORKDIR"] = str(working_dir)
    print(f"Set CAMEL_WORKDIR to: {os.environ['CAMEL_WORKDIR']}")

    # ========================================================================
    #               Create chat agent with terminal toolkit docker
    # ========================================================================
    from camel.agents import ChatAgent
    from camel.configs import ChatGPTConfig, LMStudioConfig
    from camel.models import ModelFactory
    from camel.toolkits import TerminalToolkit
    from camel.types import ModelPlatformType, ModelType

    with spin_up_terminal(
        client_container_name=trial_handler.client_container_name,
        client_image_name=trial_handler.client_image_name,
        docker_image_name_prefix=trial_handler.docker_image_name_prefix,
        docker_compose_path=trial_handler.task_paths.docker_compose_path,
        sessions_logs_path=trial_handler.trial_paths.sessions_path,
        agent_logs_path=trial_handler.trial_paths.agent_logging_dir,
        commands_path=trial_handler.trial_paths.commands_path,
        no_rebuild=True,
        cleanup=False,
        livestream=False,
        disable_recording=False,
    ) as terminal:
        # Create session
        session = terminal.create_session(
            "agent", is_active_stream=False, as_configured_user=True
        )

        # ====================================================================
        #               Create terminal toolkit instance
        # ====================================================================
        terminal_toolkit_kwargs = {
            'timeout': 20.0,
            'working_directory': None,
            'use_docker_backend': True,
            'docker_container_name': trial_handler.client_container_name,
            'session_logs_dir': (
                trial_handler.trial_paths.sessions_path / 'session_logs'
            ),
            'safe_mode': False,
        }

        # ====================================================================
        #               Run single chat agent
        # ====================================================================
        from eigent_simple import developer_agent_factory
        from eigent_simple import main as eigent_main

        if not args.workforce:  # Run single agent
            # Create model backend
            model_backend_reason = ModelFactory.create(
                model_platform=ModelPlatformType.LMSTUDIO,
                model_type="qwen3-8b",
                url="http://localhost:1234/v1",
                model_config_dict={
                    "stream": False,
                    "max_tokens": 8000,
                },
            )

            task_id = 'workforce_task'
            camel_agent = developer_agent_factory(
                model_backend_reason,
                task_id,
                terminal_toolkit_kwargs,
                system="Linux (in Docker)",
                machine="x86_64",
                is_workforce=False,
                working_directory=working_dir,
            )
            camel_agent.reset()

            # Send user message - prompts will be logged automatically
            usr_msg = f"Task instruction: {task_instruction}"
            print(f"User message: {usr_msg}")

            # Get response - logging happens automatically via monkey patch
            response = camel_agent.step(usr_msg)
            print(str(response.info['tool_calls'])[:1000])

            usage = response.info['usage']
            print(
                f"Prompt tokens: {usage['prompt_tokens']}, "
                f"completion tokens: {usage['completion_tokens']}"
            )

        else:  # Run workforce agent
            import asyncio

            asyncio.run(
                eigent_main(
                    task_instruction=task_instruction,
                    terminal_toolkit_kwargs=terminal_toolkit_kwargs,
                    logdir=f"{str(output_path)}/{trial_name}/",
                    system="Linux (in Docker)",
                    machine="x86_64",
                    working_directory=working_dir,
                )
            )

        # ====================================================================
        #               Test the results in the container
        # ====================================================================
        print("Run test script inside the container...")

        session = terminal.create_session(
            "tests", is_active_stream=False, as_configured_user=False
        )

        def _setup_test_env(
            terminal: Terminal, trial_handler: TrialHandler
        ) -> None:
            paths = [
                trial_handler.task_paths.run_tests_path,
            ]

            if trial_handler.task_paths.test_dir.exists():
                paths.append(trial_handler.task_paths.test_dir)

            terminal.copy_to_container(
                paths=paths,
                container_dir=str(
                    terminal._compose_manager.CONTAINER_TEST_DIR
                ),
            )

        def _run_tests(
            terminal: Terminal,
            session,
            trial_handler: TrialHandler,
        ) -> FailureMode:
            _setup_test_env(terminal, trial_handler)

            # Use command-line argument for test timeout if provided
            if args.test_timeout:
                test_timeout_sec = args.test_timeout
            elif trial_handler.task.max_test_timeout_sec:
                test_timeout_sec = (
                    trial_handler.task.max_test_timeout_sec * 1.0
                )
            else:
                test_timeout_sec = 600

            try:
                session.send_keys(
                    [
                        "bash ",
                        str(
                            terminal._compose_manager.CONTAINER_TEST_DIR
                            / trial_handler.task_paths.run_tests_path.name
                        ),
                        "Enter",
                    ],
                    block=True,
                    max_timeout_sec=test_timeout_sec,
                )
            except TimeoutError:
                print(
                    f"Test command timed out after {test_timeout_sec}s for "
                    f"task {trial_handler.task_id}."
                )
                return FailureMode.TEST_TIMEOUT

            return FailureMode.NONE

        test_failure_mode = _run_tests(
            terminal=terminal,
            session=session,
            trial_handler=trial_handler,
        )

        # ====================================================================
        #               Strip ansi from test log and display
        # ====================================================================
        testlog_path = (
            trial_handler.trial_paths.sessions_path / "tests.log"
        )
        testlog_strip_path = (
            trial_handler.trial_paths.sessions_path / "tests.log.strip"
        )
        clean_text_file(str(testlog_path), str(testlog_strip_path))
        print(f"Cleaned test log saved to: {testlog_strip_path}")
        clean_and_display_log(str(testlog_strip_path))

# ============================================================================
# INTEGRATION POINT 5: Show next steps
# ============================================================================
print("\n" + "=" * 70)
print("✅ Task execution completed!")
print("=" * 70)
print(f"\n📊 Logging Statistics:")
stats = prompt_logger.get_stats()
print(f"   Total prompts logged: {stats['total_prompts']}")
print(f"   Log file: {stats['log_file']}")
print(f"   File exists: {stats['file_exists']}")

print(f"\n🎨 Convert log to interactive HTML viewer:")
print(f"   python llm_log_to_html.py {prompt_log_path}")
print(f"\n   This will create: {prompt_log_path.parent / 'llm_prompts_viewer.html'}")
print("=" * 70 + "\n")
