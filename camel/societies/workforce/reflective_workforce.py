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
import logging
from enum import Enum
from typing import Optional

from camel.societies.workforce.completion_verifier import (
    CompletionVerifier,
    VerificationResult,
)
from camel.societies.workforce.workforce import Workforce

try:
    from camel.tasks.task import Task
except Exception:  # pragma: no cover
    from typing import Any as Task  # fallback for type hints


logger = logging.getLogger(__name__)


class ReflectionStrategy(Enum):
    RETURN = "return"
    ARCHIVE = "archive"


class ReflectiveWorkforce(Workforce):
    """A Workforce subclass that performs LLM-based completion verification.

    This implementation is minimally invasive: it overrides the completed-task
    handling to optionally verify the task's result before marking it
    completed. On verification failure, it can return the task for further
    processing or archive it based on `strategy`.
    """

    def __init__(
        self,
        *args,
        verifier: Optional[CompletionVerifier] = None,
        strategy: ReflectionStrategy = ReflectionStrategy.RETURN,
        max_verification_attempts: int = 1,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._verifier = verifier or CompletionVerifier()
        self._reflection_strategy = strategy
        self._max_verification_attempts = max_verification_attempts

    async def _handle_completed_task(self, task: Task) -> None:  # type: ignore[override]
        """Verify completion before delegating to base handler.

        If verification fails and attempts remain, return or archive the task
        based on strategy and annotate metadata. Otherwise, fall back to the
        base completion handler.
        """
        # Normalize additional_info to a dict for safe updates
        info = getattr(task, "additional_info", None)
        if not isinstance(info, dict):
            try:
                info = {}
                setattr(task, "additional_info", info)
            except Exception:
                info = {}

        attempts = int(info.get("verification_attempts", 0))

        # Run verification
        result: VerificationResult = await self._verifier.verify(task)

        if result.passed or attempts >= self._max_verification_attempts:
            # Proceed with normal completion
            await super()._handle_completed_task(task)
            return

        # Verification failed and attempts remain
        info["verification_attempts"] = attempts + 1
        info["verification_reason"] = result.reason

        # Log queue status for observability
        try:
            self.metrics_logger.log_queue_status(
                queue_name="verification",
                length=len(self._pending_tasks),
                pending_task_ids=[t.id for t in self._pending_tasks],
                metadata={
                    "task_id": getattr(task, "id", None),
                    "strategy": self._reflection_strategy.value,
                    "reason": result.reason or "verification failed",
                    "attempts": attempts + 1,
                },
            )
        except Exception:
            logger.debug("Metrics logging unavailable during verification.")

        # Enact strategy
        if self._reflection_strategy == ReflectionStrategy.RETURN:
            # Return task back to publisher queue for re-processing
            try:
                await self._channel.return_task(task.id)
                logger.info(
                    "Task %s returned for further processing.",
                    getattr(task, "id", None),
                )
            except Exception as e:
                logger.warning(
                    "Failed to return task %s: %s",
                    getattr(task, "id", None),
                    e,
                )
        elif self._reflection_strategy == ReflectionStrategy.ARCHIVE:
            try:
                await self._channel.archive_task(task.id)
                logger.info(
                    "Task %s archived due to verification failure.",
                    getattr(task, "id", None),
                )
            except Exception as e:
                logger.warning(
                    "Failed to archive task %s: %s",
                    getattr(task, "id", None),
                    e,
                )
        else:
            # Fallback: do not block completion
            await super()._handle_completed_task(task)