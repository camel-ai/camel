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
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from camel.logger import get_logger
from camel.types.agents import ToolCallingRecord

logger = get_logger(__name__)


class WorkforceLogger:
    r"""Logs events and metrics for a Workforce instance."""

    def __init__(self, workforce_id: str):
        """Initializes the WorkforceLogger.

        Args:
            workforce_id (str): The unique identifier for the workforce.
        """
        self.workforce_id: str = workforce_id
        self.log_entries: List[Dict[str, Any]] = []
        self._task_hierarchy: Dict[str, Dict[str, Any]] = {}
        self._worker_information: Dict[str, Dict[str, Any]] = {}
        self._initial_worker_logs: List[Dict[str, Any]] = []

    def _log_event(self, event_type: str, **kwargs: Any) -> None:
        r"""Internal method to create and store a log entry.

        Args:
            event_type (str): The type of event being logged.
            **kwargs: Additional data associated with the event.
        """
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'workforce_id': self.workforce_id,
            'event_type': event_type,
            **kwargs,
        }
        self.log_entries.append(log_entry)
        if event_type == 'worker_created':
            self._initial_worker_logs.append(log_entry)

    def log_task_created(
        self,
        task_id: str,
        description: str,
        parent_task_id: Optional[str] = None,
        task_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        r"""Logs the creation of a new task."""
        self._log_event(
            'task_created',
            task_id=task_id,
            description=description,
            parent_task_id=parent_task_id,
            task_type=task_type,
            metadata=metadata or {},
        )
        self._task_hierarchy[task_id] = {
            'parent': parent_task_id,
            'children': [],
            'status': 'created',
            'description': description,
            'assigned_to': None,
            **(metadata or {}),
        }
        if parent_task_id and parent_task_id in self._task_hierarchy:
            self._task_hierarchy[parent_task_id]['children'].append(task_id)

    def log_task_decomposed(
        self,
        parent_task_id: str,
        subtask_ids: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        r"""Logs the decomposition of a task into subtasks."""
        self._log_event(
            'task_decomposed',
            parent_task_id=parent_task_id,
            subtask_ids=subtask_ids,
            metadata=metadata or {},
        )
        if parent_task_id in self._task_hierarchy:
            self._task_hierarchy[parent_task_id]['status'] = "decomposed"

    def log_task_assigned(
        self,
        task_id: str,
        worker_id: str,
        queue_time_seconds: Optional[float] = None,
        dependencies: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        r"""Logs the assignment of a task to a worker."""
        self._log_event(
            'task_assigned',
            task_id=task_id,
            worker_id=worker_id,
            queue_time_seconds=queue_time_seconds,
            dependencies=dependencies or [],
            metadata=metadata or {},
        )
        if task_id in self._task_hierarchy:
            self._task_hierarchy[task_id]['status'] = 'assigned'
            self._task_hierarchy[task_id]['assigned_to'] = worker_id
            self._task_hierarchy[task_id]['dependencies'] = dependencies or []
        if worker_id in self._worker_information:
            self._worker_information[worker_id]['current_task_id'] = task_id
            self._worker_information[worker_id]['status'] = 'busy'

    def log_task_started(
        self,
        task_id: str,
        worker_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        r"""Logs when a worker starts processing a task."""
        self._log_event(
            'task_started',
            task_id=task_id,
            worker_id=worker_id,
            metadata=metadata or {},
        )
        if task_id in self._task_hierarchy:
            self._task_hierarchy[task_id]['status'] = 'processing'

    def log_task_completed(
        self,
        task_id: str,
        worker_id: str,
        result_summary: Optional[str] = None,
        processing_time_seconds: Optional[float] = None,
        token_usage: Optional[Dict[str, int]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        r"""Logs the successful completion of a task."""
        self._log_event(
            'task_completed',
            task_id=task_id,
            worker_id=worker_id,
            result_summary=result_summary,
            processing_time_seconds=processing_time_seconds,
            token_usage=token_usage or {},
            metadata=metadata or {},
        )
        if task_id in self._task_hierarchy:
            self._task_hierarchy[task_id]['status'] = 'completed'
            self._task_hierarchy[task_id]['assigned_to'] = None
            # Store processing time in task hierarchy for display in tree
            if processing_time_seconds is not None:
                self._task_hierarchy[task_id]['completion_time_seconds'] = (
                    processing_time_seconds
                )
            # Store token usage in task hierarchy for display in tree
            if token_usage is not None:
                self._task_hierarchy[task_id]['token_usage'] = token_usage
        if worker_id in self._worker_information:
            self._worker_information[worker_id]['current_task_id'] = None
            self._worker_information[worker_id]['status'] = 'idle'
            self._worker_information[worker_id]['tasks_completed'] = (
                self._worker_information[worker_id].get('tasks_completed', 0)
                + 1
            )

    def log_task_failed(
        self,
        task_id: str,
        error_message: str,
        worker_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        r"""Logs the failure of a task."""
        self._log_event(
            'task_failed',
            task_id=task_id,
            worker_id=worker_id,
            error_message=error_message,
            metadata=metadata or {},
        )
        if task_id in self._task_hierarchy:
            self._task_hierarchy[task_id]['status'] = 'failed'
            self._task_hierarchy[task_id]['error'] = error_message
            self._task_hierarchy[task_id]['assigned_to'] = None
        if worker_id and worker_id in self._worker_information:
            self._worker_information[worker_id]['current_task_id'] = None
            self._worker_information[worker_id]['status'] = 'idle'
            self._worker_information[worker_id]['tasks_failed'] = (
                self._worker_information[worker_id].get('tasks_failed', 0) + 1
            )

    def log_worker_created(
        self,
        worker_id: str,
        worker_type: str,
        role: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        r"""Logs the creation of a new worker."""
        self._log_event(
            'worker_created',
            worker_id=worker_id,
            worker_type=worker_type,
            role=role,
            metadata=metadata or {},
        )
        self._worker_information[worker_id] = {
            'type': worker_type,
            'role': role,
            'status': 'idle',
            'current_task_id': None,
            'tasks_completed': 0,
            'tasks_failed': 0,
            **(metadata or {}),
        }

    def log_worker_deleted(
        self,
        worker_id: str,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        r"""Logs the deletion of a worker."""
        self._log_event(
            'worker_deleted',
            worker_id=worker_id,
            reason=reason,
            metadata=metadata or {},
        )
        if worker_id in self._worker_information:
            self._worker_information[worker_id]['status'] = 'deleted'
            # Or del self._worker_information[worker_id]

    def reset_task_data(self) -> None:
        r"""Resets logs and data related to tasks, preserving worker
        information.
        """
        # Restore log entries from the initial worker logs
        self.log_entries = list(self._initial_worker_logs)  # Make a copy

        self._task_hierarchy.clear()
        for worker_id in self._worker_information:
            if (
                self._worker_information[worker_id].get('status') != 'deleted'
            ):  # Don't revive deleted workers
                self._worker_information[worker_id]['current_task_id'] = None
                self._worker_information[worker_id]['status'] = 'idle'
        logger.info(
            f"WorkforceLogger: Task data reset for workforce "
            f"{self.workforce_id}"
        )

    def log_queue_status(
        self,
        queue_name: str,
        length: int,
        pending_task_ids: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        r"""Logs the status of a task queue."""
        self._log_event(
            'queue_status',
            queue_name=queue_name,
            length=length,
            pending_task_ids=pending_task_ids or [],
            metadata=metadata or {},
        )

    def dump_to_json(self, file_path: str) -> None:
        r"""Dumps all log entries to a JSON file.

        Args:
            file_path (str): The path to the JSON file.
        """

        def json_serializer_default(o: Any) -> Any:
            if isinstance(o, ToolCallingRecord):
                return o.as_dict()
            # Let the default encoder raise the TypeError for other types
            raise TypeError(
                f"Object of type {o.__class__.__name__} is not "
                f"JSON serializable"
            )

        try:
            with open(file_path, 'w') as f:
                json.dump(
                    self.log_entries,
                    f,
                    indent=4,
                    default=json_serializer_default,
                )
        except IOError as e:
            # Consider using camel.logger for this kind of internal error
            logger.error(f"Error dumping logs to JSON: {e}")

    def _get_all_tasks_in_hierarchy(
        self, task_id: str
    ) -> Dict[str, Dict[str, Any]]:
        r"""Recursively collect all tasks in the hierarchy starting from
        task_id.
        """
        result: Dict[str, Dict[str, Any]] = {}
        if task_id not in self._task_hierarchy:
            return result

        # Add the current task
        result[task_id] = self._task_hierarchy[task_id]

        # Add all children recursively
        children = self._task_hierarchy[task_id].get('children', [])
        for child_id in children:
            result.update(self._get_all_tasks_in_hierarchy(child_id))

        return result

    def _get_task_tree_string(
        self, task_id: str, prefix: str = "", is_last: bool = True
    ) -> str:
        r"""Generate a string representation of the task tree."""
        if task_id not in self._task_hierarchy:
            return ""

        task_info = self._task_hierarchy[task_id]
        description = task_info.get('description', '')
        status = task_info.get('status', 'unknown')
        assignee = task_info.get('assigned_to')
        assignee_str = f" [assigned to: {assignee}]" if assignee else ""
        dependencies = task_info.get('dependencies', [])
        dependencies_list = [
            dep for dep in dependencies if dep in self._task_hierarchy
        ]
        dependencies_str = (
            f" (dependencies: {', '.join(dependencies_list)})"
            if dependencies_list
            else ""
        )
        error_str = (
            f" [ERROR: {task_info.get('error', '')}]"
            if status == 'failed'
            else ""
        )

        # Add completion time and token usage for completed tasks
        completion_time_str = ""
        token_usage_str = ""

        if status == 'completed':
            # For the root task (typically task_id = '0'), calculate total
            # tokens and time
            if task_id == '0':
                # Calculate total tokens from all child tasks
                total_tokens = 0
                total_time = 0.0

                # Recursively get all tasks in the hierarchy
                all_tasks = self._get_all_tasks_in_hierarchy(task_id)

                # Sum up tokens and time from all tasks
                for child_id, child_info in all_tasks.items():
                    if (
                        child_id != task_id
                    ):  # Skip the root task itself to avoid double counting
                        # Add tokens
                        if (
                            'token_usage' in child_info
                            and child_info['token_usage'] is not None
                        ):
                            child_tokens = child_info['token_usage']
                            if (
                                isinstance(child_tokens, dict)
                                and 'total_tokens' in child_tokens
                            ):
                                total_tokens += child_tokens['total_tokens']
                            elif isinstance(child_tokens, int):
                                total_tokens += child_tokens

                        # Add completion time
                        if (
                            'completion_time_seconds' in child_info
                            and child_info['completion_time_seconds']
                            is not None
                        ):
                            total_time += child_info['completion_time_seconds']

                # Format the strings for the root task
                completion_time_str = (
                    f" (completed in {total_time:.2f} seconds total)"
                )
                token_usage_str = f" [total tokens: {total_tokens}]"
            else:
                # Regular task (not root) - show its own completion time and
                # tokens
                if (
                    'completion_time_seconds' in task_info
                    and task_info['completion_time_seconds'] is not None
                ):
                    completion_time = task_info['completion_time_seconds']
                    completion_time_str = (
                        f" (completed in {completion_time:.2f} seconds)"
                    )
                else:
                    # Add a default message when completion time is not
                    # available
                    completion_time_str = " (completed)"

                # Add token usage if available
                if (
                    'token_usage' in task_info
                    and task_info['token_usage'] is not None
                ):
                    token_usage = task_info['token_usage']
                    if (
                        isinstance(token_usage, dict)
                        and 'total_tokens' in token_usage
                    ):
                        token_usage_str = (
                            f" [tokens: {token_usage['total_tokens']}]"
                        )
                    elif isinstance(token_usage, int):
                        token_usage_str = f" [tokens: {token_usage}]"

        tree_str = f"{prefix}{'`-- ' if is_last else '|-- '}[{task_id}] {description} [{status}]{completion_time_str}{token_usage_str}{assignee_str}{dependencies_str}{error_str}\n"  # noqa: E501

        children = task_info.get('children', [])
        for i, child_id in enumerate(children):
            new_prefix = prefix + ("    " if is_last else "|   ")
            tree_str += self._get_task_tree_string(
                child_id, new_prefix, i == len(children) - 1
            )
        return tree_str

    def get_ascii_tree_representation(self) -> str:
        r"""Generates an ASCII tree representation of the current task
        hierarchy and worker status.
        """
        output_str = "=== Task Hierarchy ===\n"
        root_tasks = [
            task_id
            for task_id, info in self._task_hierarchy.items()
            if info.get('parent') is None
        ]
        if not root_tasks:
            output_str += "No tasks recorded.\n"
        else:
            for i, task_id in enumerate(root_tasks):
                output_str += self._get_task_tree_string(
                    task_id, "", i == len(root_tasks) - 1
                )

        output_str += "\n=== Worker Information ===\n"
        if not self._worker_information:
            output_str += "No workers recorded.\n"
        else:
            for worker_id, info in self._worker_information.items():
                role = info.get('role', 'N/A')
                completed = info.get('tasks_completed', 0)
                failed = info.get('tasks_failed', 0)
                output_str += (
                    f"- Worker ID: {worker_id} (Role: {role})\n"
                    f"    Tasks Completed: {completed}, Tasks "
                    f"Failed: {failed}\n"
                )
        return output_str

    def get_kpis(self) -> Dict[str, Any]:
        r"""Calculates and returns key performance indicators from the logs."""
        kpis: Dict[str, Any] = {
            'total_tasks_created': 0,
            'total_tasks_completed': 0,
            'total_tasks_failed': 0,
            'worker_utilization': {},
            'current_pending_tasks': 0,
            'total_workforce_running_time_seconds': 0.0,
        }

        task_start_times: Dict[str, float] = {}
        task_creation_timestamps: Dict[str, datetime] = {}
        task_assignment_timestamps: Dict[str, datetime] = {}
        first_timestamp: Optional[datetime] = None
        last_timestamp: Optional[datetime] = None

        tasks_handled_by_worker: Dict[str, int] = {}

        # Helper function to check if a task is the main task (has no parent)
        def is_main_task(task_id: str) -> bool:
            return (
                task_id in self._task_hierarchy
                and self._task_hierarchy[task_id].get('parent') is None
            )

        for entry in self.log_entries:
            event_type = entry['event_type']
            timestamp = datetime.fromisoformat(entry['timestamp'])
            task_id = entry.get('task_id', '')

            if first_timestamp is None or timestamp < first_timestamp:
                first_timestamp = timestamp
            if last_timestamp is None or timestamp > last_timestamp:
                last_timestamp = timestamp

            if event_type == 'task_created':
                # Exclude main task from total count
                if not is_main_task(task_id):
                    kpis['total_tasks_created'] += 1
                task_creation_timestamps[task_id] = timestamp
            elif event_type == 'task_assigned':
                task_assignment_timestamps[task_id] = timestamp
                # Queue time tracking has been removed

            elif event_type == 'task_started':
                # Store start time for processing time calculation
                task_start_times[task_id] = timestamp.timestamp()

            elif event_type == 'task_completed':
                # Exclude main task from total count
                if not is_main_task(task_id):
                    kpis['total_tasks_completed'] += 1
                    # Count tasks handled by worker (only for non-main tasks)
                    if 'worker_id' in entry and entry['worker_id'] is not None:
                        worker_id = entry['worker_id']
                        tasks_handled_by_worker[worker_id] = (
                            tasks_handled_by_worker.get(worker_id, 0) + 1
                        )

                if task_id in task_assignment_timestamps:
                    completion_time = (
                        timestamp - task_assignment_timestamps[task_id]
                    ).total_seconds()
                    # Store completion time in task hierarchy instead of KPIs
                    # array
                    if task_id in self._task_hierarchy:
                        self._task_hierarchy[task_id][
                            'completion_time_seconds'
                        ] = completion_time

            elif event_type == 'task_failed':
                # Exclude main task from total count
                if not is_main_task(task_id):
                    kpis['total_tasks_failed'] += 1
                    # Count tasks handled by worker (only for non-main tasks)
                    if 'worker_id' in entry and entry['worker_id'] is not None:
                        worker_id = entry['worker_id']
                        tasks_handled_by_worker[worker_id] = (
                            tasks_handled_by_worker.get(worker_id, 0) + 1
                        )
            elif event_type == 'queue_status':
                pass  # Placeholder for now

        # Calculate total workforce running time
        if first_timestamp and last_timestamp and self.log_entries:
            kpis['total_workforce_running_time_seconds'] = (
                last_timestamp - first_timestamp
            ).total_seconds()
        # Calculate worker utilization based on proportion of tasks handled
        total_tasks_processed_for_utilization = (
            kpis['total_tasks_completed'] + kpis['total_tasks_failed']
        )
        if total_tasks_processed_for_utilization > 0:
            for (
                worker_id_key,
                num_tasks_handled,
            ) in tasks_handled_by_worker.items():
                percentage = (
                    num_tasks_handled / total_tasks_processed_for_utilization
                ) * 100
                kpis['worker_utilization'][worker_id_key] = (
                    f"{percentage:.2f}%"
                )
        else:
            for worker_id_key in (
                tasks_handled_by_worker
            ):  # Ensure all workers who handled tasks are listed, even if 0%
                kpis['worker_utilization'][worker_id_key] = "0.00%"
            # If no tasks were processed, but workers exist (e.g. from
            # _initial_worker_logs), list them with 0%
            for worker_id_key in self._worker_information:
                if worker_id_key not in kpis['worker_utilization']:
                    kpis['worker_utilization'][worker_id_key] = "0.00%"

        # Task throughput (completed tasks per minute, for example)
        if self.log_entries:
            first_log_time = datetime.fromisoformat(
                self.log_entries[0]['timestamp']
            )
            last_log_time = datetime.fromisoformat(
                self.log_entries[-1]['timestamp']
            )
            duration_seconds = (last_log_time - first_log_time).total_seconds()
            if duration_seconds > 0:
                kpis['task_throughput_per_second'] = (
                    kpis['total_tasks_completed'] / duration_seconds
                )
                kpis['task_throughput_per_minute'] = (
                    kpis['task_throughput_per_second'] * 60
                )

        kpis['total_workers_created'] = len(self._worker_information)

        # Current pending tasks (simplified)
        kpis['current_pending_tasks'] = kpis['total_tasks_created'] - (
            kpis['total_tasks_completed'] + kpis['total_tasks_failed']
        )

        return kpis
