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
from datetime import time as dt_time
from enum import Enum
from typing import Any, Dict, Optional

import schedule
from pydantic import BaseModel, Field, validator

from camel.triggers.base_trigger import (
    BaseTrigger,
    TriggerEvent,
    TriggerState,
    TriggerType,
)


class TimeUnit(str, Enum):
    """Supported time units for interval scheduling"""

    SECONDS = "seconds"
    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"
    WEEKS = "weeks"


class ScheduleType(str, Enum):
    """Types of schedule configurations"""

    CRON = "cron"
    INTERVAL = "interval"
    AT = "at"


class IntervalConfig(BaseModel):
    """Configuration for interval-based scheduling"""

    unit: TimeUnit = Field(description="Time unit for the interval")
    value: int = Field(gt=0, description="Interval value (must be positive)")

    @validator('value')
    def validate_positive_value(cls, v):
        if v <= 0:
            raise ValueError("Interval value must be positive")
        return v


class CronConfig(BaseModel):
    """Configuration for cron-based scheduling"""

    expression: str = Field(
        description="Cron expression (e.g., '0 9 * * 1-5')"
    )
    timezone: Optional[str] = Field(
        default=None, description="Timezone for cron execution"
    )

    @validator('expression')
    def validate_cron_expression(cls, v):
        # Basic validation for cron expression format
        parts = v.strip().split()
        if len(parts) != 5:
            raise ValueError(
                "Cron expression must have 5 parts: minute hour day month weekday"
            )
        return v


class AtConfig(BaseModel):
    """Configuration for daily scheduling at specific time"""

    time: str = Field(description="Time in HH:MM format (e.g., '09:30')")
    timezone: Optional[str] = Field(
        default=None, description="Timezone for execution"
    )

    @validator('time')
    def validate_time_format(cls, v):
        try:
            # Validate HH:MM format
            dt_time.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError("Time must be in HH:MM format (e.g., '09:30')")


class ScheduleConfig(BaseModel):
    """Unified schedule configuration supporting multiple types"""

    type: ScheduleType = Field(description="Type of schedule configuration")
    cron: Optional[CronConfig] = Field(
        default=None, description="Cron configuration"
    )
    interval: Optional[IntervalConfig] = Field(
        default=None, description="Interval configuration"
    )
    at: Optional[AtConfig] = Field(
        default=None, description="Daily time configuration"
    )

    @validator('cron')
    def validate_cron_when_type_is_cron(cls, v, values):
        if values.get('type') == ScheduleType.CRON and v is None:
            raise ValueError(
                "Cron configuration is required when type is 'cron'"
            )
        return v

    @validator('interval')
    def validate_interval_when_type_is_interval(cls, v, values):
        if values.get('type') == ScheduleType.INTERVAL and v is None:
            raise ValueError(
                "Interval configuration is required when type is 'interval'"
            )
        return v

    @validator('at')
    def validate_at_when_type_is_at(cls, v, values):
        if values.get('type') == ScheduleType.AT and v is None:
            raise ValueError("At configuration is required when type is 'at'")
        return v


class ScheduleTrigger(BaseTrigger):
    """Cron/Schedule-based trigger using Celery-like scheduling"""

    def __init__(self, schedule_config: ScheduleConfig, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.schedule_config = schedule_config
        self._scheduler_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate that the configuration contains valid schedule information"""
        try:
            # If config is passed as dict, try to parse it into ScheduleConfig
            if isinstance(config, dict):
                ScheduleConfig(**config)
            return True
        except Exception:
            return False

    async def initialize(
        self, schedule_config: Optional[ScheduleConfig] = None
    ) -> bool:
        """
        Initialize the schedule trigger with strongly typed configuration

        Args:
            schedule_config: Optional schedule configuration to override the instance config

        Returns:
            bool: True if initialization successful, False otherwise
        """
        if schedule_config:
            self.schedule_config = schedule_config

        # Validate the schedule configuration
        try:
            if not isinstance(self.schedule_config, ScheduleConfig):
                return False
            return True
        except Exception:
            return False

    async def activate(self) -> bool:
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            return False

        self._stop_event.clear()
        self._setup_schedule()

        self._scheduler_thread = threading.Thread(target=self._run_scheduler)
        self._scheduler_thread.daemon = True
        self._scheduler_thread.start()

        self.state = TriggerState.ACTIVE
        return True

    async def deactivate(self) -> bool:
        self._stop_event.set()
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
        schedule.clear()
        self.state = TriggerState.INACTIVE
        return True

    async def test_connection(self) -> bool:
        """Test schedule parsing and configuration validity"""
        try:
            self._setup_schedule()
            return True
        except Exception:
            return False

    def _setup_schedule(self):
        """Setup the schedule based on the typed configuration"""
        schedule.clear()

        if (
            self.schedule_config.type == ScheduleType.CRON
            and self.schedule_config.cron
        ):
            # TODO; Parse cron expression
            cron_expr = self.schedule_config.cron.expression

        elif (
            self.schedule_config.type == ScheduleType.INTERVAL
            and self.schedule_config.interval
        ):
            interval_config = self.schedule_config.interval
            unit = interval_config.unit
            value = interval_config.value

            if unit == TimeUnit.SECONDS:
                schedule.every(value).seconds.do(self._trigger_job)
            elif unit == TimeUnit.MINUTES:
                schedule.every(value).minutes.do(self._trigger_job)
            elif unit == TimeUnit.HOURS:
                schedule.every(value).hours.do(self._trigger_job)
            elif unit == TimeUnit.DAYS:
                schedule.every(value).days.do(self._trigger_job)
            elif unit == TimeUnit.WEEKS:
                schedule.every(value).weeks.do(self._trigger_job)

        elif (
            self.schedule_config.type == ScheduleType.AT
            and self.schedule_config.at
        ):
            time_str = self.schedule_config.at.time
            schedule.every().day.at(time_str).do(self._trigger_job)

    def _run_scheduler(self):
        while not self._stop_event.is_set():
            schedule.run_pending()
            time.sleep(1)

    def _trigger_job(self):
        """Execute trigger job with typed event data"""
        event_data = {
            "scheduled_time": datetime.now(),
            "trigger_config": self.schedule_config.dict(),
            "schedule_type": self.schedule_config.type.value,
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

    async def process_trigger_event(self, event_data: Any) -> TriggerEvent:
        """Process trigger event with typed configuration data"""
        return TriggerEvent(
            trigger_id=self.trigger_id,
            trigger_type=TriggerType.SCHEDULE,
            timestamp=datetime.now(),
            payload=event_data,
            metadata={
                "trigger_config": self.schedule_config.dict(),
                "schedule_type": self.schedule_config.type.value,
            },
        )

    @classmethod
    def create_interval_trigger(
        cls,
        trigger_id: str,
        name: str,
        description: str,
        unit: TimeUnit,
        value: int,
    ) -> 'ScheduleTrigger':
        """Factory method to create an interval-based schedule trigger"""
        schedule_config = ScheduleConfig(
            type=ScheduleType.INTERVAL,
            interval=IntervalConfig(unit=unit, value=value),
        )
        return cls(
            schedule_config=schedule_config,
            trigger_id=trigger_id,
            name=name,
            description=description,
            config={},
        )

    @classmethod
    def create_daily_trigger(
        cls,
        trigger_id: str,
        name: str,
        description: str,
        time: str,
        timezone: Optional[str] = None,
    ) -> 'ScheduleTrigger':
        """Factory method to create a daily schedule trigger"""
        schedule_config = ScheduleConfig(
            type=ScheduleType.AT, at=AtConfig(time=time, timezone=timezone)
        )
        return cls(
            schedule_config=schedule_config,
            trigger_id=trigger_id,
            name=name,
            description=description,
            config={},
        )

    @classmethod
    def create_cron_trigger(
        cls,
        trigger_id: str,
        name: str,
        description: str,
        cron_expression: str,
        timezone: Optional[str] = None,
    ) -> 'ScheduleTrigger':
        """Factory method to create a cron-based schedule trigger"""
        schedule_config = ScheduleConfig(
            type=ScheduleType.CRON,
            cron=CronConfig(expression=cron_expression, timezone=timezone),
        )
        return cls(
            schedule_config=schedule_config,
            trigger_id=trigger_id,
            name=name,
            description=description,
            config={},
        )
