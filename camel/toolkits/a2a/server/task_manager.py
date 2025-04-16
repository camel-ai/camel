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
import logging
from abc import ABC, abstractmethod
from typing import AsyncIterable, List, Optional, Union

from camel.toolkits.a2a.server.utils import new_not_implemented_error
from camel.toolkits.a2a.types import (
    Artifact,
    CancelTaskRequest,
    CancelTaskResponse,
    GetTaskPushNotificationRequest,
    GetTaskPushNotificationResponse,
    GetTaskRequest,
    GetTaskResponse,
    InternalError,
    JSONRPCError,
    JSONRPCResponse,
    PushNotificationConfig,
    SendTaskRequest,
    SendTaskResponse,
    SendTaskStreamingRequest,
    SendTaskStreamingResponse,
    SetTaskPushNotificationRequest,
    SetTaskPushNotificationResponse,
    Task,
    TaskIdParams,
    TaskNotCancelableError,
    TaskNotFoundError,
    TaskPushNotificationConfig,
    TaskQueryParams,
    TaskResubscriptionRequest,
    TaskSendParams,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)

logger = logging.getLogger(__name__)


class TaskManager(ABC):
    @abstractmethod
    async def on_get_task(self, request: GetTaskRequest) -> GetTaskResponse:
        pass

    @abstractmethod
    async def on_cancel_task(
        self, request: CancelTaskRequest
    ) -> CancelTaskResponse:
        pass

    @abstractmethod
    async def on_send_task(self, request: SendTaskRequest) -> SendTaskResponse:
        pass

    @abstractmethod
    async def on_send_task_subscribe(
        self, request: SendTaskStreamingRequest
    ) -> Union[AsyncIterable[SendTaskStreamingResponse], JSONRPCResponse]:
        pass

    @abstractmethod
    async def on_set_task_push_notification(
        self, request: SetTaskPushNotificationRequest
    ) -> SetTaskPushNotificationResponse:
        pass

    @abstractmethod
    async def on_get_task_push_notification(
        self, request: GetTaskPushNotificationRequest
    ) -> GetTaskPushNotificationResponse:
        pass

    @abstractmethod
    async def on_resubscribe_to_task(
        self, request: TaskResubscriptionRequest
    ) -> Union[AsyncIterable[SendTaskStreamingResponse], JSONRPCResponse]:
        pass


class InMemoryTaskManager(TaskManager):
    def __init__(self) -> None:
        self.tasks: dict[str, Task] = {}
        self.push_notification_infos: dict[str, PushNotificationConfig] = {}
        self.lock = asyncio.Lock()
        self.task_sse_subscribers: dict[str, List[asyncio.Queue]] = {}
        self.subscriber_lock = asyncio.Lock()

    async def on_get_task(self, request: GetTaskRequest) -> GetTaskResponse:
        if not request.params:
            return GetTaskResponse(
                id=request.id,
                error=JSONRPCError(
                    code=-32602,
                    message="Invalid params",
                    data="Missing task ID",
                ),
            )

        task_query_params = TaskQueryParams(**request.params)

        async with self.lock:
            task = self.tasks.get(task_query_params.id)
            if task is None:
                return GetTaskResponse(
                    id=request.id, error=TaskNotFoundError()
                )

            task_result = self.append_task_history(
                task, task_query_params.historyLength
            )

        return GetTaskResponse(id=request.id, result=task_result)

    async def on_cancel_task(
        self, request: CancelTaskRequest
    ) -> CancelTaskResponse:
        if not request.params:
            return CancelTaskResponse(
                id=request.id,
                error=JSONRPCError(
                    code=-32602,
                    message="Invalid params",
                    data="Missing task ID",
                ),
            )

        task_id_params = TaskIdParams(**request.params)

        async with self.lock:
            task = self.tasks.get(task_id_params.id)
            if task is None:
                return CancelTaskResponse(
                    id=request.id, error=TaskNotFoundError()
                )

        return CancelTaskResponse(
            id=request.id, error=TaskNotCancelableError()
        )

    @abstractmethod
    async def on_send_task(self, request: SendTaskRequest) -> SendTaskResponse:
        pass

    @abstractmethod
    async def on_send_task_subscribe(
        self, request: SendTaskStreamingRequest
    ) -> Union[AsyncIterable[SendTaskStreamingResponse], JSONRPCResponse]:
        pass

    async def set_push_notification_info(
        self, task_id: str, notification_config: PushNotificationConfig
    ):
        async with self.lock:
            task = self.tasks.get(task_id)
            if task is None:
                raise ValueError(f"Task not found for {task_id}")

            self.push_notification_infos[task_id] = notification_config

        return

    async def get_push_notification_info(
        self, task_id: str
    ) -> PushNotificationConfig:
        async with self.lock:
            task = self.tasks.get(task_id)
            if task is None:
                raise ValueError(f"Task not found for {task_id}")

            return self.push_notification_infos[task_id]

        return

    async def has_push_notification_info(self, task_id: str) -> bool:
        async with self.lock:
            return task_id in self.push_notification_infos

    async def on_set_task_push_notification(
        self, request: SetTaskPushNotificationRequest
    ) -> SetTaskPushNotificationResponse:
        if not request.params:
            return SetTaskPushNotificationResponse(
                id=request.id,
                error=JSONRPCError(
                    code=-32602,
                    message="Invalid params",
                    data="Missing task notification parameters",
                ),
            )

        try:
            params = request.params
            task_notification_params = TaskPushNotificationConfig(**params)
            task_id = task_notification_params.id
            logger.info(f"Setting task push notification {task_id}")

            await self.set_push_notification_info(
                task_id,
                task_notification_params.pushNotificationConfig,
            )
        except Exception as e:
            logger.error(f"Error while setting push notification info: {e}")
            return SetTaskPushNotificationResponse(
                id=request.id,
                error=InternalError(
                    message="An error occurred while"
                    " setting push notification info"
                ),
            )

        return SetTaskPushNotificationResponse(
            id=request.id, result=task_notification_params
        )

    async def on_get_task_push_notification(
        self, request: GetTaskPushNotificationRequest
    ) -> GetTaskPushNotificationResponse:
        if not request.params:
            return GetTaskPushNotificationResponse(
                id=request.id,
                error=JSONRPCError(
                    code=-32602,
                    message="Invalid params",
                    data="Missing task ID",
                ),
            )
        task_params = TaskIdParams(**request.params)

        try:
            notification_info = await self.get_push_notification_info(
                task_params.id
            )
        except Exception as e:
            logger.error(f"Error while getting push notification info: {e}")
            return GetTaskPushNotificationResponse(
                id=request.id,
                error=InternalError(
                    message="An error occurred while"
                    " getting push notification info"
                ),
            )

        return GetTaskPushNotificationResponse(
            id=request.id,
            result=TaskPushNotificationConfig(
                id=task_params.id,
                pushNotificationConfig=notification_info,
            ),
        )

    async def upsert_task(self, task_send_params: TaskSendParams) -> Task:
        logger.info(f"Upserting task {task_send_params.id}")
        async with self.lock:
            task = self.tasks.get(task_send_params.id)
            if task is None:
                # Initialize with empty lists if needed
                history = [task_send_params.message]
                task = Task(
                    id=task_send_params.id,
                    sessionId=task_send_params.sessionId,
                    status=TaskStatus(state=TaskState.SUBMITTED),
                    history=history,
                )
                self.tasks[task_send_params.id] = task
            else:
                if task.history is None:
                    task.history = []
                task.history.append(task_send_params.message)

            return task

    async def on_resubscribe_to_task(
        self, request: TaskResubscriptionRequest
    ) -> Union[AsyncIterable[SendTaskStreamingResponse], JSONRPCResponse]:
        return new_not_implemented_error(request.id)

    async def update_store(
        self, task_id: str, status: TaskStatus, artifacts: list[Artifact]
    ) -> Task:
        async with self.lock:
            try:
                task = self.tasks[task_id]
            except KeyError:
                logger.error(f"Task {task_id} not found for updating the task")
                raise ValueError(f"Task {task_id} not found")

            task.status = status

            if status.message is not None:
                if task.history is None:
                    task.history = []
                task.history.append(status.message)

            if artifacts is not None:
                if task.artifacts is None:
                    task.artifacts = []
                task.artifacts.extend(artifacts)

            return task

    def append_task_history(
        self, task: Task, historyLength: Optional[int] = None
    ):
        new_task = task.model_copy()
        if (
            historyLength is not None
            and historyLength > 0
            and new_task.history is not None
        ):
            new_task.history = new_task.history[-historyLength:]
        else:
            new_task.history = []

        return new_task

    async def setup_sse_consumer(
        self, task_id: str, is_resubscribe: bool = False
    ) -> asyncio.Queue:
        async with self.subscriber_lock:
            if task_id not in self.task_sse_subscribers:
                if is_resubscribe:
                    raise ValueError("Task not found for resubscription")
                else:
                    self.task_sse_subscribers[task_id] = []

            sse_event_queue: asyncio.Queue = asyncio.Queue(
                maxsize=0
            )  # <=0 is unlimited
            self.task_sse_subscribers[task_id].append(sse_event_queue)
            return sse_event_queue

    async def enqueue_events_for_sse(
        self, task_id: str, task_update_event: TaskStatusUpdateEvent
    ):
        async with self.subscriber_lock:
            if task_id not in self.task_sse_subscribers:
                return

            current_subscribers = self.task_sse_subscribers[task_id]
            for subscriber in current_subscribers:
                await subscriber.put(task_update_event)

    async def dequeue_events_for_sse(
        self, request_id: str, task_id: str, sse_event_queue: asyncio.Queue
    ) -> AsyncIterable[SendTaskStreamingResponse]:
        try:
            while True:
                event = await sse_event_queue.get()
                if isinstance(event, JSONRPCError):
                    yield SendTaskStreamingResponse(id=request_id, error=event)
                    break

                yield SendTaskStreamingResponse(id=request_id, result=event)
                if isinstance(event, TaskStatusUpdateEvent) and event.final:
                    break
        finally:
            async with self.subscriber_lock:
                if task_id in self.task_sse_subscribers:
                    self.task_sse_subscribers[task_id].remove(sse_event_queue)
