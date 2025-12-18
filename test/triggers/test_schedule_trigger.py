# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
from datetime import datetime

import pytest

from camel.triggers.base_trigger import TriggerState, TriggerType
from camel.triggers.schedule_trigger import (
    DayOfWeek,
    ScheduleConfig,
    ScheduleTrigger,
    ScheduleType,
)


def test_schedule_trigger_initialization_basic():
    """Test basic ScheduleTrigger initialization with valid cron expression"""
    trigger = ScheduleTrigger(
        trigger_id="test_schedule",
        name="Test Schedule",
        description="A test schedule trigger",
        cron_expression="0 9 * * 1-5",
        timezone="UTC",
    )

    assert trigger.trigger_id == "test_schedule"
    assert trigger.name == "Test Schedule"
    assert trigger.cron_expression == "0 9 * * 1-5"
    assert trigger.timezone == "UTC"
    assert trigger.state == TriggerState.INACTIVE
    assert trigger.next_run_at is None


def test_schedule_trigger_initialization_with_invalid_cron():
    """Test that invalid cron expression raises ValueError"""
    with pytest.raises(ValueError, match="Invalid cron expression"):
        ScheduleTrigger(
            trigger_id="test_schedule",
            name="Test Schedule",
            description="A test schedule trigger",
            cron_expression="invalid cron",
            timezone="UTC",
        )


def test_schedule_trigger_initialization_with_config():
    """Test initialization with ScheduleConfig"""
    config = ScheduleConfig(
        schedule_type=ScheduleType.DAILY,
        daily_hour=9,
        daily_minute=0,
    )

    trigger = ScheduleTrigger(
        trigger_id="test_schedule",
        name="Daily Schedule",
        description="Daily trigger at 9 AM",
        cron_expression="0 9 * * *",
        timezone="America/New_York",
        schedule_config=config,
    )

    assert trigger.timezone == "America/New_York"
    assert "schedule_config" in trigger.config
    assert trigger.get_schedule_config() is not None
    assert (
        trigger.get_schedule_config().schedule_type == ScheduleType.DAILY.value
    )


def test_validate_config_valid():
    """Test config validation with valid configuration"""
    trigger = ScheduleTrigger(
        trigger_id="test_schedule",
        name="Test Schedule",
        description="A test schedule trigger",
        cron_expression="*/5 * * * *",
        timezone="UTC",
    )

    config = {
        "cron_expression": "*/15 * * * *",
        "timezone": "UTC",
    }

    assert trigger.validate_config(config) is True


def test_validate_config_invalid_cron():
    """Test config validation with invalid cron expression"""
    trigger = ScheduleTrigger(
        trigger_id="test_schedule",
        name="Test Schedule",
        description="A test schedule trigger",
        cron_expression="*/5 * * * *",
        timezone="UTC",
    )

    config = {
        "cron_expression": "not a cron",
        "timezone": "UTC",
    }

    assert trigger.validate_config(config) is False


def test_validate_config_missing_cron():
    """Test config validation with missing cron expression"""
    trigger = ScheduleTrigger(
        trigger_id="test_schedule",
        name="Test Schedule",
        description="A test schedule trigger",
        cron_expression="*/5 * * * *",
        timezone="UTC",
    )

    config = {
        "timezone": "UTC",
    }

    assert trigger.validate_config(config) is False


@pytest.mark.asyncio
async def test_initialize_default():
    """Test trigger initialization without parameters"""
    trigger = ScheduleTrigger(
        trigger_id="test_schedule",
        name="Test Schedule",
        description="A test schedule trigger",
        cron_expression="*/5 * * * *",
        timezone="UTC",
    )

    result = await trigger.initialize()

    assert result is True
    assert trigger.next_run_at is not None
    assert trigger.updated_at is not None


@pytest.mark.asyncio
async def test_initialize_with_new_cron():
    """Test initialization with updated cron expression"""
    trigger = ScheduleTrigger(
        trigger_id="test_schedule",
        name="Test Schedule",
        description="A test schedule trigger",
        cron_expression="*/5 * * * *",
        timezone="UTC",
    )

    result = await trigger.initialize(cron_expression="*/10 * * * *")

    assert result is True
    assert trigger.cron_expression == "*/10 * * * *"


@pytest.mark.asyncio
async def test_initialize_with_invalid_cron():
    """Test initialization with invalid cron expression fails"""
    trigger = ScheduleTrigger(
        trigger_id="test_schedule",
        name="Test Schedule",
        description="A test schedule trigger",
        cron_expression="*/5 * * * *",
        timezone="UTC",
    )

    result = await trigger.initialize(cron_expression="invalid")

    assert result is False


@pytest.mark.asyncio
async def test_activate():
    """Test activating the schedule trigger"""
    trigger = ScheduleTrigger(
        trigger_id="test_schedule",
        name="Test Schedule",
        description="A test schedule trigger",
        cron_expression="*/5 * * * *",
        timezone="UTC",
    )

    result = await trigger.activate()

    assert result is True
    assert trigger.state == TriggerState.ACTIVE
    assert trigger._scheduler_thread is not None
    assert trigger._scheduler_thread.is_alive()

    # Cleanup
    await trigger.deactivate()


@pytest.mark.asyncio
async def test_activate_already_active():
    """Test that activating already active trigger returns False"""
    trigger = ScheduleTrigger(
        trigger_id="test_schedule",
        name="Test Schedule",
        description="A test schedule trigger",
        cron_expression="*/5 * * * *",
        timezone="UTC",
    )

    await trigger.activate()
    result = await trigger.activate()

    assert result is False

    # Cleanup
    await trigger.deactivate()


@pytest.mark.asyncio
async def test_deactivate():
    """Test deactivating the schedule trigger"""
    trigger = ScheduleTrigger(
        trigger_id="test_schedule",
        name="Test Schedule",
        description="A test schedule trigger",
        cron_expression="*/5 * * * *",
        timezone="UTC",
    )

    await trigger.activate()
    assert trigger.state == TriggerState.ACTIVE

    result = await trigger.deactivate()

    assert result is True
    assert trigger.state == TriggerState.INACTIVE
    assert trigger._stop_event.is_set()


@pytest.mark.asyncio
async def test_test_connection():
    """Test connection test validates cron expression"""
    trigger = ScheduleTrigger(
        trigger_id="test_schedule",
        name="Test Schedule",
        description="A test schedule trigger",
        cron_expression="*/5 * * * *",
        timezone="UTC",
    )

    result = await trigger.test_connection()

    assert result is True


def test_update_cron_expression_valid():
    """Test updating cron expression with valid value"""
    trigger = ScheduleTrigger(
        trigger_id="test_schedule",
        name="Test Schedule",
        description="A test schedule trigger",
        cron_expression="*/5 * * * *",
        timezone="UTC",
    )

    result = trigger.update_cron_expression("*/10 * * * *")

    assert result is True
    assert trigger.cron_expression == "*/10 * * * *"


def test_update_cron_expression_invalid():
    """Test updating cron expression with invalid value fails"""
    trigger = ScheduleTrigger(
        trigger_id="test_schedule",
        name="Test Schedule",
        description="A test schedule trigger",
        cron_expression="*/5 * * * *",
        timezone="UTC",
    )

    original_cron = trigger.cron_expression
    result = trigger.update_cron_expression("invalid cron")

    assert result is False
    assert trigger.cron_expression == original_cron


def test_create_interval_trigger():
    """Test creating interval-based trigger using factory method"""
    trigger = ScheduleTrigger.create_interval_trigger(
        trigger_id="interval_test",
        name="Interval Trigger",
        description="Runs every 15 minutes",
        minutes=15,
        timezone="UTC",
    )

    assert trigger.trigger_id == "interval_test"
    assert trigger.cron_expression == "*/15 * * * *"
    config = trigger.get_schedule_config()
    assert config is not None
    assert config.schedule_type == ScheduleType.INTERVAL.value
    assert config.interval_minutes == 15


def test_create_daily_trigger():
    """Test creating daily trigger using factory method"""
    trigger = ScheduleTrigger.create_daily_trigger(
        trigger_id="daily_test",
        name="Daily Trigger",
        description="Runs daily at 9:30 AM",
        hour=9,
        minute=30,
        timezone="America/New_York",
    )

    assert trigger.trigger_id == "daily_test"
    assert trigger.cron_expression == "30 9 * * *"
    assert trigger.timezone == "America/New_York"
    config = trigger.get_schedule_config()
    assert config is not None
    assert config.schedule_type == ScheduleType.DAILY.value
    assert config.daily_hour == 9
    assert config.daily_minute == 30


def test_create_weekly_trigger():
    """Test creating weekly trigger using factory method"""
    trigger = ScheduleTrigger.create_weekly_trigger(
        trigger_id="weekly_test",
        name="Weekly Trigger",
        description="Runs every Monday at 10 AM",
        day_of_week=DayOfWeek.MONDAY,
        hour=10,
        minute=0,
        timezone="UTC",
    )

    assert trigger.trigger_id == "weekly_test"
    assert trigger.cron_expression == "0 10 * * 1"
    config = trigger.get_schedule_config()
    assert config is not None
    assert config.schedule_type == ScheduleType.WEEKLY.value
    assert config.weekly_day == DayOfWeek.MONDAY.value
    assert config.weekly_hour == 10


@pytest.mark.asyncio
async def test_process_trigger_event():
    """Test processing trigger event creates proper TriggerEvent"""
    trigger = ScheduleTrigger(
        trigger_id="test_schedule",
        name="Test Schedule",
        description="A test schedule trigger",
        cron_expression="*/5 * * * *",
        timezone="UTC",
    )

    event_data = {
        "scheduled_time": datetime.now(),
        "cron_expression": "*/5 * * * *",
        "timezone": "UTC",
        "next_run_at": datetime.now(),
    }

    event = await trigger.process_trigger_event(event_data)

    assert event.trigger_id == "test_schedule"
    assert event.trigger_type == TriggerType.SCHEDULE
    assert event.payload == event_data
    assert "cron_expression" in event.metadata
    assert event.metadata["cron_expression"] == "*/5 * * * *"


def test_get_database_fields():
    """Test getting database fields for persistence"""
    trigger = ScheduleTrigger(
        trigger_id="test_schedule",
        name="Test Schedule",
        description="A test schedule trigger",
        cron_expression="*/5 * * * *",
        timezone="America/New_York",
    )

    fields = trigger.get_database_fields()

    assert "cron_expression" in fields
    assert "timezone" in fields
    assert "next_run_at" in fields
    assert "created_at" in fields
    assert "updated_at" in fields
    assert fields["cron_expression"] == "*/5 * * * *"
    assert fields["timezone"] == "America/New_York"


def test_get_database_fields_with_config():
    """Test database fields include schedule config when present"""
    config = ScheduleConfig(
        schedule_type=ScheduleType.INTERVAL,
        interval_minutes=30,
    )

    trigger = ScheduleTrigger(
        trigger_id="test_schedule",
        name="Test Schedule",
        description="A test schedule trigger",
        cron_expression="*/30 * * * *",
        timezone="UTC",
        schedule_config=config,
    )

    fields = trigger.get_database_fields()

    assert "schedule_config" in fields


@pytest.mark.asyncio
async def test_trigger_job_execution():
    """Test that trigger job creates and emits events"""
    trigger = ScheduleTrigger(
        trigger_id="test_schedule",
        name="Test Schedule",
        description="A test schedule trigger",
        cron_expression="*/5 * * * *",
        timezone="UTC",
    )

    # Track callback invocation
    callback_called = False
    received_event = None

    async def test_callback(event):
        nonlocal callback_called, received_event
        callback_called = True
        received_event = event

    trigger.add_callback(test_callback)

    # Manually trigger event processing
    import asyncio

    event_data = {
        "scheduled_time": datetime.now(),
        "cron_expression": "*/5 * * * *",
        "timezone": "UTC",
        "next_run_at": datetime.now(),
    }
    event = await trigger.process_trigger_event(event_data)

    # Emit the event to trigger callbacks
    await trigger._emit_trigger_event(event)

    # Give async operations time to complete
    await asyncio.sleep(0.1)

    assert callback_called is True
    assert received_event is not None
    assert received_event.trigger_id == "test_schedule"


def test_get_schedule_config_none():
    """Test getting schedule config when none is set"""
    trigger = ScheduleTrigger(
        trigger_id="test_schedule",
        name="Test Schedule",
        description="A test schedule trigger",
        cron_expression="*/5 * * * *",
        timezone="UTC",
    )

    config = trigger.get_schedule_config()

    assert config is None


def test_schedule_type_enum():
    """Test ScheduleType enum values"""
    assert ScheduleType.INTERVAL.value == "interval"
    assert ScheduleType.DAILY.value == "daily"
    assert ScheduleType.WEEKLY.value == "weekly"
    assert ScheduleType.MONTHLY.value == "monthly"
    assert ScheduleType.CUSTOM_CRON.value == "custom_cron"


def test_day_of_week_enum():
    """Test DayOfWeek enum values"""
    assert DayOfWeek.SUNDAY.value == 0
    assert DayOfWeek.MONDAY.value == 1
    assert DayOfWeek.TUESDAY.value == 2
    assert DayOfWeek.WEDNESDAY.value == 3
    assert DayOfWeek.THURSDAY.value == 4
    assert DayOfWeek.FRIDAY.value == 5
    assert DayOfWeek.SATURDAY.value == 6


@pytest.mark.asyncio
async def test_schedule_config_validation():
    """Test ScheduleConfig model validation"""
    config = ScheduleConfig(
        schedule_type=ScheduleType.INTERVAL,
        interval_minutes=60,
        custom_metadata={"key": "value"},
    )

    assert config.schedule_type == ScheduleType.INTERVAL.value
    assert config.interval_minutes == 60
    assert config.custom_metadata == {"key": "value"}
    assert config.daily_hour is None


@pytest.mark.asyncio
async def test_next_run_calculation():
    """Test that next_run_at is calculated after initialization"""
    trigger = ScheduleTrigger(
        trigger_id="test_schedule",
        name="Test Schedule",
        description="A test schedule trigger",
        cron_expression="*/5 * * * *",
        timezone="UTC",
    )

    await trigger.initialize()

    assert trigger.next_run_at is not None
    assert trigger.next_run_at > datetime.now()


@pytest.mark.asyncio
async def test_multiple_callbacks():
    """Test that multiple callbacks can be registered and invoked"""
    trigger = ScheduleTrigger(
        trigger_id="test_schedule",
        name="Test Schedule",
        description="A test schedule trigger",
        cron_expression="*/5 * * * *",
        timezone="UTC",
    )

    callback1_called = False
    callback2_called = False

    async def callback1(event):
        nonlocal callback1_called
        callback1_called = True

    async def callback2(event):
        nonlocal callback2_called
        callback2_called = True

    trigger.add_callback(callback1)
    trigger.add_callback(callback2)

    # Manually trigger event processing
    import asyncio

    event_data = {
        "scheduled_time": datetime.now(),
        "cron_expression": "*/5 * * * *",
        "timezone": "UTC",
        "next_run_at": datetime.now(),
    }
    event = await trigger.process_trigger_event(event_data)

    # Emit the event to trigger callbacks
    await trigger._emit_trigger_event(event)

    # Give async operations time to complete
    await asyncio.sleep(0.1)

    assert callback1_called is True
    assert callback2_called is True
