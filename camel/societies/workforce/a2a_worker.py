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
from typing import TYPE_CHECKING, Any, List

if TYPE_CHECKING:
    from a2a.types import (
        InvalidAgentResponseError,
        SendMessageSuccessResponse,
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
        from a2a.client import A2ACardResolver, A2AClient

        self.base_url = base_url.rstrip("/")
        self.http_client = AsyncClient(**http_kwargs)
        self.resolver = A2ACardResolver(
            base_url=self.base_url, httpx_client=self.http_client
        )
        self.agent_card = agent_card
        description = self.agent_card.description
        node_id = getattr(agent_card, 'id', f"a2a_{uuid.uuid4().hex[:8]}")
        super().__init__(description, node_id=node_id)
        self.client = A2AClient(
            httpx_client=self.http_client, agent_card=agent_card
        )
        self.context_id: str | None = None
        self.use_structured_output_handler = False

    @classmethod
    async def create(
        cls, base_url: str, http_kwargs: dict | None = None
    ) -> "A2AAgent":
        r"""Creates a new instance of the A2AAgent by fetching the agent
        card from the remote service.
        """
        from a2a.client import A2ACardResolver

        http_kwargs = http_kwargs or {}
        http_client = AsyncClient(**http_kwargs)
        resolver = A2ACardResolver(base_url=base_url, httpx_client=http_client)
        agent_card = await resolver.get_agent_card()
        await http_client.aclose()
        return cls(base_url, http_kwargs, agent_card)

    def reset(self) -> Any:
        r"""Resets the worker to its initial state."""
        super().reset()
        self.context_id = None

    async def aclose(self):
        r"""Close the underlying HTTP client and cleanup resources."""
        await self.http_client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.aclose()

    async def cleanup(self):
        r"""Explicit cleanup method for better resource management."""
        try:
            if hasattr(self, 'http_client') and not self.http_client.is_closed:
                await self.http_client.aclose()
        except Exception as e:
            print(f"Error during A2A agent cleanup: {e}")

    def __del__(self):
        r"""Destructor to ensure cleanup on garbage collection."""
        try:
            if hasattr(self, 'http_client') and not self.http_client.is_closed:
                # Schedule cleanup if event loop is still running
                try:
                    loop = asyncio.get_event_loop()
                    if not loop.is_closed():
                        task = loop.create_task(self.http_client.aclose())
                        # Store reference to prevent RUF006 warning
                        _ = task
                except RuntimeError:
                    # Event loop is closed, skip cleanup
                    pass
        except Exception:
            # Ignore cleanup errors during destruction
            pass

    def _extract_text_from_parts(self, parts) -> str:
        r"""Extract text content from parts list."""
        from a2a.types import TextPart

        for part in parts:
            if hasattr(part, 'root') and isinstance(part.root, TextPart):
                return part.root.text
        return ""

    async def _send_a2a_message(
        self, message: str
    ) -> "SendMessageSuccessResponse | InvalidAgentResponseError":
        r"""Sends a message to the A2A agent and returns the structured
        response.
        """
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

        msg_obj = Message(
            role=Role.user,
            parts=[Part(root=TextPart(kind="text", text=message))],
            messageId=str(uuid.uuid4()),
            contextId=self.context_id,
        )
        params = MessageSendParams(message=msg_obj)
        request = SendMessageRequest(
            id=str(uuid.uuid4()),
            method="message/send",
            params=params,
        )
        response = await self.client.send_message(request)

        if isinstance(
            response.root,
            (SendMessageSuccessResponse, InvalidAgentResponseError),
        ):
            return response.root
        elif isinstance(response.root, JSONRPCErrorResponse):
            raise RuntimeError(f"A2A JSONRPCErrorResponse: {response.root}")
        else:
            raise TypeError(f"Unexpected response type: {type(response.root)}")

    async def _process_task(
        self, task: Task, dependencies: List[Task]
    ) -> TaskState:
        r"""Processes a task by sending it to the A2A agent and handling the
        structured response.

        Args:
            task (Task): The task to process.
            dependencies (List[Task]): A list of tasks that this task depends
                on.

        Returns:
            TaskState: The final state of the task after processing.
        """
        from a2a.types import (
            InvalidAgentResponseError,
            SendMessageSuccessResponse,
        )

        try:
            dependency_tasks_info = self._get_dep_tasks_info(dependencies)
            prompt = PROCESS_TASK_PROMPT.format(
                content=task.content,
                parent_task_content=task.parent.content if task.parent else "",
                dependency_tasks_info=dependency_tasks_info,
                additional_info=task.additional_info,
            )

            response = await self._send_a2a_message(prompt)

            # Update context ID if available
            if (
                self.context_id is None
                and hasattr(response, "result")
                and hasattr(response.result, "contextId")
            ):
                self.context_id = response.result.contextId

            if isinstance(response, SendMessageSuccessResponse):
                result_task = response.result
                task_result_content = ""

                # Try to extract text from status message
                if (
                    hasattr(result_task, "status")
                    and result_task.status
                    and hasattr(result_task.status, "message")
                    and result_task.status.message
                ):
                    task_result_content = self._extract_text_from_parts(
                        result_task.status.message.parts
                    )

                # Fallback to artifacts
                if (
                    not task_result_content
                    and hasattr(result_task, "artifacts")
                    and result_task.artifacts
                ):
                    task_result_content = self._extract_text_from_parts(
                        result_task.artifacts[0].parts
                    )

                # Fallback to parts
                if not task_result_content and hasattr(result_task, 'parts'):
                    task_result_content = self._extract_text_from_parts(
                        getattr(result_task, 'parts', [])
                    )

                if not task_result_content:
                    task_result_content = "Task completed, but no text content found in response"

                task.result = task_result_content
                print(f"======\n{Fore.GREEN}Response from {self}:{Fore.RESET}")
                print(
                    f"\n{Fore.GREEN}{task_result_content}{Fore.RESET}\n======"
                )

            elif isinstance(response, InvalidAgentResponseError):
                error_obj = getattr(response, "error", None)
                error_msg = (
                    f"Error from A2A Agent: {error_obj.message}"
                    if error_obj and hasattr(error_obj, "message")
                    else "Error from A2A Agent: Unknown error format."
                )
                task.result = error_msg
                print(f"======\n{Fore.RED}Error from {self}:{Fore.RESET}")
                print(f"\n{Fore.RED}{error_msg}{Fore.RESET}\n======")
                return TaskState.FAILED

        except Exception as e:
            error_msg = f"Exception during A2A call: {type(e).__name__}: {e!s}"
            print(
                f"{Fore.RED}Error processing task {task.id}: "
                f"{error_msg}{Fore.RESET}"
            )
            print(traceback.format_exc())
            task.result = error_msg
            return TaskState.FAILED
        finally:
            # Record worker attempt details
            if task.additional_info is None:
                task.additional_info = {}

            if "worker_attempts" not in task.additional_info:
                task.additional_info["worker_attempts"] = []

            task.additional_info["worker_attempts"].append(
                {
                    "agent_id": self.node_id,
                    "timestamp": str(datetime.datetime.now()),
                    "description": (
                        f"A2A worker {self.node_id} processed task: "
                        f"{task.content}"
                    ),
                    "response_content": str(response)
                    if 'response' in locals()
                    else "",
                    "tool_calls": None,
                    "total_tokens": 0,
                }
            )
            task.additional_info["token_usage"] = {"total_tokens": 0}

        if is_task_result_insufficient(task):
            print(
                f"{Fore.RED}Task {task.id}: Content validation failed"
                f"{Fore.RESET}"
            )
            return TaskState.FAILED

        return TaskState.DONE

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
