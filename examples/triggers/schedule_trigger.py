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

"""
Simple Schedule Trigger Example

Demonstrates scheduled tasks that run automatically:
- Every 2 minutes (for quick testing)
- Daily backup at 2 AM
- Weekly report on Mondays at 9 AM
"""

import asyncio

from camel.logger import get_logger
from camel.societies.workforce.workforce import Workforce
from camel.triggers.base_trigger import TriggerEvent
from camel.triggers.handlers.workforce_handler import WorkforceHandler
from camel.triggers.schedule_trigger import DayOfWeek, ScheduleTrigger
from camel.triggers.trigger_manager import TriggerManager

logger = get_logger(__name__)


async def run_backup(event: TriggerEvent):
    """Simulate a backup task."""
    logger.info("Running daily backup...")
    # Simulate backup work
    await asyncio.sleep(1)
    logger.info("Backup completed")


async def generate_report(event: TriggerEvent):
    """Simulate generating a weekly report."""
    logger.info("Generating weekly report...")
    # Simulate report generation
    await asyncio.sleep(1)
    logger.info("Report generated and sent")


async def health_check(event: TriggerEvent):
    """Simulate a system health check."""
    logger.info("System health check - all systems operational")


async def main():
    """Run scheduled tasks."""
    # Setup
    workforce = Workforce("Scheduled Tasks")
    trigger_manager = TriggerManager(
        handler=WorkforceHandler(workforce=workforce)
    )

    # Health check every 2 minutes (for demo - normally would be longer)
    health_trigger = ScheduleTrigger.create_interval_trigger(
        trigger_id="health_check",
        name="Health Check",
        description="Check system health every 2 minutes",
        minutes=2,
    )

    # Daily backup at 2 AM
    backup_trigger = ScheduleTrigger.create_daily_trigger(
        trigger_id="daily_backup",
        name="Daily Backup",
        description="Run backup every day at 2 AM",
        hour=2,
        minute=0,
    )

    # Weekly report on Mondays at 9 AM
    report_trigger = ScheduleTrigger.create_weekly_trigger(
        trigger_id="weekly_report",
        name="Weekly Report",
        description="Generate report every Monday at 9 AM",
        day_of_week=DayOfWeek.MONDAY,
        hour=9,
        minute=0,
    )

    health_trigger.add_callback(health_check)
    backup_trigger.add_callback(run_backup)
    report_trigger.add_callback(generate_report)

    # Register all triggers
    await trigger_manager.register_trigger(health_trigger)
    await trigger_manager.register_trigger(backup_trigger)
    await trigger_manager.register_trigger(report_trigger)

    logger.info("Scheduled tasks started")
    try:
        while True:
            await asyncio.sleep(30)
    except KeyboardInterrupt:
        logger.info("Stopping scheduled tasks...")
        await trigger_manager.deactivate_all_triggers()
        logger.info("Done")


if __name__ == "__main__":
    asyncio.run(main())
