import asyncio
import threading
import logging
from typing import List, Optional, Type, Union
from pydantic import BaseModel
import os


# --- CAMEL Imports ---
from camel.responses import ChatAgentResponse
from camel.types import (
    ChatCompletion,
    ChatCompletionChunk,
    ModelPlatformType,
    ModelType,
    OpenAIBackendRole,
    RoleType,
)
from camel.memories import (
    AgentMemory,
    ChatHistoryMemory,
    ContextRecord,
    MemoryRecord,
    ScoreBasedContextCreator,
)
# Langfuse decorator setting
if os.environ.get("LANGFUSE_ENABLED", "False").lower() == "true":
    try:
        from langfuse.decorators import observe
    except ImportError:
        from camel.utils import observe
elif os.environ.get("TRACEROOT_ENABLED", "False").lower() == "true":
    try:
        from traceroot import trace as observe  # type: ignore[import]
    except ImportError:
        from camel.utils import observe
else:
    from camel.utils import observe
from camel.messages import BaseMessage
from camel.agents import ChatAgent
from camel.types.agents import ToolCallingRecord
from camel.agents._types import ModelResponse, ToolCallRequest
logger = logging.getLogger(__name__)

class RLAgent(ChatAgent):
    """A reinforcement learning agent."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize RL-specific parameters here


    @observe()
    async def astep(
        self,
        input_message: Union[BaseMessage, str],
        response_format: Optional[Type[BaseModel]] = None,
    ) -> Union[ChatAgentResponse]:
        r"""Performs a single step in the chat session by generating a response
        to the input message. This agent step can call async function calls.

        Args:
            input_message (Union[BaseMessage, str]): The input message to the
                agent. For BaseMessage input, its `role` field that specifies
                the role at backend may be either `user` or `assistant` but it
                will be set to `user` anyway since for the self agent any
                incoming message is external. For str input, the `role_name`
                would be `User`.
            response_format (Optional[Type[BaseModel]], optional): A pydantic
                model class that includes value types and field descriptions
                used to generate a structured response by LLM. This schema
                helps in defining the expected output format. (default:
                :obj:`None`)
        Returns:
            Union[ChatAgentResponse, AsyncStreamingChatAgentResponse]:
                If stream is False, returns a ChatAgentResponse. If stream is
                True, returns an AsyncStreamingChatAgentResponse that can be
                awaited for the final result or async iterated for streaming
                updates.

        Raises:
            asyncio.TimeoutError: If the step operation exceeds the configured
                timeout.
        """

        try:
            from camel.utils.langfuse import set_current_agent_session_id

            set_current_agent_session_id(self.agent_id)
        except ImportError:
            pass  # Langfuse not available

        stream = self.model_backend.model_config_dict.get("stream", False)
        if stream:
            # Return wrapped async generator that is awaitable
            raise NotImplementedError()
        else:
            if self.step_timeout is not None:
                try:
                    return await asyncio.wait_for(
                        self._astep_non_streaming_task(
                            input_message, response_format
                        ),
                        timeout=self.step_timeout,
                    )
                except asyncio.TimeoutError:
                    raise asyncio.TimeoutError(
                        f"Async step timed out after {self.step_timeout}s"
                    )
            else:
                return await self._astep_non_streaming_task(
                    input_message, response_format
                )


    async def _astep_non_streaming_task(
        self,
        input_message: Union[BaseMessage, str],
        response_format: Optional[Type[BaseModel]] = None,
    ) -> ChatAgentResponse:
        r"""Internal async method for non-streaming astep logic."""

        try:
            from camel.utils.langfuse import set_current_agent_session_id

            set_current_agent_session_id(self.agent_id)
        except ImportError:
            pass  # Langfuse not available

        # Check if this call is from a RegisteredAgentToolkit to prevent tool
        # use
        disable_tools = self._is_called_from_registered_toolkit()

        # Handle response format compatibility with non-strict tools
        original_response_format = response_format
        input_message, response_format, used_prompt_formatting = (
            self._handle_response_format_with_non_strict_tools(
                input_message, response_format
            )
        )

        if isinstance(input_message, str):
            input_message = BaseMessage.make_user_message(
                role_name="User", content=input_message
            )

        self.update_memory(input_message, OpenAIBackendRole.USER)

        tool_call_records: List[ToolCallingRecord] = []
        external_tool_call_requests: Optional[List[ToolCallRequest]] = None
        accumulated_context_tokens = (
            0  # This tracks cumulative context tokens, not API usage tokens
        )

        # Initialize token usage tracker
        step_token_usage = self._create_token_usage_tracker()
        iteration_count: int = 0
        prev_num_openai_messages: int = 0

        while True:
            if self.pause_event is not None and not self.pause_event.is_set():
                if isinstance(self.pause_event, asyncio.Event):
                    await self.pause_event.wait()
                elif isinstance(self.pause_event, threading.Event):
                    # For threading.Event in async context, run in executor
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, self.pause_event.wait)
            try:
                openai_messages, num_tokens = self.memory.get_context()
                if self.summarize_threshold is not None:
                    threshold = self._calculate_next_summary_threshold()
                    summary_token_count = self._summary_token_count
                    token_limit = self.model_backend.token_limit

                    if num_tokens <= token_limit:
                        if (
                            summary_token_count
                            > token_limit * self.summary_window_ratio
                        ):
                            logger.info(
                                f"Summary tokens ({summary_token_count}) "
                                f"exceed limit, full compression."
                            )
                            # Summarize everything (including summaries)
                            summary = await self.asummarize(
                                include_summaries=True
                            )
                            self._update_memory_with_summary(
                                summary.get("summary", ""),
                                include_summaries=True,
                            )
                        elif num_tokens > threshold:
                            logger.info(
                                f"Token count ({num_tokens}) exceed threshold "
                                "({threshold}). Triggering summarization."
                            )
                            # Only summarize non-summary content
                            summary = await self.asummarize(
                                include_summaries=False
                            )
                            self._update_memory_with_summary(
                                summary.get("summary", ""),
                                include_summaries=False,
                            )
                accumulated_context_tokens += num_tokens
            except RuntimeError as e:
                return self._step_terminate(
                    e.args[1], tool_call_records, "max_tokens_exceeded"
                )
            # Get response from model backend with token limit error handling
            try:
                response = await self._aget_model_response(
                    openai_messages,
                    num_tokens=num_tokens,
                    current_iteration=iteration_count,
                    response_format=response_format,
                    tool_schemas=[]
                    if disable_tools
                    else self._get_full_tool_schemas(),
                    prev_num_openai_messages=prev_num_openai_messages,
                )
            except Exception as exc:
                logger.exception("Model error: %s", exc)

                if self._is_token_limit_error(exc):
                    tool_signature = self._last_tool_call_signature
                    if (
                        tool_signature is not None
                        and tool_signature
                        == self._last_token_limit_tool_signature
                    ):
                        description = self._describe_tool_call(
                            self._last_tool_call_record
                        )
                        repeated_msg = (
                            "Context exceeded again by the same tool call."
                        )
                        if description:
                            repeated_msg += f" {description}"
                        raise RuntimeError(repeated_msg) from exc

                    user_message_count = sum(
                        1
                        for msg in openai_messages
                        if getattr(msg, "role", None) == "user"
                    )
                    if (
                        user_message_count == 1
                        and getattr(openai_messages[-1], "role", None)
                        == "user"
                    ):
                        raise RuntimeError(
                            "The provided user input alone exceeds the"
                            "context window. Please shorten the input."
                        ) from exc

                    logger.warning(
                        "Token limit exceeded error detected. "
                        "Summarizing context."
                    )

                    recent_records: List[ContextRecord]
                    try:
                        recent_records = self.memory.retrieve()
                    except Exception:  # pragma: no cover - defensive guard
                        recent_records = []

                    indices_to_remove = (
                        self._find_indices_to_remove_for_last_tool_pair(
                            recent_records
                        )
                    )
                    self.memory.remove_records_by_indices(indices_to_remove)

                    summary = await self.asummarize()

                    tool_notice = self._format_tool_limit_notice()
                    summary_messages = summary.get("summary", "")

                    if tool_notice:
                        summary_messages += "\n\n" + tool_notice
                    self._update_memory_with_summary(
                        summary_messages, include_summaries=False
                    )
                    self._last_token_limit_tool_signature = tool_signature
                    return await self._astep_non_streaming_task(
                        input_message, response_format
                    )

                raise

            prev_num_openai_messages = len(openai_messages)
            iteration_count += 1

            # Accumulate API token usage
            self._update_token_usage_tracker(
                step_token_usage, response.usage_dict
            )

            # Terminate Agent if stop_event is set
            if self.stop_event and self.stop_event.is_set():
                # Use the _step_terminate to terminate the agent with reason
                logger.info(
                    f"Termination triggered at iteration {iteration_count}"
                )
                return self._step_terminate(
                    accumulated_context_tokens,
                    tool_call_records,
                    "termination_triggered",
                )

            if tool_call_requests := response.tool_call_requests:
                # Process all tool calls
                for tool_call_request in tool_call_requests:
                    if (
                        tool_call_request.tool_name
                        in self._external_tool_schemas
                    ):
                        if external_tool_call_requests is None:
                            external_tool_call_requests = []
                        external_tool_call_requests.append(tool_call_request)
                    else:
                        if (
                            self.pause_event is not None
                            and not self.pause_event.is_set()
                        ):
                            if isinstance(self.pause_event, asyncio.Event):
                                await self.pause_event.wait()
                            elif isinstance(self.pause_event, threading.Event):
                                loop = asyncio.get_event_loop()
                                await loop.run_in_executor(
                                    None, self.pause_event.wait
                                )
                        tool_call_record = await self._aexecute_tool(
                            tool_call_request
                        )
                        tool_call_records.append(tool_call_record)

                # If we found an external tool call, break the loop
                if external_tool_call_requests:
                    break

                if (
                    self.max_iteration is not None
                    and iteration_count >= self.max_iteration
                ):
                    break

                # If we're still here, continue the loop
                continue

            break

        await self._aformat_response_if_needed(response, response_format)

        # Apply manual parsing if we used prompt-based formatting
        if used_prompt_formatting and original_response_format:
            self._apply_prompt_based_parsing(
                response, original_response_format
            )

        self._record_final_output(response.output_messages)

        # Clean tool call messages from memory after response generation
        if self.prune_tool_calls_from_memory and tool_call_records:
            self.memory.clean_tool_calls()

        self._last_token_limit_user_signature = None

        return self._convert_to_chatagent_response(
            response,
            tool_call_records,
            accumulated_context_tokens,
            external_tool_call_requests,
            step_token_usage["prompt_tokens"],
            step_token_usage["completion_tokens"],
            step_token_usage["total_tokens"],
        )