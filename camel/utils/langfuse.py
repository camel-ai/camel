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
import inspect
import os
from collections.abc import Callable
from contextvars import ContextVar
from functools import wraps
from typing import Any

from camel.logger import get_logger
from camel.utils import dependencies_required

logger = get_logger(__name__)

_agent_session_id_var: ContextVar[str | None] = ContextVar(
    'agent_session_id', default=None
)

_langfuse_configured = False
_langfuse_client: Any | None = None

try:
    import langfuse as _langfuse_sdk

    LANGFUSE_AVAILABLE = True
except ImportError:
    _langfuse_sdk = None
    LANGFUSE_AVAILABLE = False

try:
    from langfuse.decorators import (
        langfuse_context as _langfuse_v2_context,
    )
except ImportError:
    _langfuse_v2_context = None


def _is_langfuse_v3() -> bool:
    r"""Return whether the installed SDK exposes the v3 client API."""
    return _langfuse_v2_context is None and callable(
        getattr(_langfuse_sdk, 'Langfuse', None)
    )


def _get_langfuse_client() -> Any | None:
    r"""Return the configured v2 context or v3 client."""
    if _is_langfuse_v3():
        return _langfuse_client
    return _langfuse_v2_context


def _get_langfuse_observe() -> Callable[..., Any] | None:
    r"""Return the SDK's observe decorator for either supported API."""
    if _is_langfuse_v3():
        return getattr(_langfuse_sdk, 'observe', None)

    try:
        from langfuse.decorators import observe as v2_observe

        return v2_observe
    except ImportError:
        return None


def _as_usage_details(usage: Any) -> dict[str, int] | None:
    r"""Convert provider/OpenAI usage objects to Langfuse v3 details."""
    if usage is None:
        return None

    if hasattr(usage, 'model_dump'):
        usage = usage.model_dump(exclude_none=True)
    elif not isinstance(usage, dict) and hasattr(usage, 'dict'):
        usage = usage.dict(exclude_none=True)

    if not isinstance(usage, dict):
        return None

    return {
        str(key): value
        for key, value in usage.items()
        if isinstance(value, int) and not isinstance(value, bool)
    }


@dependencies_required('langfuse')
def configure_langfuse(
    public_key: str | None = None,
    secret_key: str | None = None,
    host: str | None = None,
    debug: bool | None = None,
    enabled: bool | None = None,
) -> None:
    r"""Configure Langfuse for CAMEL models.

    Supports the legacy v2 ``langfuse_context`` API and the v3 client API.

    Args:
        public_key(Optional[str]): Langfuse public key. Can be set via
            ``LANGFUSE_PUBLIC_KEY``. (default: :obj:`None`)
        secret_key(Optional[str]): Langfuse secret key. Can be set via
            ``LANGFUSE_SECRET_KEY``. (default: :obj:`None`)
        host(Optional[str]): Langfuse host URL. Can be set via
            ``LANGFUSE_BASE_URL`` or ``LANGFUSE_HOST``.
            (default: :obj:`https://cloud.langfuse.com`)
        debug(Optional[bool]): Enable debug mode. Can be set via
            ``LANGFUSE_DEBUG``. (default: :obj:`None`)
        enabled(Optional[bool]): Enable/disable tracing. Can be set via
            ``LANGFUSE_ENABLED``. (default: :obj:`None`)
    """
    global _langfuse_client, _langfuse_configured

    public_key = public_key or os.environ.get('LANGFUSE_PUBLIC_KEY')
    secret_key = secret_key or os.environ.get('LANGFUSE_SECRET_KEY')
    host = (
        host
        or os.environ.get('LANGFUSE_BASE_URL')
        or os.environ.get('LANGFUSE_HOST')
        or 'https://cloud.langfuse.com'
    )
    debug = (
        debug
        if debug is not None
        else os.environ.get('LANGFUSE_DEBUG', 'false').lower() == 'true'
    )

    if enabled is None:
        enabled = os.environ.get('LANGFUSE_ENABLED', 'false').lower() == 'true'

    if not enabled:
        _langfuse_client = None
        _langfuse_configured = False
        logger.info('Langfuse tracing disabled for CAMEL models')
        return

    if not public_key or not secret_key:
        _langfuse_client = None
        _langfuse_configured = False
        logger.warning(
            'Langfuse tracing requires both a public key and a secret key'
        )
        return

    logger.debug(
        f"Configuring Langfuse - enabled: {enabled}, "
        f"public_key: {'***' + public_key[-4:]}, "
        f"host: {host}, debug: {debug}"
    )

    try:
        if _is_langfuse_v3():
            _langfuse_client = _langfuse_sdk.Langfuse(
                public_key=public_key,
                secret_key=secret_key,
                host=host,
                debug=debug,
                tracing_enabled=True,
            )
        elif _langfuse_v2_context is not None:
            _langfuse_v2_context.configure(
                public_key=public_key,
                secret_key=secret_key,
                host=host,
                debug=debug,
                enabled=True,
            )
            _langfuse_client = None
        else:
            raise RuntimeError('Installed Langfuse SDK has no supported API')
    except Exception as exc:  # noqa: BLE001
        _langfuse_client = None
        _langfuse_configured = False
        logger.error(f'Failed to configure Langfuse: {exc}')
        return

    _langfuse_configured = True
    logger.info('Langfuse tracing enabled for CAMEL models')


def is_langfuse_available() -> bool:
    r"""Check if Langfuse is configured."""
    return _langfuse_configured


def set_current_agent_session_id(session_id: str) -> None:
    r"""Set the session ID for the current agent in context-local storage.

    This is safe to use in both sync and async contexts. In async contexts,
    each coroutine maintains its own value.

    Args:
        session_id(str): The session ID to set for the current agent.
    """
    _agent_session_id_var.set(session_id)


def get_current_agent_session_id() -> str | None:
    r"""Get the session ID for the current agent.

    Returns:
        Optional[str]: The current context-local session ID.
    """
    return _agent_session_id_var.get()


def update_langfuse_trace(
    session_id: str | None = None,
    user_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    tags: list[str] | None = None,
) -> bool:
    r"""Update the current Langfuse trace with session ID and metadata.

    Args:
        session_id(Optional[str]): Session ID. Uses the current agent session
            when omitted. (default: :obj:`None`)
        user_id(Optional[str]): User ID for the trace.
            (default: :obj:`None`)
        metadata(Optional[Dict[str, Any]]): Trace metadata.
            (default: :obj:`None`)
        tags(Optional[List[str]]): Trace tags. (default: :obj:`None`)

    Returns:
        bool: Whether an update was sent to Langfuse.
    """
    client = _get_langfuse_client()
    if not is_langfuse_available() or client is None:
        return False

    final_session_id = session_id or get_current_agent_session_id()
    update_data: dict[str, Any] = {}
    if final_session_id:
        update_data['session_id'] = final_session_id
    if user_id:
        update_data['user_id'] = user_id
    if metadata:
        update_data['metadata'] = metadata
    if tags:
        update_data['tags'] = tags

    if not update_data:
        return False

    client.update_current_trace(**update_data)
    return True


def update_current_observation(
    input: dict[str, Any] | None = None,
    output: dict[str, Any] | None = None,
    model: str | None = None,
    model_parameters: dict[str, Any] | None = None,
    usage_details: dict[str, Any] | None = None,
    **kwargs: Any,
) -> None:
    r"""Update the current Langfuse generation.

    CAMEL's model call sites are generation observations. Langfuse v2 exposes
    a generic ``update_current_observation`` method, while v3 replaces it with
    ``update_current_generation``.

    Args:
        input(Optional[Dict[str, Any]]): Generation input.
            (default: :obj:`None`)
        output(Optional[Dict[str, Any]]): Generation output.
            (default: :obj:`None`)
        model(Optional[str]): Model name. (default: :obj:`None`)
        model_parameters(Optional[Dict[str, Any]]): Model parameters.
            (default: :obj:`None`)
        usage_details(Optional[Dict[str, Any]]): Token usage details.
            (default: :obj:`None`)
        **kwargs(Any): Additional Langfuse fields. A legacy ``usage`` object
            is normalized to v3 ``usage_details``.
    """
    client = _get_langfuse_client()
    if not is_langfuse_available() or client is None:
        return

    if _is_langfuse_v3():
        legacy_usage = kwargs.pop('usage', None)
        normalized_usage = _as_usage_details(
            usage_details if usage_details is not None else legacy_usage
        )
        client.update_current_generation(
            input=input,
            output=output,
            model=model,
            model_parameters=model_parameters,
            usage_details=normalized_usage,
            **kwargs,
        )
        return

    client.update_current_observation(
        input=input,
        output=output,
        model=model,
        model_parameters=model_parameters,
        usage_details=usage_details,
        **kwargs,
    )


def get_langfuse_status() -> dict[str, Any]:
    r"""Get detailed Langfuse configuration status for debugging.

    Returns:
        Dict[str, Any]: Status information including configuration state.
    """
    env_enabled_str = os.environ.get('LANGFUSE_ENABLED')
    env_enabled = (
        env_enabled_str.lower() == 'true' if env_enabled_str else None
    )

    return {
        'configured': _langfuse_configured,
        'has_public_key': bool(os.environ.get('LANGFUSE_PUBLIC_KEY')),
        'has_secret_key': bool(os.environ.get('LANGFUSE_SECRET_KEY')),
        'env_enabled': env_enabled,
        'host': (
            os.environ.get('LANGFUSE_BASE_URL')
            or os.environ.get('LANGFUSE_HOST')
            or 'https://cloud.langfuse.com'
        ),
        'debug': os.environ.get('LANGFUSE_DEBUG', 'false').lower() == 'true',
        'current_session_id': get_current_agent_session_id(),
        'client_available': _get_langfuse_client() is not None,
        'sdk_api': 'v3' if _is_langfuse_v3() else 'v2',
    }


def observe(*decorator_args: Any, **decorator_kwargs: Any) -> Any:
    r"""Lazily apply the installed Langfuse observe decorator.

    Model modules import this function before applications usually call
    :func:`configure_langfuse`. Delaying native decoration until the first
    configured call avoids permanently replacing tracing with a no-op.
    """

    def decorate(func: Callable[..., Any]) -> Callable[..., Any]:
        observed_func: Callable[..., Any] | None = None

        def resolve() -> Callable[..., Any]:
            nonlocal observed_func
            if not is_langfuse_available():
                return func
            if observed_func is None:
                sdk_observe = _get_langfuse_observe()
                if sdk_observe is None:
                    return func
                observed_func = sdk_observe(
                    *decorator_args, **decorator_kwargs
                )(func)
            return observed_func

        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                return await resolve()(*args, **kwargs)

            return async_wrapper

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return resolve()(*args, **kwargs)

        return wrapper

    if (
        len(decorator_args) == 1
        and callable(decorator_args[0])
        and not decorator_kwargs
    ):
        func = decorator_args[0]
        decorator_args = ()
        return decorate(func)

    return decorate
