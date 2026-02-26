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
import os
from contextvars import ContextVar
from typing import Any, Callable, Dict, List, Optional

from camel.logger import get_logger
from camel.utils import dependencies_required

logger = get_logger(__name__)

_agent_session_id_var: ContextVar[Optional[str]] = ContextVar(
    'agent_session_id', default=None
)

# Global flag to track if Langfuse has been configured
_langfuse_configured = False

try:
    from langfuse import get_client

    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    get_client: Optional[Callable[..., Any]] = None


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
        In Langfuse v3+, the @observe() decorator automatically reads
        configuration from environment variables. This function sets the
        environment variables so that @observe() decorators work correctly.
        Set enabled=False to disable all tracing.
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
        os.environ["LANGFUSE_ENABLED"] = "false"
        return

    # Set environment variables for Langfuse v3+ @observe() decorator
    # The decorator automatically reads from these environment variables
    if public_key:
        os.environ["LANGFUSE_PUBLIC_KEY"] = public_key
    if secret_key:
        os.environ["LANGFUSE_SECRET_KEY"] = secret_key
    if host:
        os.environ["LANGFUSE_HOST"] = host
    os.environ["LANGFUSE_DEBUG"] = "true" if debug else "false"
    os.environ["LANGFUSE_ENABLED"] = "true"

    logger.debug(
        f"Configuring Langfuse - enabled: {enabled}, "
        f"public_key: {'***' + public_key[-4:] if public_key else None}, "
        f"host: {host}, debug: {debug}"
    )

    # Check if Langfuse is available and properly configured
    if enabled and public_key and secret_key and LANGFUSE_AVAILABLE:
        try:
            # Verify that Langfuse can be imported and get_client works
            if get_client is not None:
                _langfuse_configured = True
                logger.info("Langfuse tracing enabled for CAMEL models")
            else:
                _langfuse_configured = False
                logger.warning("Langfuse is not available")
        except Exception as e:
            _langfuse_configured = False
            logger.error(f"Failed to verify Langfuse configuration: {e}")
    else:
        _langfuse_configured = False
        if not LANGFUSE_AVAILABLE:
            logger.warning("Langfuse package is not installed")
        elif not public_key or not secret_key:
            logger.warning(
                "Langfuse public_key or secret_key is missing"
            )


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
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,
) -> bool:
    r"""Update the current Langfuse trace with session ID and metadata.

    Note: In Langfuse v3+, trace updates are handled automatically by the
    @observe() decorator. This function is kept for backward compatibility
    but may have limited functionality.

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
    """
    if not is_langfuse_available():
        return False

    # In Langfuse v3+, trace updates are typically handled through the
    # @observe() decorator's context. This function is kept for compatibility
    # but trace updates should be done through the decorator's metadata parameter.
    logger.debug(
        "update_langfuse_trace called - in Langfuse v3+, "
        "trace updates should be done through @observe() decorator metadata"
    )

    # Note: In v3, we cannot directly update the current trace without
    # access to the trace object. The @observe() decorator handles this.
    # This function returns True to maintain backward compatibility.
    return True


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

    Note: In Langfuse v3+, observation updates are handled automatically by the
    @observe() decorator. This function is kept for backward compatibility
    but may have limited functionality.

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

    # In Langfuse v3+, observation updates are typically handled through the
    # @observe() decorator. This function is kept for compatibility.
    logger.debug(
        "update_current_observation called - in Langfuse v3+, "
        "observation updates should be done through @observe() decorator"
    )
    # Note: Parameters are accepted but not used in v3+ as updates are
    # handled automatically by the @observe() decorator.


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

    if _langfuse_configured and LANGFUSE_AVAILABLE:
        try:
            # Try to verify Langfuse client is available
            if get_client is not None:
                status["langfuse_client_available"] = True
        except Exception as e:
            status["langfuse_client_error"] = str(e)

    return status


def observe(*args, **kwargs):
    def decorator(func):
        return func

    return decorator
