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
"""
Example demonstrating the new skip_gracefully functionality
in the Workforce class.

This example shows how to:
1. Set up a workforce with multiple tasks
2. Use the skip_gracefully function to empty pending tasks
3. Move to the next main task from the queue
4. Handle the case when no main tasks exist
"""

import asyncio

from camel.agents import ChatAgent
from camel.logger import get_logger
from camel.models import ModelFactory
from camel.societies.workforce.task_channel import TaskChannel
from camel.societies.workforce.workforce import Workforce
from camel.types import ModelPlatformType, ModelType

logger = get_logger(__name__)


def log_workforce_metrics(workforce, stage=""):
    r"""Helper function to log current workforce metrics including
    completed tasks"""
    pending_tasks = workforce.get_pending_tasks()
    main_tasks = workforce.get_main_task_queue()
    completed_tasks = workforce.get_completed_tasks()

    logger.info(f"\n--- Workforce Metrics {stage} ---")
    logger.info(f"  Pending: {len(pending_tasks)}")
    logger.info(f"  Main Task Queue: {len(main_tasks)}")
    logger.info(f"  Completed: {len(completed_tasks)}")
    logger.info(f"  Workforce state: {workforce._state.value}")

    # Log completed task details
    if completed_tasks:
        logger.info("  Completed task details:")
        for task in completed_tasks:
            logger.info(f"    - {task.content} (ID: {task.id})")
    else:
        logger.info("    No completed tasks yet")
    logger.info(f"--- End Metrics {stage} ---\n")


async def interactive_skip_demo():
    r"""Interactive demo showing real-time skip functionality"""
    TIME_AFTER_SKIP = 30  # Seconds to wait after skip to observe behavior
    LOOP_TIMEOUT = 60.0  # Overall timeout for the demo loop

    logger.info("\n=== Interactive Skip Demo ===")
    logger.info(
        "This demo shows how skip_gracefully works in"
        " real-time with user control\n"
    )

    # Create workforce with channel
    workforce = Workforce("Interactive Demo Workforce")
    channel = TaskChannel()
    workforce.set_channel(channel)

    # Add worker
    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )
    worker = ChatAgent(model=model)
    workforce.add_single_agent_worker("Interactive Worker", worker)

    # Add multiple tasks
    logger.info("Adding tasks...")
    workforce.add_main_task("Long running task 1", "long_1")
    workforce.add_main_task("Long running task 2", "long_2")
    workforce.add_main_task("Main backup task A", "backup_A")
    workforce.add_main_task("Main backup task B", "backup_B")

    log_workforce_metrics(workforce, "(Initial Setup)")

    # Start workforce
    logger.info("\nStarting workforce...")
    workforce_task = asyncio.create_task(workforce.start())
    await asyncio.sleep(0.5)

    logger.info("Workforce running! You can now interact with it.")
    logger.info(f"State: {workforce._state.value}")

    logger.info(
        "\nSimulating user calling skip_gracefully() after 15"
        " seconds of monitoring..."
    )
    await asyncio.sleep(15)
    log_workforce_metrics(workforce, "(Before Skip)")
    workforce.skip_gracefully()

    # Let the skip process
    await asyncio.sleep(TIME_AFTER_SKIP)

    log_workforce_metrics(workforce, "(After Skip)")

    # Let it run a bit more
    await asyncio.sleep(2.0)

    # Try another skip
    logger.info("\nTrying another skip...")
    workforce.skip_gracefully()
    await asyncio.sleep(TIME_AFTER_SKIP)

    log_workforce_metrics(workforce, "(Final State)")

    # Wait for workforce to complete or timeout
    try:
        await asyncio.wait_for(workforce_task, timeout=LOOP_TIMEOUT)
    except asyncio.TimeoutError:
        workforce.stop()

    logger.info("\n=== Interactive Demo Complete ===")


if __name__ == "__main__":

    async def main():
        # Run the interactive demo
        await interactive_skip_demo()

    # Run everything in an async event loop
    asyncio.run(main())
