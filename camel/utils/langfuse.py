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
import os
import threading
from typing import Any, Dict, List, Optional

from camel.logger import get_logger
from camel.utils import dependencies_required

logger = get_logger(__name__)
# Thread-local storage for agent session IDs
_local = threading.local()

# Global flag to track if Langfuse has been configured
_langfuse_configured = False

try:
    from langfuse.decorators import langfuse_context

    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False


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
        This function configures the native langfuse_context which works with
            @observe() decorators. Set enabled=False to disable all tracing.
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
        # Configure langfuse_context with native method
        langfuse_context.configure(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
            debug=debug,
            enabled=True,  # Always True here since we checked enabled above
        )

        logger.info("Langfuse tracing enabled for CAMEL models")

    except Exception as e:
        logger.error(f"Failed to configure Langfuse: {e}")


def is_langfuse_available() -> bool:
    r"""Check if Langfuse is configured."""
    return _langfuse_configured


def set_current_agent_session_id(session_id: str) -> None:
    r"""Set the session ID for the current agent in thread-local storage.

    Args:
        session_id(str): The session ID to set for the current agent.
    """

    _local.agent_session_id = session_id


def get_current_agent_session_id() -> Optional[str]:
    r"""Get the session ID for the current agent from thread-local storage.

    Returns:
        Optional[str]: The session ID for the current agent.
    """
    if is_langfuse_available():
        return getattr(_local, 'agent_session_id', None)
    return None


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
        langfuse_context.update_current_trace(**update_data)
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

    langfuse_context.update_current_observation(
        input=input,
        output=output,
        model=model,
        model_parameters=model_parameters,
        usage_details=usage_details,
        **kwargs,
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


def observe(*args, **kwargs):
    def decorator(func):
        return func

    return decorator
