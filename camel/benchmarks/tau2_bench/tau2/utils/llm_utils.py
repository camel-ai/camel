from __future__ import annotations

from typing import Any

from loguru import logger

from tau2.data_model.message import AssistantMessage, UserMessage


def _stub_warning() -> None:
    logger.error(
        "tau2.utils.llm_utils.generate is disabled in the CAMEL integration. "
        "Use camel.benchmarks.tau2_bench.adapters with ChatAgent instead of "
        "tau2's built-in LiteLLM wrappers."
    )


def generate(*args: Any, **kwargs: Any) -> UserMessage | AssistantMessage:
    """Placeholder that blocks accidental LiteLLM usage."""
    _stub_warning()
    raise RuntimeError(
        "LiteLLM has been removed from the vendored τ² benchmark. "
        "Please run through CAMEL's ChatAgent adapters."
    )
