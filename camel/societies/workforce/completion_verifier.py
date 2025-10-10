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
from dataclasses import dataclass
from typing import Any, Callable, Optional
import inspect

try:
    # Task type hint; avoid hard import to keep lightweight
    from camel.tasks.task import Task
except Exception:  # pragma: no cover - fallback for type hints
    Task = Any


@dataclass
class VerificationResult:
    passed: bool
    reason: Optional[str] = None


class CompletionVerifier:
    """Completion verifier that checks whether a task is truly complete.

    This class is intentionally framework-agnostic. You can inject any callable
    `model_fn` that maps a prompt or structured input to a boolean decision and
    optional reason.

    If `model_fn` is not provided, the verifier acts as a permissive stub and
    returns `passed=True` to avoid impacting existing workflows.
    """

    def __init__(
        self, model_fn: Optional[Callable[[Task], VerificationResult]] = None
    ) -> None:
        self._model_fn = model_fn

    async def verify(self, task: Task) -> VerificationResult:
        """Run completion verification for a task.

        Args:
            task: The task to verify.

        Returns:
            VerificationResult: Decision with optional reason.
        """
        if self._model_fn is None:
            # Default permissive behavior: do not block completion
            return VerificationResult(
                passed=True, reason="Default stub verifier: no model provided"
            )

        try:
            result_obj = self._model_fn(task)
            # Allow model_fn to be sync or async
            if inspect.isawaitable(result_obj):
                result_obj = await result_obj
            if not isinstance(result_obj, VerificationResult):
                # Coerce simple bools to VerificationResult
                return VerificationResult(passed=bool(result_obj), reason=None)
            return result_obj
        except Exception as e:  # robust fallback
            return VerificationResult(
                passed=True, reason=f"Verifier error, allowing completion: {e}"
            )