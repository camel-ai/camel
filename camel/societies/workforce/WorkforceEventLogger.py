import time
import uuid
from typing import Dict, List, Optional

from camel.societies.workforce.WorkforceEventType import (
    TaskEventType,
)
from camel.tasks import Task


class WorkforceEventLogger:
    def __init__(self):
        self.events: List[Dict] = []

    def log_task_event(
        self,
        event_type: TaskEventType,
        task: Task,
        trace_id: str | None = None,
        workforce_id: Optional[str] = None,
        workforce_description: Optional[str] = None,
        details: Optional[Dict] = None,
    ):
        if trace_id is None:
            trace_id = str(uuid.uuid4())
        event = {
            "timestamp": time.time(),
            "event_type": event_type.value,
            "task_id": task.id,
            "trace_id": trace_id,
            "task_content": task.content,
            "task_state": task.state.name if task.state else None,
            "workforce_id": workforce_id,
            "workforce_description": workforce_description,
            "details": details or {}
        }
        self.events.append(event)
        print(f"[{event_type.value}] [Task: {task.id}] {event}")

    def get_events(self) -> List[Dict]:
        return self.events

    def clear_events(self):
        self.events.clear()

    def save_to_file(self, filepath: str):
        import json
        with open(filepath, 'w') as f:
            json.dump(self.events, f, indent=2)
