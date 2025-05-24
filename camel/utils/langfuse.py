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

import logging
import os
from typing import Any, Callable, Dict, Optional

# Langfuse configuration singleton
_langfuse_configured = False


def configure_langfuse(
    public_key: Optional[str] = None,
    secret_key: Optional[str] = None,
    host: Optional[str] = None,
    debug: Optional[bool] = None,
    enabled: Optional[bool] = None,
) -> bool:
    r"""Configure Langfuse for CAMEL models.

    Args:
        public_key: Langfuse public key. Can be set via LANGFUSE_PUBLIC_KEY.
        secret_key: Langfuse secret key. Can be set via LANGFUSE_SECRET_KEY.
        host: Langfuse host URL. Can be set via LANGFUSE_HOST.
        debug: Enable debug mode. Can be set via LANGFUSE_DEBUG.
        enabled: Enable/disable Langfuse tracing.

    Returns:
        bool: True if Langfuse was successfully configured, False otherwise.

    Note:
        Langfuse tracing is disabled by default. You must explicitly set
        LANGFUSE_ENABLED=true or enabled=True to enable tracing.
    """
    global _langfuse_configured

    logger = logging.getLogger("camel.models")

    if _langfuse_configured:
        logger.debug("Langfuse already configured")
        return True

    try:
        logger.debug("Attempting to import langfuse.decorators")
        from langfuse.decorators import langfuse_context

        # Get configuration from environment or parameters
        public_key = public_key or os.environ.get("LANGFUSE_PUBLIC_KEY")
        secret_key = secret_key or os.environ.get("LANGFUSE_SECRET_KEY")
        host = host or os.environ.get(
            "LANGFUSE_HOST", "https://us.cloud.langfuse.com"
        )
        debug = (
            debug
            if debug is not None
            else os.environ.get("LANGFUSE_DEBUG", "False").lower() == "true"
        )

        logger.debug(
            f"Configuration values - public_key: "
            f"{'***' + public_key[-4:] if public_key else None}, "
            f"secret_key: {'***' + secret_key[-4:] if secret_key else None}, "
            f"host: {host}, debug: {debug}, enabled: {enabled}"
        )

        # Check if explicitly enabled/disabled via environment variable
        env_enabled_str = os.environ.get("LANGFUSE_ENABLED")
        env_enabled: Optional[bool] = None
        if env_enabled_str is not None:
            env_enabled = env_enabled_str.lower() == "true"

        logger.debug(f"Environment enabled setting: {env_enabled}")

        # Determine final enabled state
        if enabled is not None:
            # Parameter takes precedence
            final_enabled = enabled
            logger.debug(f"Using parameter enabled: {final_enabled}")
        elif env_enabled is not None:
            # Environment variable takes precedence
            final_enabled = env_enabled
            logger.debug(f"Using environment enabled: {final_enabled}")
        else:
            final_enabled = False
            logger.debug("No explicit setting, defaulting to disabled")

        # If explicitly disabled, don't configure even if keys are present
        if not final_enabled:
            logger.debug(
                "Langfuse tracing disabled - explicit setting required"
            )
            return False

        # Check if keys are available when enabled
        if not public_key or not secret_key:
            logger.debug("Langfuse enabled but keys not found")
            return False

        logger.debug("Attempting to configure langfuse_context")

        # Try to configure Langfuse
        langfuse_context.configure(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
            debug=debug,
            enabled=final_enabled,
        )

        logger.debug("langfuse_context.configure() completed successfully")

        _langfuse_configured = True
        logger.info("Langfuse configured successfully for CAMEL models")
        return True

    except ImportError as e:
        logger.debug(f"Langfuse not installed: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to configure Langfuse: {e}")
        logger.debug(f"Exception details: {type(e).__name__}: {e}")
        import traceback

        logger.debug(f"Traceback: {traceback.format_exc()}")
        return False


def is_langfuse_available() -> bool:
    r"""Check if Langfuse is installed and configured."""
    global _langfuse_configured

    try:
        from langfuse.decorators import langfuse_context

        # First check our global variable
        if not _langfuse_configured:
            return False

        try:
            langfuse_context.get_current_trace()
            return True
        except Exception:
            try:
                client = getattr(langfuse_context, "_client", None) or getattr(
                    langfuse_context, "client", None
                )
                return client is not None
            except Exception:
                return _langfuse_configured

    except ImportError:
        return False
    except Exception:
        return _langfuse_configured


def get_langfuse_context():
    r"""Get the Langfuse context if available."""
    try:
        from langfuse.decorators import langfuse_context

        if is_langfuse_available():
            return langfuse_context
        return None
    except ImportError:
        return None


def conditional_observe(as_type: Optional[str] = None, **kwargs):
    r"""Conditional decorator that only applies Langfuse observe if
        available and configured.

    Args:
        as_type: The observation type (e.g., "generation")
        **kwargs: Additional arguments for the observe decorator

    Returns:
        Decorator function that either applies Langfuse observe or returns
        the original function.
    """

    def decorator(func: Callable) -> Callable:
        if is_langfuse_available():
            try:
                from langfuse.decorators import observe

                return observe(as_type=as_type, **kwargs)(func)
            except ImportError:
                pass

        return func

    return decorator


def update_langfuse_observation(func_wrapper):
    r"""Helper function to update Langfuse observation with model details."""

    def update_observation(model, messages, tools=None):
        if is_langfuse_available():
            try:
                from langfuse.decorators import langfuse_context

                langfuse_context.update_current_observation(
                    model=str(model.model_type),
                    model_parameters=model.model_config_dict,
                    input={"messages": messages, "tools": tools},
                )
            except Exception as e:
                logging.getLogger("camel.models").debug(
                    f"Failed to update Langfuse observation: {e}"
                )

    return update_observation


def update_langfuse_output(result):
    r"""Helper function to update Langfuse observation with output."""
    if is_langfuse_available():
        try:
            from langfuse.decorators import langfuse_context

            if hasattr(result, 'choices') and result.choices:
                langfuse_context.update_current_observation(
                    output=result.choices[0].message.content
                    if result.choices[0].message
                    else None
                )
        except Exception as e:
            logging.getLogger("camel.models").debug(
                f"Failed to update Langfuse output: {e}"
            )


def get_langfuse_status() -> Dict[str, Any]:
    r"""Get detailed Langfuse configuration status for debugging.

    Returns:
        Dict[str, Any]: Status information including configuration state and
        reasons.
    """
    global _langfuse_configured

    has_keys = bool(
        os.environ.get("LANGFUSE_PUBLIC_KEY")
        and os.environ.get("LANGFUSE_SECRET_KEY")
    )
    env_enabled_str = os.environ.get("LANGFUSE_ENABLED")
    env_enabled: Optional[bool] = None
    if env_enabled_str is not None:
        env_enabled = env_enabled_str.lower() == "true"
    explicitly_enabled = env_enabled if env_enabled is not None else None

    should_be_configured = has_keys and explicitly_enabled is True

    actual_configured = _langfuse_configured and should_be_configured

    status: Dict[str, Any] = {
        "configured": actual_configured,
        "global_var_configured": _langfuse_configured,  # For debugging
        "should_be_configured": should_be_configured,  # For debugging
        "has_public_key": bool(os.environ.get("LANGFUSE_PUBLIC_KEY")),
        "has_secret_key": bool(os.environ.get("LANGFUSE_SECRET_KEY")),
        "explicitly_enabled": explicitly_enabled,
        "host": os.environ.get(
            "LANGFUSE_HOST", "https://us.cloud.langfuse.com"
        ),
        "debug": os.environ.get("LANGFUSE_DEBUG", "false").lower() == "true",
    }

    if _langfuse_configured:
        try:
            from langfuse.decorators import langfuse_context

            context_checks = {}

            for attr in ['_client', 'client', '_langfuse', 'langfuse']:
                context_checks[f"has_{attr}"] = hasattr(langfuse_context, attr)
                if hasattr(langfuse_context, attr):
                    obj = getattr(langfuse_context, attr)
                    context_checks[f"{attr}_is_none"] = obj is None

            status["context_debug"] = context_checks

        except Exception as e:
            status["context_error"] = str(e)

    return status
