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
import datetime
import traceback
import uuid
from typing import Any, List, Optional

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    InvalidAgentResponseError,
    JSONRPCErrorResponse,
    Message,
    MessageSendParams,
    Part,
    Role,
    SendMessageRequest,
    SendMessageSuccessResponse,
    TextPart,
)
from colorama import Fore
from httpx import AsyncClient

from camel.societies.workforce.prompts import PROCESS_TASK_PROMPT
from camel.societies.workforce.worker import Worker
from camel.tasks.task import Task, TaskState, is_task_result_insufficient


class A2AAgent(Worker):
    r"""A worker node that interfaces with an A2A (Agent-to-Agent) compliant
    agent.

    This worker acts as a client to an external agent service that follows
    the A2A specification. It sends tasks to the A2A agent and processes
    the structured responses.

    Args:
        base_url (str): The base URL of the A2A compliant agent service.
        http_kwargs (dict): A dictionary of keyword arguments to be passed to
            the underlying `httpx.AsyncClient`.
        agent_card (Any): The pre-fetched agent card of the A2A service.
        use_structured_output_handler (bool, optional): This parameter is
            included for API consistency with other workers but is not used,
            as the A2A protocol provides its own structured output mechanism.
            (default: :obj:`True`)
    """

    def __init__(
        self,
        base_url: str,
        http_kwargs: dict,
        agent_card: Any,
        use_structured_output_handler: bool = True,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.http_client = AsyncClient(**http_kwargs)
        self.resolver = A2ACardResolver(
            base_url=self.base_url, httpx_client=self.http_client
        )
        self.agent_card = agent_card
        description = self.agent_card.description
        # The agent_card id serves as the unique identifier for this worker
        node_id = getattr(agent_card, 'id', f"a2a_{uuid.uuid4().hex[:8]}")
        super().__init__(description, node_id=node_id)
        self.client = A2AClient(
            httpx_client=self.http_client, agent_card=agent_card
        )
        self.context_id: str | None = None
        # Note: A2A has its own structured output, so we disable the handler.
        self.use_structured_output_handler = False
        self._cleanup_task: Optional[asyncio.Task] = None

    @classmethod
    async def create(
        cls, base_url: str, http_kwargs: dict | None = None
    ) -> "A2AAgent":
        r"""Creates a new instance of the A2AAgent by fetching the agent
        card from the remote service.
        """
        http_kwargs = http_kwargs or {}
        http_client = AsyncClient(**http_kwargs)
        resolver = A2ACardResolver(base_url=base_url, httpx_client=http_client)
        agent_card = await resolver.get_agent_card()
        # The http_client is passed to the constructor, so we close the temp
        # one
        await http_client.aclose()
        return cls(base_url, http_kwargs, agent_card)

    def reset(self) -> Any:
        r"""Resets the worker to its initial state."""
        super().reset()
        # Reset context for A2A agent
        self.context_id = None

        # Stop cleanup task if running
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            self._cleanup_task = None

    async def aclose(self):
        """Close the underlying HTTP client and cleanup resources."""
        # Cancel cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()

        await self.http_client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.aclose()

    async def _send_a2a_message(
        self, message: str
    ) -> SendMessageSuccessResponse | InvalidAgentResponseError:
        """Sends a message to the A2A agent and returns the structured
        response.
        """
        # Construct a proper Message object for the message param
        msg_obj = Message(
            role=Role.user,
            parts=[
                Part(
                    root=TextPart(
                        kind="text",
                        text=message,
                    )
                )
            ],
            messageId=str(uuid.uuid4()),
            contextId=self.context_id,
        )
        params = MessageSendParams(
            message=msg_obj,
        )
        request = SendMessageRequest(
            id=str(uuid.uuid4()),
            method="message/send",
            params=params,
        )
        response = await self.client.send_message(request)
        # Only return allowed types
        if isinstance(response.root, SendMessageSuccessResponse):
            return response.root
        elif isinstance(response.root, InvalidAgentResponseError):
            return response.root
        elif isinstance(response.root, JSONRPCErrorResponse):
            # Log or raise for unexpected error response
            print(f"A2A JSONRPCErrorResponse: {response.root}")
            # Optionally, you could raise an exception here
            raise RuntimeError(f"A2A JSONRPCErrorResponse: {response.root}")
        else:
            raise TypeError(f"Unexpected response type: {type(response.root)}")

    async def _process_task(
        self, task: Task, dependencies: List[Task]
    ) -> TaskState:
        r"""Processes a task by sending it to the A2A agent and handling the
        structured response.

        This method formats a prompt with task and dependency information,
        sends it to the A2A agent, and records the results and metadata.

        Args:
            task (Task): The task to process.
            dependencies (List[Task]): A list of tasks that this task depends
                on.

        Returns:
            TaskState: The final state of the task after processing.
        """
        response = None
        response_content = ""
        task_result_content = ""

        try:
            dependency_tasks_info = self._get_dep_tasks_info(dependencies)
            prompt = PROCESS_TASK_PROMPT.format(
                content=task.content,
                parent_task_content=task.parent.content if task.parent else "",
                dependency_tasks_info=dependency_tasks_info,
                additional_info=task.additional_info,
            )

            response = await self._send_a2a_message(prompt)
            response_content = str(response)

            context_id_from_response = None
            # Try to extract contextId from different response types
            if hasattr(response, "result") and hasattr(
                response.result, "contextId"
            ):
                context_id_from_response = response.result.contextId
            elif hasattr(response, "contextId"):
                context_id_from_response = response.contextId
            if self.context_id is None and context_id_from_response:
                self.context_id = context_id_from_response
                print(f"A2A Context ID initialized: {self.context_id}")
            # --- END CONTEXT ID HANDLING ---

            if isinstance(response, SendMessageSuccessResponse):
                result_task = response.result
                # Use hasattr checks for status and artifacts
                if hasattr(result_task, "status") and hasattr(
                    result_task.status, "message"
                ):
                    if result_task.status and result_task.status.message:
                        for part in result_task.status.message.parts:
                            if hasattr(part, 'root') and isinstance(
                                part.root, TextPart
                            ):
                                task_result_content = part.root.text
                                break
                # Fallback to artifacts if no text found in status message
                if (
                    not task_result_content
                    and hasattr(result_task, "artifacts")
                    and result_task.artifacts
                ):
                    for part in result_task.artifacts[0].parts:
                        if hasattr(part, 'root') and isinstance(
                            part.root, TextPart
                        ):
                            task_result_content = part.root.text
                            break
                # Fallback to parts if present
                if not task_result_content and hasattr(result_task, 'parts'):
                    for part in getattr(result_task, 'parts', []):
                        if hasattr(part, 'root') and isinstance(
                            part.root, TextPart
                        ):
                            task_result_content = part.root.text
                            break
                if not task_result_content:
                    task_result_content = (
                        "Task completed, but no text content found in "
                        "response."
                    )
                task.result = task_result_content
                color = Fore.GREEN
                is_failed = False
            elif isinstance(response, InvalidAgentResponseError):
                error_obj = getattr(response, "error", None)
                if error_obj and hasattr(error_obj, "message"):
                    task_result_content = (
                        f"Error from A2A Agent: {error_obj.message}"
                    )
                else:
                    task_result_content = (
                        "Error from A2A Agent: Unknown error format."
                    )
                task.result = task_result_content
                color = Fore.RED
                is_failed = True
            else:
                task_result_content = "Unknown response type from A2A agent."
                task.result = task_result_content
                color = Fore.RED
                is_failed = True

        except Exception as e:
            print(
                f"{Fore.RED}Error processing task {task.id}: "
                f"{type(e).__name__}: {e}{Fore.RESET}"
            )
            print(traceback.format_exc())
            task.result = (
                f"Exception during A2A call: {type(e).__name__}: {e!s}"
            )
            return TaskState.FAILED
        finally:
            # Populate additional_info with worker attempt details
            if task.additional_info is None:
                task.additional_info = {}

            # Create worker attempt details with descriptive keys (similar to
            # SingleAgentWorker)
            worker_attempt_details = {
                "agent_id": self.node_id,
                "original_worker_id": self.node_id,
                "timestamp": str(datetime.datetime.now()),
                "description": f"Attempt by A2A worker {self.node_id} to "
                f"process task: {task.content}",
                "response_content": response_content,
                # A2A protocol does not provide token usage or tool calls
                "tool_calls": None,
                "total_tokens": 0,
            }

            # Store the worker attempt in additional_info
            if "worker_attempts" not in task.additional_info:
                task.additional_info["worker_attempts"] = []
            task.additional_info["worker_attempts"].append(
                worker_attempt_details
            )

            # Store the actual token usage for this specific task
            # (consistent with SingleAgentWorker)
            task.additional_info["token_usage"] = {"total_tokens": 0}

        print(f"======\n{Fore.GREEN}Response from {self}:{Fore.RESET}")
        print(f"\n{color}{task_result_content}{Fore.RESET}\n======")

        if is_failed:
            return TaskState.FAILED

        if is_task_result_insufficient(task):
            print(
                f"{Fore.RED}Task {task.id}: Content validation failed - "
                f"task marked as failed{Fore.RESET}"
            )
            return TaskState.FAILED

        return TaskState.DONE

    async def _listen_to_channel(self):
        r"""Override to start cleanup task when needed."""
        # Start cleanup task for periodic maintenance
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())

        # Call parent implementation
        await super()._listen_to_channel()

        # Stop cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()

    async def _periodic_cleanup(self):
        r"""Periodically perform cleanup tasks for A2A agent."""
        while True:
            try:
                await asyncio.sleep(300)  # Cleanup every 5 minutes
                # Perform any A2A-specific cleanup here
                # For example, checking connection health,
                # clearing old contexts, etc.
                await self._health_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in A2A cleanup: {e}")

    async def _health_check(self):
        r"""Perform a health check on the A2A connection."""
        try:
            # This could be expanded to include actual health check logic
            # For now, just ensure the client is still functional
            if self.http_client.is_closed:
                print(
                    f"{Fore.YELLOW}A2A HTTP client is closed, maybe due to a "
                    f"connection issue."
                )

        except Exception as e:
            print(f"A2A health check failed: {e}")

    def get_stats(self) -> dict:
        r"""Get A2A agent statistics."""
        return {
            "agent_id": self.node_id,
            "base_url": self.base_url,
            "context_id": self.context_id,
            "client_closed": self.http_client.is_closed,
            "agent_card_id": getattr(self.agent_card, 'id', 'unknown'),
            "agent_card_description": getattr(
                self.agent_card, 'description', 'unknown'
            ),
        }
