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
import pytest

from camel.toolkits import TriggerToolkit
from camel.triggers import TriggerManager

pytest.importorskip("croniter")


@pytest.fixture
def toolkit():
    return TriggerToolkit(TriggerManager())


def test_get_tools_names(toolkit):
    names = {t.get_function_name() for t in toolkit.get_tools()}
    assert names == {
        "create_trigger",
        "list_triggers",
        "get_trigger",
        "update_trigger",
        "pause_trigger",
        "resume_trigger",
        "cancel_trigger",
        "list_trigger_types",
    }


def test_list_trigger_types(toolkit):
    assert toolkit.list_trigger_types() == ["schedule", "webhook"]


def test_create_and_list(toolkit):
    res = toolkit.create_trigger(
        name="morning",
        type="schedule",
        payload="summarize email",
        config={"kind": "cron", "expr": "0 9 * * 1-5"},
    )
    assert res["created"] is True
    tid = res["id"]
    listed = toolkit.list_triggers()
    assert len(listed) == 1
    assert listed[0]["id"] == tid
    assert listed[0]["type"] == "schedule"


def test_create_invalid_returns_error_not_raise(toolkit):
    res = toolkit.create_trigger(
        name="bad",
        type="schedule",
        payload="x",
        config={"kind": "cron", "expr": "nonsense"},
    )
    assert "error" in res
    assert toolkit.list_triggers() == []


def test_create_unknown_type_returns_error(toolkit):
    res = toolkit.create_trigger(
        name="bad", type="carrier-pigeon", payload="x", config={}
    )
    assert "error" in res


def test_get_missing_returns_error(toolkit):
    assert "error" in toolkit.get_trigger("nope")


def test_update_pause_resume_cancel(toolkit):
    tid = toolkit.create_trigger(
        name="poll",
        type="schedule",
        payload="poll",
        config={"kind": "interval", "seconds": 60},
    )["id"]

    upd = toolkit.update_trigger(tid, payload="poll harder", max_runs=5)
    assert upd["updated"] is True

    full = toolkit.get_trigger(tid)
    assert full["payload"] == "poll harder"
    assert full["max_runs"] == 5

    assert toolkit.pause_trigger(tid)["state"] == "paused"
    assert toolkit.resume_trigger(tid)["state"] == "active"

    assert toolkit.cancel_trigger(tid)["deleted"] is True
    assert "error" in toolkit.cancel_trigger(tid)


def test_update_no_fields_returns_error(toolkit):
    tid = toolkit.create_trigger(
        name="x",
        type="schedule",
        payload="p",
        config={"kind": "interval", "seconds": 60},
    )["id"]
    assert "error" in toolkit.update_trigger(tid)


def test_update_bad_config_returns_error(toolkit):
    tid = toolkit.create_trigger(
        name="x",
        type="schedule",
        payload="p",
        config={"kind": "interval", "seconds": 60},
    )["id"]
    res = toolkit.update_trigger(
        tid, config={"kind": "interval", "seconds": -1}
    )
    assert "error" in res


def test_create_webhook(toolkit):
    res = toolkit.create_trigger(
        name="ci",
        type="webhook",
        payload="handle ci result",
        config={"path": "/hooks/ci", "method": "POST"},
    )
    assert res["created"] is True
    assert res["type"] == "webhook"
