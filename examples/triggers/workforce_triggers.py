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
r"""Agentic triggers with a Workforce.

This example shows how to:

1. Enable triggers on a ``Workforce`` (turning it into a long-running,
   trigger-driven service that stays alive while triggers are registered).
2. Give an agent a ``TriggerToolkit`` so it can CRUD its own triggers.
3. Have a fired schedule inject a task back into the same workforce.

Install the extra first::

    pip install 'camel-ai[triggers]'

Run::

    python examples/triggers/workforce_triggers.py
"""

import asyncio

from camel.societies.workforce import Workforce
from camel.tasks import Task
from camel.toolkits import TriggerToolkit


async def main() -> None:
    # 1. Build a workforce and enable triggers on it.
    workforce = Workforce("Trigger-driven assistant")
    manager = workforce.enable_triggers()

    # 2. Expose trigger CRUD to an agent via the toolkit. The toolkit and the
    #    workforce share the same manager, so anything the agent schedules is
    #    injected back into this workforce when it fires.
    trigger_toolkit = TriggerToolkit(manager)
    # An agent given these tools could schedule work itself, e.g.:
    #   planner = ChatAgent("You manage automations...",
    #                       tools=trigger_toolkit.get_tools())
    #   planner.step("Every weekday at 9am, summarize my unread email.")

    # For a self-contained demo we call the create tool directly.
    result = trigger_toolkit.create_trigger(
        name="heartbeat",
        type="schedule",
        payload="Report the current system status.",
        config={"kind": "interval", "seconds": 10},
        max_runs=3,
    )
    print("Created trigger:", result)
    print("Active triggers:", trigger_toolkit.list_triggers())

    # 3. Kick off the workforce with an initial task. Because a trigger is
    #    registered, the workforce stays alive after the initial task is done,
    #    processing each fired heartbeat as a new task until the trigger is
    #    exhausted (max_runs=3).
    initial = Task(content="Introduce yourself.", id="seed")

    # Run the workforce; stop once the trigger is exhausted.
    async def stop_when_exhausted():
        while manager.has_active_triggers or workforce._pending_tasks:
            await asyncio.sleep(1)
        workforce.stop_gracefully()

    stopper = asyncio.ensure_future(stop_when_exhausted())
    await workforce.process_task_async(initial)
    await stopper

    # A webhook trigger example (not started here): the agent could also do
    #   trigger_toolkit.create_trigger(
    #       name="ci", type="webhook", payload="Handle the CI result.",
    #       config={"path": "/hooks/ci", "method": "POST"})
    # and POST to http://127.0.0.1:8080/hooks/ci would inject a task.
    print("Done. Remaining triggers:", trigger_toolkit.list_triggers())


if __name__ == "__main__":
    asyncio.run(main())
