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
import asyncio
import threading
import time
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel

# Optional croniter import for advanced cron parsing
try:
    from croniter import croniter

    HAS_CRONITER = True
except ImportError:
    HAS_CRONITER = False

from camel.triggers.base_trigger import (
    BaseTrigger,
    TriggerEvent,
    TriggerState,
    TriggerType,
)


class ScheduleType(Enum):
    """Enumeration of supported schedule types."""

    INTERVAL = "interval"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM_CRON = "custom_cron"


class DayOfWeek(Enum):
    """Enumeration of days of the week for weekly schedules."""

    SUNDAY = 0
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6


class ScheduleConfig(BaseModel):
    """Configuration for schedule-specific parameters."""

    schedule_type: ScheduleType
    interval_minutes: Optional[int] = None
    daily_hour: Optional[int] = None
    daily_minute: Optional[int] = None
    weekly_day: Optional[DayOfWeek] = None
    weekly_hour: Optional[int] = None
    weekly_minute: Optional[int] = None
    monthly_day: Optional[int] = None
    monthly_hour: Optional[int] = None
    monthly_minute: Optional[int] = None
    custom_metadata: Optional[Dict[str, Any]] = None

    class Config:
        use_enum_values = True


class ScheduleTrigger(BaseTrigger):
    """Cron expression-based trigger with database persistence.

    This trigger executes at scheduled intervals defined by cron expressions,
    supporting advanced scheduling patterns with timezone awareness and
    optional croniter library integration for enhanced cron parsing.
    """

    def __init__(
        self,
        trigger_id: str,
        name: str,
        description: str,
        cron_expression: str,
        timezone: str = "UTC",
        schedule_config: Optional[ScheduleConfig] = None,
    ) -> None:
        """
        Initialize ScheduleTrigger with cron expression.

        Args:
            trigger_id (str): Unique identifier for the trigger instance.
                Must be unique across all triggers in the system.
            name (str): Human-readable name for the trigger.
                Used for display and logging purposes.
            description (str): Detailed description of the trigger's purpose.
                Should explain what the trigger does and when it executes.
            cron_expression (str): Standard cron expression string
                defining the schedule.
                Format: "minute hour day_of_month month day_of_week"
                Examples:
                - "0 9 * * 1-5" (9 AM on weekdays)
                - "*/15 * * * *" (every 15 minutes)
                - "0 0 1 * *" (first day of each month at midnight)
            timezone (str, optional): Timezone identifier for schedule
                calculation.
                Supports standard timezone names like "UTC",
                "America/New_York", "Europe/London", etc. Defaults to "UTC".
            schedule_config (Optional[ScheduleConfig], optional): Additional
                configuration with structured metadata. Used by factory methods
                to store creation parameters. Defaults to None.

        Raises:
            ValueError: If the cron expression is invalid or malformed.

        Note:
            Requires croniter package for advanced cron parsing. Falls back to
            basic validation without croniter.
        """
        # Create config dictionary for base class
        config_dict = {
            "cron_expression": cron_expression,
            "timezone": timezone,
        }
        if schedule_config:
            config_dict["schedule_config"] = schedule_config.dict()

        super().__init__(
            trigger_id=trigger_id,
            name=name,
            description=description,
            config=config_dict,
        )
        self.cron_expression: str = cron_expression
        self.timezone: str = timezone
        self.next_run_at: Optional[datetime] = None
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()

        self._scheduler_thread: Optional[threading.Thread] = None
        self._stop_event: threading.Event = threading.Event()

        # Validate cron expression on initialization
        if not self._validate_cron_expression(cron_expression):
            raise ValueError(f"Invalid cron expression: {cron_expression}")

    def _validate_cron_expression(self, expression: str) -> bool:
        """Validate cron expression format and syntax.

        Args:
            expression (str): The cron expression to validate.

        Returns:
            bool: True if the expression is valid, False otherwise.

        Note:
            Uses croniter library if available for comprehensive validation,
            otherwise falls back to basic format checking (5 space-separated
                parts).
        """
        try:
            if HAS_CRONITER:
                # Check if croniter can parse the expression
                croniter(expression)
                return True
            else:
                # Fallback to basic format validation
                parts = expression.strip().split()
                return len(parts) == 5
        except Exception:
            # Fallback to basic format validation
            parts = expression.strip().split()
            return len(parts) == 5

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate that the configuration contains valid cron expression.

        Args:
            config (Dict[str, Any]): Configuration dictionary to validate.
                Expected to contain 'cron_expression' key with a valid
                cron string.

        Returns:
            bool: True if configuration is valid, False otherwise.
        """
        try:
            cron_expr = config.get('cron_expression')
            if not cron_expr:
                return False
            return self._validate_cron_expression(cron_expr)
        except Exception:
            return False

    async def initialize(
        self,
        cron_expression: Optional[str] = None,
        timezone: Optional[str] = None,
    ) -> bool:
        """
        Initialize the schedule trigger with cron expression.

        Args:
            cron_expression (Optional[str], optional): Cron expression to
                override the instance's current expression. Must be a valid
                5-part cron string.
                If None, uses the existing cron_expression. Defaults to None.
            timezone (Optional[str], optional): Timezone identifier to override
                the instance's current timezone. Must be a valid
                timezone string.
                If None, uses the existing timezone. Defaults to None.

        Returns:
            bool: True if initialization successful and next run time
                calculated, False if cron expression validation fails.

        Side Effects:
            - Updates self.cron_expression if provided
            - Updates self.timezone if provided
            - Calculates and sets self.next_run_at
            - Updates self.updated_at timestamp
        """
        if cron_expression:
            if not self._validate_cron_expression(cron_expression):
                return False
            self.cron_expression = cron_expression

        if timezone:
            self.timezone = timezone

        # Calculate next run time
        self._calculate_next_run()
        self.updated_at = datetime.now()

        return True

    def _calculate_next_run(self) -> None:
        """Calculate the next run time based on cron expression.

        Side Effects:
            Sets self.next_run_at to the next scheduled execution datetime.
            Uses croniter library if available, otherwise falls back to
            basic calculation for common patterns.

        Note:
            If cron parsing fails, defaults to next minute as fallback.
        """
        try:
            if HAS_CRONITER:
                cron = croniter(self.cron_expression, datetime.now())
                self.next_run_at = cron.get_next(datetime)
            else:
                # Basic fallback for common patterns
                self._calculate_next_run_basic()
        except Exception:
            # Fallback: calculate next run in 1 minute if cron parsing fails
            self.next_run_at = datetime.now().replace(second=0, microsecond=0)
            self.next_run_at = self.next_run_at.replace(
                minute=self.next_run_at.minute + 1
            )

    def _calculate_next_run_basic(self) -> None:
        """Basic cron calculation without croniter dependency.

        Handles simple cron patterns without external dependencies:
        - Interval patterns like "*/5 * * * *" (every 5 minutes)
        - Falls back to next minute for other patterns

        Raises:
            ValueError: If cron expression doesn't have exactly 5 parts.

        Side Effects:
            Sets self.next_run_at based on parsed cron expression.
        """
        # Simple pattern matching for common cron expressions
        parts = self.cron_expression.strip().split()
        if len(parts) != 5:
            raise ValueError("Invalid cron expression format")

        minute, hour, day, month, weekday = parts
        now = datetime.now()

        # Handle simple cases
        if minute.startswith("*/"):
            # Interval pattern like "*/5 * * * *"
            interval = int(minute[2:])
            next_minute = ((now.minute // interval) + 1) * interval
            if next_minute >= 60:
                self.next_run_at = now.replace(
                    hour=now.hour + 1,
                    minute=next_minute - 60,
                    second=0,
                    microsecond=0,
                )
            else:
                self.next_run_at = now.replace(
                    minute=next_minute, second=0, microsecond=0
                )
        else:
            # Default: next minute
            self.next_run_at = now.replace(second=0, microsecond=0)
            self.next_run_at = self.next_run_at.replace(
                minute=self.next_run_at.minute + 1
            )

    async def activate(self) -> bool:
        """Activate the schedule trigger and start the scheduler thread.

        Returns:
            bool: True if activation successful, False if scheduler is
                already running.

        Side Effects:
            - Calculates next run time
            - Starts background scheduler thread
            - Sets state to TriggerState.ACTIVE
            - Updates self.updated_at timestamp

        Note:
            The scheduler runs in a daemon thread that checks every second
            for trigger execution time.
        """
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            return False

        self._stop_event.clear()
        self._calculate_next_run()

        self._scheduler_thread = threading.Thread(target=self._run_scheduler)
        self._scheduler_thread.daemon = True
        self._scheduler_thread.start()

        self.state = TriggerState.ACTIVE
        self.updated_at = datetime.now()
        return True

    async def deactivate(self) -> bool:
        """Deactivate the schedule trigger and stop the scheduler thread.

        Returns:
            bool: True when deactivation is complete.

        Side Effects:
            - Signals scheduler thread to stop
            - Waits up to 5 seconds for thread to join
            - Sets state to TriggerState.INACTIVE
            - Updates self.updated_at timestamp

        Note:
            Uses threading.Event for graceful shutdown with timeout.
        """
        self._stop_event.set()
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)

        self.state = TriggerState.INACTIVE
        self.updated_at = datetime.now()
        return True

    async def test_connection(self) -> bool:
        """Test cron expression validity and trigger readiness.

        Returns:
            bool: True if the cron expression is valid and trigger is ready.

        Note:
            This method validates the cron expression format but doesn't
            test actual scheduling functionality.
        """
        return self._validate_cron_expression(self.cron_expression)

    def _run_scheduler(self) -> None:
        """Main scheduler loop that checks for trigger execution.

        Runs in a separate daemon thread, checking every second if it's time
        to execute the scheduled job. When execution time is reached:
        1. Triggers the job execution
        2. Calculates the next run time
        3. Updates the timestamp

        The loop continues until the stop event is set via deactivate().

        Side Effects:
            - Calls _trigger_job() when scheduled time arrives
            - Updates self.next_run_at after each execution
            - Updates self.updated_at timestamp
        """
        while not self._stop_event.is_set():
            current_time = datetime.now()

            # Check if it's time to run
            if self.next_run_at and current_time >= self.next_run_at:
                self._trigger_job()
                self._calculate_next_run()  # Calculate next execution time
                self.updated_at = datetime.now()

            time.sleep(1)  # Check every second

    def _trigger_job(self) -> None:
        """Execute trigger job and emit trigger event.

        Creates a comprehensive event with scheduling metadata and processes
        it through the trigger event pipeline. Handles async operations
        within the synchronous scheduler thread context.

        Side Effects:
            - Creates TriggerEvent with current execution data
            - Emits event to all registered callbacks
            - Manages event loop for async operations in sync context

        Note:
            Creates a new event loop to handle async operations since this
            runs in a synchronous thread context.
        """
        event_data = {
            "scheduled_time": datetime.now(),
            "cron_expression": self.cron_expression,
            "timezone": self.timezone,
            "next_run_at": self.next_run_at,
        }

        # Create event and emit (need to handle async in sync context)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            event = loop.run_until_complete(
                self.process_trigger_event(event_data)
            )
            loop.run_until_complete(self._emit_trigger_event(event))
        finally:
            loop.close()

    async def process_trigger_event(
        self, event_data: Dict[str, Any]
    ) -> TriggerEvent:
        """Process trigger event with cron configuration data.

        Args:
            event_data (Dict[str, Any]): Raw event data containing:
                - scheduled_time (datetime): When the trigger executed
                - cron_expression (str): The cron pattern used
                - timezone (str): Timezone for the schedule
                - next_run_at (Optional[datetime]): Next scheduled execution

        Returns:
            TriggerEvent: Standardized trigger event with comprehensive
                metadata.

        Note:
            Enriches the basic event data with scheduling-specific metadata
            including cron expression, timezone, and execution timestamps.
        """
        return TriggerEvent(
            trigger_id=self.trigger_id,
            trigger_type=TriggerType.SCHEDULE,
            timestamp=datetime.now(),
            payload=event_data,
            metadata={
                "cron_expression": self.cron_expression,
                "timezone": self.timezone,
                "next_run_at": self.next_run_at.isoformat()
                if self.next_run_at
                else None,
                "created_at": self.created_at.isoformat(),
                "updated_at": self.updated_at.isoformat(),
            },
        )

    @classmethod
    def create_interval_trigger(
        cls,
        trigger_id: str,
        name: str,
        description: str,
        minutes: int,
        timezone: str = "UTC",
    ) -> 'ScheduleTrigger':
        """Factory method to create an interval-based schedule trigger.

        Args:
            trigger_id (str): Unique identifier for the trigger instance.
            name (str): Human-readable name for the trigger.
            description (str): Detailed description of the trigger's purpose.
            minutes (int): Interval in minutes between trigger executions.
                Must be positive integer. Common values: 1, 5, 15, 30, 60.
            timezone (str, optional): Timezone for schedule calculation.
                Defaults to "UTC".

        Returns:
            ScheduleTrigger: Configured trigger instance ready for activation.

        Raises:
            ValueError: If minutes is not a positive integer.

        Example:
            >>> trigger = ScheduleTrigger.create_interval_trigger(
            ...     trigger_id="data-sync",
            ...     name="Data Synchronization",
            ...     description="Sync data every 15 minutes",
            ...     minutes=15
            ... )
        """
        if minutes <= 0:
            raise ValueError("Interval minutes must be positive")

        # Convert interval to cron expression (every N minutes)
        cron_expression = f"*/{minutes} * * * *"

        schedule_config = ScheduleConfig(
            schedule_type=ScheduleType.INTERVAL, interval_minutes=minutes
        )

        return cls(
            trigger_id=trigger_id,
            name=name,
            description=description,
            cron_expression=cron_expression,
            timezone=timezone,
            schedule_config=schedule_config,
        )

    @classmethod
    def create_daily_trigger(
        cls,
        trigger_id: str,
        name: str,
        description: str,
        hour: int,
        minute: int = 0,
        timezone: str = "UTC",
    ) -> 'ScheduleTrigger':
        """Factory method to create a daily schedule trigger.

        Args:
            trigger_id (str): Unique identifier for the trigger instance.
            name (str): Human-readable name for the trigger.
            description (str): Detailed description of the trigger's purpose.
            hour (int): Hour of day for execution (0-23, 24-hour format).
                Examples: 0 = midnight, 9 = 9 AM, 14 = 2 PM, 23 = 11 PM.
            minute (int, optional): Minute of the hour for execution (0-59).
                Defaults to 0 (top of the hour).
            timezone (str, optional): Timezone for schedule calculation.
                Defaults to "UTC".

        Returns:
            ScheduleTrigger: Configured trigger instance for daily execution.

        Raises:
            ValueError: If hour is not in range 0-23 or minute is not in
                range 0-59.

        Example:
            >>> trigger = ScheduleTrigger.create_daily_trigger(
            ...     trigger_id="daily-report",
            ...     name="Daily Report Generation",
            ...     description="Generate daily reports at 9:30 AM",
            ...     hour=9,
            ...     minute=30
            ... )
        """
        if not (0 <= hour <= 23):
            raise ValueError("Hour must be in range 0-23")
        if not (0 <= minute <= 59):
            raise ValueError("Minute must be in range 0-59")

        # Daily at specific time
        cron_expression = f"{minute} {hour} * * *"

        schedule_config = ScheduleConfig(
            schedule_type=ScheduleType.DAILY,
            daily_hour=hour,
            daily_minute=minute,
        )

        return cls(
            trigger_id=trigger_id,
            name=name,
            description=description,
            cron_expression=cron_expression,
            timezone=timezone,
            schedule_config=schedule_config,
        )

    @classmethod
    def create_weekly_trigger(
        cls,
        trigger_id: str,
        name: str,
        description: str,
        day_of_week: DayOfWeek,
        hour: int,
        minute: int = 0,
        timezone: str = "UTC",
    ) -> 'ScheduleTrigger':
        """Factory method to create a weekly schedule trigger.

        Args:
            trigger_id (str): Unique identifier for the trigger instance.
            name (str): Human-readable name for the trigger.
            description (str): Detailed description of the trigger's purpose.
            day_of_week (DayOfWeek): Day of the week for execution.
                Use DayOfWeek enum values (SUNDAY, MONDAY, TUESDAY, etc.).
            hour (int): Hour of day for execution (0-23, 24-hour format).
            minute (int, optional): Minute of the hour for execution (0-59).
                Defaults to 0.
            timezone (str, optional): Timezone for schedule calculation.
                Defaults to "UTC".

        Returns:
            ScheduleTrigger: Configured trigger instance for weekly execution.

        Raises:
            ValueError: If hour is not in range 0-23 or minute is not in
                range 0-59.

        Example:
            >>> trigger = ScheduleTrigger.create_weekly_trigger(
            ...     trigger_id="weekly-backup",
            ...     name="Weekly System Backup",
            ...     description="Run system backup every Sunday at 2 AM",
            ...     day_of_week=DayOfWeek.SUNDAY,
            ...     hour=2
            ... )
        """
        if not (0 <= hour <= 23):
            raise ValueError("Hour must be in range 0-23")
        if not (0 <= minute <= 59):
            raise ValueError("Minute must be in range 0-59")

        # Weekly on specific day and time
        cron_expression = f"{minute} {hour} * * {day_of_week.value}"

        schedule_config = ScheduleConfig(
            schedule_type=ScheduleType.WEEKLY,
            weekly_day=day_of_week,
            weekly_hour=hour,
            weekly_minute=minute,
        )

        return cls(
            trigger_id=trigger_id,
            name=name,
            description=description,
            cron_expression=cron_expression,
            timezone=timezone,
            schedule_config=schedule_config,
        )

    def update_cron_expression(self, new_cron_expression: str) -> bool:
        """Update the cron expression and recalculate next run time.

        Args:
            new_cron_expression (str): New cron expression to replace
                current one.
                Must be a valid 5-part cron expression format.

        Returns:
            bool: True if update successful, False if new expression is
                invalid.

        Side Effects:
            - Updates self.cron_expression if validation passes
            - Recalculates and updates self.next_run_at
            - Updates self.updated_at timestamp

        Note:
            If the trigger is currently active, the new schedule will take
            effect immediately for the next execution.
        """
        if not self._validate_cron_expression(new_cron_expression):
            return False

        self.cron_expression = new_cron_expression
        self._calculate_next_run()
        self.updated_at = datetime.now()
        return True

    def get_database_fields(self) -> Dict[str, Any]:
        """Get database fields for persistence and state management.

        Returns:
            Dict[str, Any]: Dictionary containing all persistent fields:
                - cron_expression (str): Current cron schedule pattern
                - timezone (str): Timezone identifier
                - next_run_at (Optional[datetime]): Next scheduled execution
                time
                - created_at (datetime): Trigger creation timestamp
                - updated_at (datetime): Last modification timestamp
                - schedule_config (Optional[dict]): Structured schedule
                configuration

        Note:
            Used for serializing trigger state to database or
                configuration files.
            All datetime objects should be handled appropriately by the
                persistence layer.
        """
        fields = {
            "cron_expression": self.cron_expression,
            "timezone": self.timezone,
            "next_run_at": self.next_run_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

        # Add schedule config if available
        schedule_config_dict = self.config.get("schedule_config")
        if schedule_config_dict:
            fields["schedule_config"] = schedule_config_dict

        return fields

    def get_schedule_config(self) -> Optional[ScheduleConfig]:
        """Get the structured schedule configuration if available.

        Returns:
            Optional[ScheduleConfig]: The schedule configuration object or
                None.
        """
        schedule_config_dict = self.config.get("schedule_config")
        if schedule_config_dict:
            return ScheduleConfig(**schedule_config_dict)
        return None
