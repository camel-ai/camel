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
import asyncio
import os
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from typing import Any, Dict, Generator, List, Optional

from camel.logger import get_logger
from camel.utils import dependencies_required

logger = get_logger(__name__)

_agent_session_id_var: ContextVar[Optional[str]] = ContextVar(
    'agent_session_id', default=None
)

# Global flag to track if Langfuse has been configured
_langfuse_configured = False

try:
    from langfuse import Langfuse, get_client, observe, propagate_attributes

    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False

    def observe(*args, **kwargs):  # type: ignore[misc]
        def decorator(func):
            return func

        return decorator

    @contextmanager
    def propagate_attributes(*args, **kwargs):  # type: ignore[misc]
        yield


@dependencies_required('langfuse')
def configure_langfuse(
    public_key: Optional[str] = None,
    secret_key: Optional[str] = None,
    host: Optional[str] = None,
    debug: Optional[bool] = None,
    enabled: Optional[bool] = None,
):
    r"""Configure Langfuse for CAMEL models.

    Args:
        public_key(Optional[str]): Langfuse public key. Can be set via LANGFUSE_PUBLIC_KEY.
            (default: :obj:`None`)
        secret_key(Optional[str]): Langfuse secret key. Can be set via LANGFUSE_SECRET_KEY.
            (default: :obj:`None`)
        host(Optional[str]): Langfuse host URL. Can be set via LANGFUSE_HOST.
            (default: :obj:`https://cloud.langfuse.com`)
        debug(Optional[bool]): Enable debug mode. Can be set via LANGFUSE_DEBUG.
            (default: :obj:`None`)
        enabled(Optional[bool]): Enable/disable tracing. Can be set via LANGFUSE_ENABLED.
            (default: :obj:`None`)

    Note:
        This function initializes the Langfuse v4 client (OpenTelemetry-based)
            used by the @observe() decorator and by
            :func:`with_langfuse_trace`. Set enabled=False to disable all
            tracing.
    """  # noqa: E501
    global _langfuse_configured

    # Get configuration from environment or parameters
    public_key = public_key or os.environ.get("LANGFUSE_PUBLIC_KEY")
    secret_key = secret_key or os.environ.get("LANGFUSE_SECRET_KEY")
    host = host or os.environ.get(
        "LANGFUSE_HOST", "https://cloud.langfuse.com"
    )
    debug = (
        debug
        if debug is not None
        else os.environ.get("LANGFUSE_DEBUG", "False").lower() == "true"
    )

    # Handle enabled parameter
    if enabled is None:
        env_enabled_str = os.environ.get("LANGFUSE_ENABLED")
        if env_enabled_str is not None:
            enabled = env_enabled_str.lower() == "true"
        else:
            enabled = False  # Default to disabled

    # If not enabled, don't configure anything and don't call langfuse function
    if not enabled:
        _langfuse_configured = False
        logger.info("Langfuse tracing disabled for CAMEL models")
        return

    logger.debug(
        f"Configuring Langfuse - enabled: {enabled}, "
        f"public_key: {'***' + public_key[-4:] if public_key else None}, "
        f"host: {host}, debug: {debug}"
    )
    if enabled and public_key and secret_key and LANGFUSE_AVAILABLE:
        _langfuse_configured = True
    else:
        _langfuse_configured = False

    try:
        # Initializing a Langfuse client registers it as the process-wide
        # singleton returned by langfuse.get_client().
        Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
            debug=debug,
            # Always True here since we checked `enabled` above.
            tracing_enabled=True,
        )

        logger.info("Langfuse tracing enabled for CAMEL models")

    except Exception as e:
        logger.error(f"Failed to configure Langfuse: {e}")


def is_langfuse_available() -> bool:
    r"""Check if Langfuse is configured."""
    return _langfuse_configured


def set_current_agent_session_id(session_id: str) -> None:
    r"""Set the session ID for the current agent in context-local storage.

    This is safe to use in both sync and async contexts.
    In async contexts, each coroutine maintains its own value.

    Args:
        session_id(str): The session ID to set for the current agent.
    """
    _agent_session_id_var.set(session_id)


def get_current_agent_session_id() -> Optional[str]:
    r"""Get the session ID for the current agent from context-local storage.

    This is safe to use in both sync and async contexts.
    In async contexts, returns the value for the current coroutine.

    Returns:
        Optional[str]: The session ID for the current agent.
    """
    return _agent_session_id_var.get()


@contextmanager
def _trace_scope(
    session_id: Optional[str],
    metadata: Optional[Dict[str, Any]],
    tags: Optional[List[str]],
) -> Generator[None, None, None]:
    r"""Best-effort context manager around :func:`propagate_attributes`.

    No-ops when Langfuse isn't configured, so it is always safe to enter
    unconditionally.
    """
    if not is_langfuse_available():
        yield
        return

    with propagate_attributes(
        session_id=session_id, metadata=metadata, tags=tags
    ):
        yield


def with_langfuse_trace(func):
    r"""Decorator that scopes Langfuse trace propagation around a model
    backend's ``_run``/``_arun`` implementation.

    This replaces the previous per-provider imperative
    ``update_langfuse_trace(...)`` call at the top of ``_run``/``_arun``.
    Langfuse v4 removed the v2 ``langfuse_context.update_current_trace``
    API; trace-level attributes (session id, tags, metadata) must instead
    be applied via a :func:`~langfuse.propagate_attributes` scope that
    covers the observation they should attach to. Wrapping the whole
    ``_run``/``_arun`` call is the closest equivalent to the old
    "update trace, then run" behavior.
    """

    def _scope(self) -> Any:
        session_id = get_current_agent_session_id()
        metadata = {
            "source": "camel",
            "agent_id": session_id,
            "agent_type": "camel_chat_agent",
            "model_type": str(self.model_type),
        }
        tags = ["CAMEL-AI", str(self.model_type)]
        return _trace_scope(session_id, metadata, tags)

    if asyncio.iscoroutinefunction(func):

        @wraps(func)
        async def async_wrapper(self, *args, **kwargs):
            with _scope(self):
                return await func(self, *args, **kwargs)

        return async_wrapper

    @wraps(func)
    def sync_wrapper(self, *args, **kwargs):
        with _scope(self):
            return func(self, *args, **kwargs)

    return sync_wrapper


def update_langfuse_trace(
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,
) -> bool:
    r"""Update the current Langfuse trace with session ID and metadata.

    Args:
        session_id(Optional[str]): Optional session ID to use. If :obj:`None`
            uses the current agent's session ID. (default: :obj:`None`)
        user_id(Optional[str]): Optional user ID for the trace.
            (default: :obj:`None`)
        metadata(Optional[Dict[str, Any]]): Optional metadata dictionary.
            (default: :obj:`None`)
        tags(Optional[List[str]]): Optional list of tags.
            (default: :obj:`None`)

    Returns:
        bool: True if update was successful, False otherwise.

    Note:
        Langfuse v4 has no direct equivalent of the v2
        ``update_current_trace`` call: attribute propagation to the active
        observation and its children is scoped via
        ``langfuse.propagate_attributes(...)``. This function enters that
        scope for the remainder of the current execution context (it is
        not exited), which mirrors the previous fire-and-forget behavior.
        New CAMEL model backends should prefer :func:`with_langfuse_trace`,
        which scopes propagation to exactly the ``_run``/``_arun`` call.
    """
    if not is_langfuse_available():
        return False

    # Use provided session_id or get from thread-local storage
    final_session_id = session_id or get_current_agent_session_id()

    update_data: Dict[str, Any] = {}
    if final_session_id:
        update_data["session_id"] = final_session_id
    if user_id:
        update_data["user_id"] = user_id
    if metadata:
        update_data["metadata"] = metadata
    if tags:
        update_data["tags"] = tags

    if update_data:
        propagate_attributes(**update_data).__enter__()
        return True

    return False


def update_current_observation(
    input: Optional[Dict[str, Any]] = None,
    output: Optional[Dict[str, Any]] = None,
    model: Optional[str] = None,
    model_parameters: Optional[Dict[str, Any]] = None,
    usage_details: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> None:
    r"""Update the current Langfuse observation with input, output,
    model, model_parameters, and usage_details.

    Args:
        input(Optional[Dict[str, Any]]): Optional input dictionary.
            (default: :obj:`None`)
        output(Optional[Dict[str, Any]]): Optional output dictionary.
            (default: :obj:`None`)
        model(Optional[str]): Optional model name. (default: :obj:`None`)
        model_parameters(Optional[Dict[str, Any]]): Optional model parameters
            dictionary. (default: :obj:`None`)
        usage_details(Optional[Dict[str, Any]]): Optional usage details
            dictionary. (default: :obj:`None`)

    Returns:
        None
    """
    if not is_langfuse_available():
        return

    # The v2 API accepted a generic `usage` kwarg; v4's
    # `update_current_generation` only accepts `usage_details`.
    if usage_details is None and "usage" in kwargs:
        usage_details = kwargs.pop("usage")

    allowed_extra = {
        "name",
        "metadata",
        "version",
        "level",
        "status_message",
        "completion_start_time",
        "cost_details",
        "prompt",
    }
    unknown = set(kwargs) - allowed_extra
    if unknown:
        logger.debug(
            f"Ignoring unsupported Langfuse observation fields: "
            f"{sorted(unknown)}"
        )
    extra = {k: v for k, v in kwargs.items() if k in allowed_extra}

    get_client().update_current_generation(
        input=input,
        output=output,
        model=model,
        model_parameters=model_parameters,
        usage_details=usage_details,
        **extra,
    )


def get_langfuse_status() -> Dict[str, Any]:
    r"""Get detailed Langfuse configuration status for debugging.

    Returns:
        Dict[str, Any]: Status information including configuration state.
    """
    env_enabled_str = os.environ.get("LANGFUSE_ENABLED")
    env_enabled = (
        env_enabled_str.lower() == "true" if env_enabled_str else None
    )

    status = {
        "configured": _langfuse_configured,
        "has_public_key": bool(os.environ.get("LANGFUSE_PUBLIC_KEY")),
        "has_secret_key": bool(os.environ.get("LANGFUSE_SECRET_KEY")),
        "env_enabled": env_enabled,
        "host": os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        "debug": os.environ.get("LANGFUSE_DEBUG", "false").lower() == "true",
        "current_session_id": get_current_agent_session_id(),
    }

    if _langfuse_configured:
        try:
            # Try to get some context information
            status["langfuse_context_available"] = True
        except Exception as e:
            status["langfuse_context_error"] = str(e)

    return status
