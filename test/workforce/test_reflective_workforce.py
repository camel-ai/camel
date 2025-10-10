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
from unittest.mock import AsyncMock, MagicMock

import pytest

from camel.societies.workforce.completion_verifier import (
    CompletionVerifier,
    VerificationResult,
)
from camel.societies.workforce.reflective_workforce import (
    ReflectionStrategy,
    ReflectiveWorkforce,
)
from camel.societies.workforce.task_channel import TaskChannel


@pytest.mark.asyncio
async def test_reflective_workforce_verification_passes():
    # Verifier always passes
    verifier = CompletionVerifier(
        model_fn=lambda task: VerificationResult(passed=True)
    )
    wf = ReflectiveWorkforce(verifier=verifier)

    # Mock underlying channel and base handler
    wf._channel = AsyncMock(spec=TaskChannel)
    # Patch base handler to observe delegation
    wf_base_handle = AsyncMock()
    # Monkey-patch into instance
    wf.__class__.__mro__[1]._handle_completed_task = wf_base_handle

    mock_task = MagicMock()
    mock_task.id = "t1"

    await wf._handle_completed_task(mock_task)

    wf_base_handle.assert_awaited()
    wf._channel.return_task.assert_not_called()
    wf._channel.archive_task.assert_not_called()


@pytest.mark.asyncio
async def test_reflective_workforce_verification_fails_return():
    # Verifier fails
    verifier = CompletionVerifier(
        model_fn=lambda task: VerificationResult(
            passed=False, reason="not complete"
        )
    )
    wf = ReflectiveWorkforce(
        verifier=verifier,
        strategy=ReflectionStrategy.RETURN,
        max_verification_attempts=2,
    )

    wf._channel = AsyncMock(spec=TaskChannel)

    mock_task = MagicMock()
    mock_task.id = "t2"
    mock_task.additional_info = {}

    # First failure triggers return
    await wf._handle_completed_task(mock_task)
    wf._channel.return_task.assert_awaited_once_with("t2")
    wf._channel.archive_task.assert_not_called()

    # Second call should allow completion due to attempts limit
    # Make verifier still fail; attempts should be incremented
    await wf._handle_completed_task(mock_task)
    # Ensure base handler was eventually called (monkey-patch again)
    wf_base_handle = AsyncMock()
    wf.__class__.__mro__[1]._handle_completed_task = wf_base_handle
    await wf._handle_completed_task(mock_task)
    wf_base_handle.assert_awaited()