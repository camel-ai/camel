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
import datetime
import logging
import traceback
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from a2a.types import (
        AgentCard,
        InvalidAgentResponseError,
        SendMessageSuccessResponse,
    )
from colorama import Fore
from httpx import AsyncClient

from camel.societies.workforce.prompts import PROCESS_TASK_PROMPT
from camel.societies.workforce.worker import Worker
from camel.tasks.task import Task, TaskState, is_task_result_insufficient

logger = logging.getLogger(__name__)


class A2AAgentError(Exception):
    r"""Base exception for A2A Agent errors."""
    pass


class A2AMessageError(A2AAgentError):
    r"""Exception for A2A message sending errors."""
    pass


class A2AResponseError(A2AAgentError):
    r"""Exception for A2A response format errors."""
    pass


class A2AAgent(Worker):
    r"""A worker node that interfaces with an A2A (Agent-to-Agent) compliant
    agent.

    This worker acts as a client to an external agent service that follows
    the A2A specification. It sends tasks to the A2A agent and processes
    the structured responses.

    Args:
        base_url (str): The base URL of the A2A compliant agent service.
        agent_card (AgentCard): The pre-fetched agent card of the A2A service.
        http_kwargs (Optional[dict]): A dictionary of keyword arguments to be
            passed to the underlying `httpx.AsyncClient`. (default:
            :obj:`None`)
    """

    def __init__(
        self,
        base_url: str,
        agent_card: "AgentCard",
        http_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        from a2a.client import A2ACardResolver, A2AClient

        self.base_url = base_url.rstrip("/")
        http_kwargs = http_kwargs or {}
        self.http_client = AsyncClient(**http_kwargs)
        self.resolver = A2ACardResolver(
            base_url=self.base_url, httpx_client=self.http_client
        )
        self.agent_card = agent_card
        description = self.agent_card.description
        node_id = getattr(agent_card, 'id', f"a2a_{uuid.uuid4()}")
        super().__init__(description, node_id=node_id)
        self.client = A2AClient(
            httpx_client=self.http_client, agent_card=agent_card
        )
        self.context_id: Optional[str] = None

    @classmethod
    async def create(
        cls, base_url: str, http_kwargs: Optional[Dict[str, Any]] = None
    ) -> "A2AAgent":
        r"""Creates a new instance of the A2AAgent by fetching the agent
        card from the remote service.

        Args:
            base_url (str): The base URL of the A2A service.
            http_kwargs (Optional[dict]): Optional HTTP client configuration
                parameters to pass to the httpx AsyncClient. (default:
                :obj:`None`)

        Returns:
            A2AAgent: A new instance of the A2AAgent with the fetched agent
                card.

        Raises:
            A2AMessageError: If unable to reach the A2A service.
            A2AAgentError: For other unexpected errors during initialization.
        """
        from a2a.client import A2ACardResolver
        from a2a.client.errors import A2AClientHTTPError

        http_kwargs = http_kwargs or {}
        # Create a temporary client just for fetching the agent card
        temp_client = AsyncClient(**http_kwargs)
        try:
            resolver = A2ACardResolver(
                base_url=base_url, httpx_client=temp_client
            )
            logger.debug(f"Fetching agent card from {base_url}...")
            agent_card = await resolver.get_agent_card()
            logger.info(
                f"Successfully fetched A2A agent card. "
                f"Agent ID: {getattr(agent_card, 'id', 'unknown')}"
            )
        except A2AClientHTTPError as e:
            error_msg = (
                f"Failed to fetch A2A agent card from {base_url}. "
                f"Please ensure the A2A service is running and accessible at "
                f"this URL. HTTP Error: {str(e)}"
            )
            logger.error(error_msg)
            raise A2AMessageError(error_msg) from e
        except Exception as e:
            error_msg = (
                f"Unexpected error while fetching agent card from {base_url}: "
                f"{type(e).__name__}: {str(e)}"
            )
            logger.error(error_msg, exc_info=True)
            raise A2AAgentError(error_msg) from e
        finally:
            await temp_client.aclose()

        # Create the actual instance with its own HTTP client
        return cls(base_url, agent_card, http_kwargs)

    @classmethod
    async def check_connectivity(
        cls,
        base_url: str,
        http_kwargs: Optional[Dict[str, Any]] = None,
        timeout: float = 5.0,
    ) -> bool:
        r"""Check if the A2A service at the given base_url is reachable.

        Args:
            base_url (str): The base URL of the A2A service.
            http_kwargs (Optional[Dict[str, Any]]): HTTP client configuration.
                (default: :obj:`None`)
            timeout (float): Request timeout in seconds. (default: :obj:`5.0`)

        Returns:
            bool: True if the A2A service is reachable, False otherwise.
        """
        http_kwargs = http_kwargs or {}
        # Override timeout for connectivity check
        check_kwargs = {**http_kwargs, "timeout": timeout}
        temp_client = AsyncClient(**check_kwargs)
        try:
            agent_card_url = f"{base_url.rstrip('/')}/.well-known/agent-card.json"
            logger.debug(f"Checking connectivity to {agent_card_url}...")
            response = await temp_client.head(agent_card_url)
            is_reachable = response.status_code < 500
            logger.debug(
                f"A2A service connectivity check: "
                f"{'reachable' if is_reachable else 'unreachable'} "
                f"(status: {response.status_code})"
            )
            return is_reachable
        except Exception as e:
            logger.warning(
                f"A2A service at {base_url} is not reachable: {type(e).__name__}: {str(e)}"
            )
            return False
        finally:
            await temp_client.aclose()

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
            if hasattr(self, 'http_client'):
                if not self.http_client.is_closed:
                    await self.http_client.aclose()
        except Exception as e:
            logger.error(f"Error during A2A agent cleanup: {e}")

    def _extract_text_from_parts(self, parts: List[Any]) -> str:
        r"""Extract text content from parts list.
        
        Args:
            parts: List of Part objects that may contain TextPart.
            
        Returns:
            Extracted text content or empty string if not found.
        """
        from a2a.types import TextPart

        if not parts:
            return ""
        
        for part in parts:
            if hasattr(part, 'root') and isinstance(part.root, TextPart):
                return part.root.text
        return ""

    def _extract_result_content(self, result_task: Any) -> str:
        r"""Extract result content from various possible locations.
        
        Tries multiple fallback options to extract text content from the task
        result in this order:
        1. status.message.parts
        2. artifacts[0].parts
        3. parts attribute
        
        Args:
            result_task: The result task object from A2A response.
            
        Returns:
            Extracted text content or empty string if not found.
        """
        # Try to extract text from status message
        if (
            hasattr(result_task, "status")
            and result_task.status
            and hasattr(result_task.status, "message")
            and result_task.status.message
        ):
            content = self._extract_text_from_parts(
                result_task.status.message.parts
            )
            if content:
                return content

        # Fallback to artifacts
        if (
            hasattr(result_task, "artifacts")
            and result_task.artifacts
            and len(result_task.artifacts) > 0
        ):
            content = self._extract_text_from_parts(
                result_task.artifacts[0].parts
            )
            if content:
                return content

        # Fallback to parts
        if hasattr(result_task, 'parts'):
            content = self._extract_text_from_parts(
                getattr(result_task, 'parts', [])
            )
            if content:
                return content

        return ""

    def _extract_token_usage(
        self, response: Optional[Any]
    ) -> Dict[str, int]:
        r"""Extract token usage from A2A response.
        
        Args:
            response: The response object from A2A service.
            
        Returns:
            Dictionary containing token usage information.
        """
        token_count = 0
        if response and hasattr(response, 'result') and response.result:
            # Try to get token_count directly
            token_count = getattr(response.result, 'token_count', 0)
            # Try to get from usage object
            if token_count == 0 and hasattr(response.result, 'usage'):
                token_count = getattr(
                    response.result.usage, 'total_tokens', 0
                )
        return {"total_tokens": token_count}

    async def _send_a2a_message(
        self, message: str
    ) -> "SendMessageSuccessResponse | InvalidAgentResponseError":
        r"""Sends a message to the A2A agent and returns the structured
        response.
        
        Raises:
            A2AResponseError: If the response is unexpected or invalid.
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
            message_id=str(uuid.uuid4()),
            context_id=self.context_id,
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
            error_msg = (
                f"A2A JSONRPC Error: {response.root.error.message}"
                if hasattr(response.root, 'error') and hasattr(response.root.error, 'message')
                else f"A2A JSONRPC Error: {response.root}"
            )
            raise A2AResponseError(error_msg) from None
        else:
            error_msg = (
                f"Unexpected response type: {type(response.root).__name__}, "
                f"response: {response.root}"
            )
            raise A2AResponseError(error_msg)

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

        response = None
        try:
            dependency_tasks_info = self._get_dep_tasks_info(dependencies)
            prompt = PROCESS_TASK_PROMPT.format(
                content=task.content,
                parent_task_content=task.parent.content if task.parent else "",
                dependency_tasks_info=dependency_tasks_info,
                additional_info=task.additional_info,
            )

            logger.debug(f"Sending message to A2A agent: {self.node_id}")
            response = await self._send_a2a_message(prompt)

            # Update context ID safely using getattr
            context_id = getattr(
                getattr(response, 'result', None), 'contextId', None
            )
            if context_id:
                self.context_id = context_id
                logger.debug(f"Updated context_id: {self.context_id}")

            if isinstance(response, SendMessageSuccessResponse):
                result_task = response.result
                task_result_content = self._extract_result_content(result_task)

                if not task_result_content:
                    task_result_content = (
                        "Task completed, but no text content found in response"
                    )

                task.result = task_result_content
                logger.info(
                    f"Task {task.id} completed successfully. "
                    f"Result length: {len(task_result_content)}"
                )

            elif isinstance(response, InvalidAgentResponseError):
                error_obj = getattr(response, "error", None)
                error_msg = (
                    f"Error from A2A Agent: {error_obj.message}"
                    if error_obj and hasattr(error_obj, "message")
                    else f"Error from A2A Agent: {response!s}"
                )
                task.result = error_msg
                logger.error(f"A2A agent error for task {task.id}: {error_msg}")
                return TaskState.FAILED

        except A2AMessageError as e:
            error_msg = f"A2A message error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            task.result = error_msg
            return TaskState.FAILED
        except A2AResponseError as e:
            error_msg = f"A2A response error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            task.result = error_msg
            return TaskState.FAILED
        except Exception as e:
            error_msg = f"Exception during A2A call: {type(e).__name__}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            task.result = error_msg
            return TaskState.FAILED
        finally:
            # Record worker attempt details
            if task.additional_info is None:
                task.additional_info = {}

            if "worker_attempts" not in task.additional_info:
                task.additional_info["worker_attempts"] = []

            token_usage = self._extract_token_usage(response)

            task.additional_info["worker_attempts"].append(
                {
                    "agent_id": self.node_id,
                    "timestamp": str(datetime.datetime.now()),
                    "description": (
                        f"A2A worker {self.node_id} processed task: "
                        f"{task.content}"
                    ),
                    "response_content": str(response) if response else "",
                    "tool_calls": None,
                    "total_tokens": token_usage.get("total_tokens", 0),
                }
            )
            task.additional_info["token_usage"] = token_usage

        if is_task_result_insufficient(task):
            logger.warning(f"Task {task.id}: Content validation failed")
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
