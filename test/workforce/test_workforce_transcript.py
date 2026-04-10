# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
from pathlib import Path

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.societies.workforce.events import (
    TaskCompletedEvent,
    TaskCreatedEvent,
)
from camel.societies.workforce.transcript import (
    TranscriptEventType,
    TranscriptStore,
    WorkforceTranscriptCallback,
)
from camel.societies.workforce.workforce import Workforce
from camel.types import ModelPlatformType, ModelType


def _build_stub_agent() -> ChatAgent:
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.STUB,
    )
    return ChatAgent(model=model)


def test_transcript_callback_persists_jsonl_events(tmp_path: Path):
    store = TranscriptStore(tmp_path / "workforce.jsonl")
    callback = WorkforceTranscriptCallback("wf-1", store)

    callback.log_task_created(
        TaskCreatedEvent(task_id="task-1", description="Main task")
    )
    callback.log_task_completed(
        TaskCompletedEvent(
            task_id="task-1",
            worker_id="worker-1",
            result_summary="done",
        )
    )

    rows = store.read_all()

    assert [row["event_type"] for row in rows] == [
        TranscriptEventType.TASK_CREATED,
        TranscriptEventType.TASK_COMPLETED,
    ]
    assert rows[1]["payload"]["result_summary"] == "done"


def test_workforce_auto_registers_transcript_callback(tmp_path: Path):
    store = TranscriptStore(tmp_path / "auto.jsonl")
    workforce = Workforce(
        "Transcript Test",
        transcript_enabled=True,
        transcript_store=store,
    )

    assert any(
        isinstance(callback, WorkforceTranscriptCallback)
        for callback in workforce._callbacks
    )

    workforce.add_single_agent_worker("Worker", _build_stub_agent())
    rows = store.read_all()
    assert any(
        row["event_type"] == TranscriptEventType.WORKER_CREATED for row in rows
    )
