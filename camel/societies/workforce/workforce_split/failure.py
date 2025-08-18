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
# failure.py
# Encapsulates failure analysis and recovery strategy determination.

import logging
from typing import Any, Callable, Generator, List, Optional, Union

from camel.societies.workforce.prompts import (
    FAILURE_ANALYSIS_PROMPT,
    TASK_DECOMPOSE_PROMPT,
)
from camel.societies.workforce.utils import (
    FailureContext,
    RecoveryDecision,
    RecoveryStrategy,
)
from camel.tasks import Task

logger = logging.getLogger(__name__)


class FailureAnalyzer:
    r"""A class that encapsulates failure analysis and recovery strategy
    determination."""

    def __init__(
        self,
        task_agent: Optional[Any] = None,
        structured_handler: Optional[Any] = None,
        use_structured: bool = True,
    ):
        r"""Initialize the FailureAnalyzer.

        Args:
            task_agent (Any, optional): ChatAgent used to generate recovery
                decisions. (default: :obj:`None`)
            structured_handler (Any, optional): Optional handler for structured
                output parsing. (default: :obj:`None`)
            use_structured (bool, optional): Whether to use the structured
                handler vs native LLM output. (default: :obj:`True`)
        """
        self.task_agent = task_agent
        self.structured_handler = structured_handler
        self.use_structured = use_structured

    def _analyze_failure(
        self,
        task: Task,
        error_message: str,
    ) -> RecoveryDecision:
        r"""Analyze a task failure and decide on the best recovery strategy.

        Args:
            task (Task): The failed task.
            error_message (str): The error message from the failure.

        Returns:
            RecoveryDecision: The decided recovery strategy with reasoning.
        """
        # First, do a quick smart analysis based on error patterns
        error_msg_lower = error_message.lower()
        if any(
            keyword in error_msg_lower
            for keyword in [
                'connection',
                'network',
                'server disconnected',
                'timeout',
                'apiconnectionerror',
            ]
        ):
            return RecoveryDecision(
                strategy=RecoveryStrategy.RETRY,
                reasoning="Network/connection error detected, retrying task",
                modified_task_content=None,
            )

        # Create failure context
        failure_context = FailureContext(
            task_id=task.id,
            task_content=task.content,
            failure_count=task.failure_count,
            error_message=error_message,
            worker_id=task.assigned_worker_id,
            task_depth=task.get_depth(),
            additional_info=str(task.additional_info)
            if task.additional_info
            else None,
        )

        # Format the analysis prompt
        analysis_prompt = FAILURE_ANALYSIS_PROMPT.format(
            task_id=failure_context.task_id,
            task_content=failure_context.task_content,
            failure_count=failure_context.failure_count,
            error_message=failure_context.error_message,
            worker_id=failure_context.worker_id or "unknown",
            task_depth=failure_context.task_depth,
            additional_info=failure_context.additional_info or "None",
        )

        try:
            # Check if we should use structured handler
            if self.use_structured and self.structured_handler:
                # Use structured handler
                enhanced_prompt = (
                    self.structured_handler.generate_structured_prompt(
                        base_prompt=analysis_prompt,
                        schema=RecoveryDecision,
                        examples=[
                            {
                                "strategy": "RETRY",
                                "reasoning": "Temporary network error, "
                                "worth retrying",
                                "modified_task_content": None,
                            }
                        ],
                    )
                )

                if self.task_agent is not None:
                    self.task_agent.reset()
                    response = self.task_agent.step(enhanced_prompt)

                    if self.structured_handler is not None:
                        result = (
                            self.structured_handler.parse_structured_response(
                                response.msg.content if response.msg else "",
                                schema=RecoveryDecision,
                                fallback_values={
                                    "strategy": RecoveryStrategy.RETRY,
                                    "reasoning": (
                                        "Defaulting to retry due to parsing "
                                        "issues"
                                    ),
                                    "modified_task_content": None,
                                },
                            )
                        )
                        # Ensure we return a RecoveryDecision instance
                        if isinstance(result, RecoveryDecision):
                            return result
                        elif isinstance(result, dict):
                            return RecoveryDecision(**result)
                        else:
                            return RecoveryDecision(
                                strategy=RecoveryStrategy.RETRY,
                                reasoning="Failed to parse recovery decision",
                                modified_task_content=None,
                            )
                    else:
                        return RecoveryDecision(
                            strategy=RecoveryStrategy.RETRY,
                            reasoning="Structured handler not available",
                            modified_task_content=None,
                        )
                else:
                    return RecoveryDecision(
                        strategy=RecoveryStrategy.RETRY,
                        reasoning=(
                            "Task agent not available, " "defaulting to retry"
                        ),
                        modified_task_content=None,
                    )
            else:
                # Use existing native structured output code
                if self.task_agent is not None:
                    self.task_agent.reset()
                    response = self.task_agent.step(
                        analysis_prompt, response_format=RecoveryDecision
                    )
                    return response.msg.parsed
                else:
                    return RecoveryDecision(
                        strategy=RecoveryStrategy.RETRY,
                        reasoning=(
                            "Task agent not available, " "defaulting to retry"
                        ),
                        modified_task_content=None,
                    )

        except Exception as e:
            logger.warning(
                f"Error during failure analysis: {e}, defaulting to RETRY"
            )
            return RecoveryDecision(
                strategy=RecoveryStrategy.RETRY,
                reasoning=f"Analysis failed due to error: {e!s}, "
                f"defaulting to retry",
                modified_task_content=None,
            )

    def _decompose_task(
        self,
        task: Task,
        child_nodes_info: str = "",
        update_dependencies_func: Optional[Callable] = None,
    ) -> Union[List[Task], Generator[List[Task], None, None]]:
        """
        Decompose the task into subtasks. This function will also set the
        relationship between the task and its subtasks.

        Args:
            task: The task to decompose
            child_nodes_info: Information about available worker nodes
            update_dependencies_func: Optional function to update dependencies

        Returns:
            Union[List[Task], Generator[List[Task], None, None]]:
            The subtasks or generator of subtasks.
        """
        decompose_prompt = TASK_DECOMPOSE_PROMPT.format(
            content=task.content,
            child_nodes_info=child_nodes_info,
            additional_info=task.additional_info,
        )
        if self.task_agent is not None:
            self.task_agent.reset()
            result = task.decompose(self.task_agent, decompose_prompt)
        else:
            logger.warning("Task agent not available for decomposition")
            return []

        # Handle both streaming and non-streaming results
        if isinstance(result, Generator):
            # This is a generator (streaming mode)
            def streaming_with_dependencies():
                all_subtasks = []
                for new_tasks in result:
                    all_subtasks.extend(new_tasks)
                    # Update dependency tracking for each batch of new tasks
                    if new_tasks and update_dependencies_func:
                        update_dependencies_func(task, all_subtasks)
                    yield new_tasks

            return streaming_with_dependencies()
        else:
            # This is a regular list (non-streaming mode)
            subtasks = result
            # Update dependency tracking for decomposed task
            if subtasks and update_dependencies_func:
                update_dependencies_func(task, subtasks)
            return subtasks
