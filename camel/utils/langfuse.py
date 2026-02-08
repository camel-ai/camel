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
import atexit
import os
from contextvars import ContextVar
from typing import Any, Dict, List, Optional

from camel.logger import get_logger
from camel.utils import dependencies_required

logger = get_logger(__name__)

_agent_session_id_var: ContextVar[Optional[str]] = ContextVar(
    'agent_session_id', default=None
)

# Global flag to track if Langfuse has been configured
_langfuse_configured = False
_langfuse_exit_handler_registered = False


def _to_primitive_str(value: Any) -> str:
    r"""Convert values to a built-in ``str`` instance.

    Some model enums in CAMEL subclass ``str`` and can survive ``str(value)``
    as a non-primitive subclass instance, which breaks OpenTelemetry tag type
    checks. This helper guarantees a plain Python ``str``.
    """
    if isinstance(value, str):
        return str.__str__(value)
    return str(value)


def _normalize_usage_details(value: Any) -> Optional[Dict[str, Any]]:
    r"""Normalize usage payloads to dictionaries expected by Langfuse v3."""
    if value is None:
        return None
    if isinstance(value, dict):
        return value

    # Pydantic/OpenAI-like usage objects
    for method_name in ("model_dump", "dict"):
        method = getattr(value, method_name, None)
        if callable(method):
            try:
                dumped = method()
                if isinstance(dumped, dict):
                    return dumped
            except Exception:
                pass

    # Attribute-style usage objects
    usage_details: Dict[str, Any] = {}
    for key in (
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "input_tokens",
        "output_tokens",
        "cache_creation_input_tokens",
        "cache_read_input_tokens",
    ):
        if hasattr(value, key):
            usage_details[key] = getattr(value, key)

    return usage_details or None


def _flush_langfuse_at_exit() -> None:
    r"""Best-effort Langfuse flush/shutdown on process exit."""
    if not is_langfuse_available():
        return
    try:
        langfuse = _get_langfuse_client()
    except Exception:
        return

    flush = getattr(langfuse, "flush", None)
    if callable(flush):
        try:
            flush()
        except Exception:
            pass

    shutdown = getattr(langfuse, "shutdown", None)
    if callable(shutdown):
        try:
            shutdown()
        except Exception:
            pass


def _register_langfuse_exit_handler() -> None:
    r"""Register Langfuse exit handler exactly once."""
    global _langfuse_exit_handler_registered
    if _langfuse_exit_handler_registered:
        return
    atexit.register(_flush_langfuse_at_exit)
    _langfuse_exit_handler_registered = True


try:
    from langfuse import get_client as _get_langfuse_client

    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False

# Auto-configure when env vars are present at import time
if (
    LANGFUSE_AVAILABLE
    and os.environ.get("LANGFUSE_ENABLED", "False").lower() == "true"
    and os.environ.get("LANGFUSE_PUBLIC_KEY")
    and os.environ.get("LANGFUSE_SECRET_KEY")
):
    _langfuse_configured = True
    _register_langfuse_exit_handler()


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
        In Langfuse v3, configuration is handled automatically via environment
        variables (LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST).
        This function sets those env vars if provided as parameters and
        validates the configuration.
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

    # If not enabled, don't configure anything
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
        # In Langfuse v3, set env vars so the client auto-configures
        if public_key:
            os.environ["LANGFUSE_PUBLIC_KEY"] = public_key
        if secret_key:
            os.environ["LANGFUSE_SECRET_KEY"] = secret_key
        if host:
            os.environ["LANGFUSE_HOST"] = host
        if debug:
            os.environ["LANGFUSE_DEBUG"] = str(debug).lower()

        # Validate by getting the client
        _get_langfuse_client()
        _register_langfuse_exit_handler()

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
    if is_langfuse_available():
        return _agent_session_id_var.get()
    return None


def update_langfuse_trace(
    name: Optional[str] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,
) -> bool:
    r"""Update the current Langfuse trace with session ID and metadata.

    Args:
        name(Optional[str]): Optional display name for the current trace.
            (default: :obj:`None`)
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
    """
    if not is_langfuse_available():
        return False

    # Use provided session_id or get from thread-local storage
    final_session_id = session_id or get_current_agent_session_id()

    update_data: Dict[str, Any] = {}
    if name:
        update_data["name"] = _to_primitive_str(name)
    if final_session_id:
        update_data["session_id"] = final_session_id
    if user_id:
        update_data["user_id"] = user_id
    if metadata:
        update_data["metadata"] = metadata
    if tags:
        # Ensure tags are primitive strings for OpenTelemetry export.
        update_data["tags"] = [
            _to_primitive_str(tag) for tag in tags if tag is not None
        ]

    if update_data:
        langfuse = _get_langfuse_client()
        langfuse.update_current_trace(**update_data)
        return True

    return False


def update_current_observation(
    input: Optional[Dict[str, Any]] = None,
    output: Optional[Dict[str, Any]] = None,
    model: Optional[str] = None,
    model_parameters: Optional[Dict[str, Any]] = None,
    usage_details: Optional[Any] = None,
    **kwargs: Any,
) -> None:
    r"""Update the current Langfuse observation with input, output,
    model, model_parameters, and usage_details.

    In Langfuse v3, model-related params (model, model_parameters,
    usage_details) go to ``update_current_generation()`` while
    span-level params (input, output, metadata) go to
    ``update_current_span()``.

    Args:
        input(Optional[Dict[str, Any]]): Optional input dictionary.
            (default: :obj:`None`)
        output(Optional[Dict[str, Any]]): Optional output dictionary.
            (default: :obj:`None`)
        model(Optional[str]): Optional model name. (default: :obj:`None`)
        model_parameters(Optional[Dict[str, Any]]): Optional model parameters
            dictionary. (default: :obj:`None`)
        usage_details(Optional[Any]): Optional usage details. Accepts dicts or
            provider usage objects that can be normalized.
            (default: :obj:`None`)

    Returns:
        None
    """
    if not is_langfuse_available():
        return

    langfuse = _get_langfuse_client()

    # Generation-level params (model, model_parameters, usage_details)
    gen_data: Dict[str, Any] = {}
    if model is not None:
        gen_data["model"] = model
    if model_parameters is not None:
        gen_data["model_parameters"] = model_parameters
    normalized_usage_details = _normalize_usage_details(usage_details)
    if normalized_usage_details is not None:
        gen_data["usage_details"] = normalized_usage_details

    # Span-level params (input, output, metadata, etc.)
    span_data: Dict[str, Any] = {}
    if input is not None:
        span_data["input"] = input
    if output is not None:
        span_data["output"] = output
    span_data.update(kwargs)

    if gen_data:
        langfuse.update_current_generation(**gen_data)
    if span_data:
        langfuse.update_current_span(**span_data)


def get_langfuse_tool_name(tool: Any) -> Optional[str]:
    r"""Get a stable tool identifier for Langfuse metadata.

    For bound toolkit methods this returns values like
    ``SearchToolkit.search_google``.
    """
    if tool is None:
        return None
    func = getattr(tool, "func", tool)
    qualname = getattr(func, "__qualname__", "")
    if isinstance(qualname, str) and qualname:
        return qualname.replace(".<locals>.", ".")
    name = getattr(func, "__name__", "")
    if isinstance(name, str) and name:
        return name
    return None


def _normalize_role_type(role_type: Any) -> str:
    value = getattr(role_type, "value", role_type)
    return _to_primitive_str(value).strip().lower()


def serialize_langfuse_step_input(
    input_message: Any, response_format: Optional[Any]
) -> Dict[str, Any]:
    r"""Build a compact, serializable step input payload."""
    if (
        hasattr(input_message, "role_name")
        and hasattr(input_message, "role_type")
        and hasattr(input_message, "content")
    ):
        message_payload: Dict[str, Any] = {
            "role_name": getattr(input_message, "role_name", "user"),
            "role_type": _normalize_role_type(
                getattr(input_message, "role_type", "user")
            ),
            "content": getattr(input_message, "content", None),
        }
    else:
        message_payload = {
            "role_name": "user",
            "role_type": "user",
            "content": _to_primitive_str(input_message),
        }

    response_format_name = None
    if response_format is not None:
        response_format_name = getattr(
            response_format, "__name__", _to_primitive_str(response_format)
        )

    return {
        "input_message": message_payload,
        "response_format": response_format_name,
    }


def serialize_langfuse_step_output(
    response: Any, tool_call_records: Optional[List[Any]] = None
) -> Dict[str, Any]:
    r"""Build a compact step output payload for observation output."""
    msgs_payload = [
        {
            "role_name": getattr(msg, "role_name", None),
            "role_type": _normalize_role_type(getattr(msg, "role_type", None)),
            "content": getattr(msg, "content", None),
        }
        for msg in (getattr(response, "msgs", None) or [])
    ]

    info = getattr(response, "info", None) or {}
    if not isinstance(info, dict):
        info = {}

    tool_calls_payload: List[Dict[str, Any]] = []
    for record in tool_call_records or []:
        tool_calls_payload.append(
            {
                "tool_name": getattr(record, "tool_name", None),
                "tool_call_id": getattr(record, "tool_call_id", None),
                "args": getattr(record, "args", None),
                "result": _to_primitive_str(getattr(record, "result", ""))[
                    :500
                ],
            }
        )

    return {
        "terminated": getattr(response, "terminated", None),
        "msgs": msgs_payload,
        "info": {
            "id": info.get("id"),
            "usage": info.get("usage"),
            "termination_reasons": info.get("termination_reasons"),
            "num_tokens": info.get("num_tokens"),
            "external_tool_call_requests": info.get(
                "external_tool_call_requests"
            ),
        },
        "tool_calls": tool_calls_payload,
    }


def serialize_langfuse_model_response_input(
    openai_messages: List[Any],
    response_format: Optional[Any],
    tool_schemas: Optional[List[Dict[str, Any]]],
) -> Dict[str, Any]:
    r"""Build compact model-response span input payload."""
    response_format_name = None
    if response_format is not None:
        response_format_name = getattr(
            response_format, "__name__", _to_primitive_str(response_format)
        )

    tool_names: List[str] = []
    for schema in tool_schemas or []:
        try:
            tool_name = schema.get("function", {}).get("name")
            if tool_name:
                tool_names.append(_to_primitive_str(tool_name))
        except Exception:
            continue

    return {
        "num_messages": len(openai_messages),
        "messages": openai_messages,
        "response_format": response_format_name,
        "tool_names": tool_names,
    }


def serialize_langfuse_model_response_output(
    model_response: Any,
) -> Dict[str, Any]:
    r"""Build compact model-response span output payload."""
    tool_names: List[str] = []
    tool_call_requests = getattr(model_response, "tool_call_requests", None)
    if tool_call_requests:
        tool_names = [
            _to_primitive_str(getattr(req, "tool_name", ""))
            for req in tool_call_requests
        ]

    msgs_payload = [
        {
            "role_name": getattr(msg, "role_name", None),
            "role_type": _normalize_role_type(getattr(msg, "role_type", None)),
            "content": getattr(msg, "content", None),
        }
        for msg in (getattr(model_response, "output_messages", None) or [])
    ]

    return {
        "response_id": getattr(model_response, "response_id", None),
        "finish_reasons": getattr(model_response, "finish_reasons", None),
        "usage": getattr(model_response, "usage_dict", None),
        "tool_call_names": tool_names,
        "msgs": msgs_payload,
    }


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


def observe(*args, **kwargs):
    def decorator(func):
        return func

    return decorator
