#!/usr/bin/env python3
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
"""Check for deprecated models by comparing ModelType enum against provider
APIs.

This script uses the camel framework's list_available_models() classmethod
on each model backend to query provider list-models endpoints, and compares
with the ModelType enum in camel/types/enums.py, producing a Markdown report.

Usage:
    python profiling/check_deprecated_models.py
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass
class ProviderConfig:
    name: str
    backend_class_path: str  # e.g. "camel.models.OpenAIModel"
    modeltype_predicate: str
    env_key: Optional[str] = None
    auth_required: bool = True
    base_url_env_key: Optional[str] = None
    default_base_url: Optional[str] = None


@dataclass
class ProviderResult:
    name: str
    enum_models: set
    api_models: Optional[set] = None
    skipped: bool = False
    skip_reason: str = ""
    possibly_deprecated: set = field(default_factory=set)
    new_in_api: set = field(default_factory=set)


# ---------------------------------------------------------------------------
# Provider configurations
# ---------------------------------------------------------------------------
def _infer_default_env_key(provider_name: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", provider_name).upper()
    return f"{normalized}_API_KEY"


def _get_env_key(config: ProviderConfig) -> str:
    return config.env_key or _infer_default_env_key(config.name)


PROVIDERS: list[ProviderConfig] = [
    ProviderConfig(
        name="OpenAI",
        backend_class_path="camel.models.OpenAIModel",
        modeltype_predicate="is_openai",
    ),
    ProviderConfig(
        name="Anthropic",
        backend_class_path="camel.models.AnthropicModel",
        modeltype_predicate="is_anthropic",
    ),
    ProviderConfig(
        name="Gemini",
        backend_class_path="camel.models.GeminiModel",
        modeltype_predicate="is_gemini",
    ),
    ProviderConfig(
        name="Mistral",
        backend_class_path="camel.models.MistralModel",
        modeltype_predicate="is_mistral",
    ),
    ProviderConfig(
        name="Groq",
        backend_class_path="camel.models.GroqModel",
        modeltype_predicate="is_groq",
    ),
    ProviderConfig(
        name="Cohere",
        backend_class_path="camel.models.CohereModel",
        modeltype_predicate="is_cohere",
    ),
    ProviderConfig(
        name="Together AI",
        env_key="TOGETHER_API_KEY",
        modeltype_predicate="is_together",
        backend_class_path="camel.models.TogetherAIModel",
    ),
    ProviderConfig(
        name="SiliconFlow",
        backend_class_path="camel.models.SiliconFlowModel",
        modeltype_predicate="is_siliconflow",
    ),
    ProviderConfig(
        name="OpenRouter",
        backend_class_path="camel.models.OpenRouterModel",
        modeltype_predicate="is_openrouter",
        auth_required=False,
    ),
    ProviderConfig(
        name="Novita",
        backend_class_path="camel.models.NovitaModel",
        modeltype_predicate="is_novita",
    ),
    ProviderConfig(
        name="DeepSeek",
        backend_class_path="camel.models.DeepSeekModel",
        modeltype_predicate="is_deepseek",
    ),
    ProviderConfig(
        name="Cerebras",
        backend_class_path="camel.models.CerebrasModel",
        modeltype_predicate="is_cerebras",
    ),
    ProviderConfig(
        name="Nebius",
        backend_class_path="camel.models.NebiusModel",
        modeltype_predicate="is_nebius",
    ),
    ProviderConfig(
        name="CometAPI",
        env_key="COMETAPI_KEY",
        backend_class_path="camel.models.CometAPIModel",
        modeltype_predicate="is_cometapi",
    ),
    ProviderConfig(
        name="PPIO",
        backend_class_path="camel.models.PPIOModel",
        modeltype_predicate="is_ppio",
    ),
    ProviderConfig(
        name="SambaNova",
        env_key="SAMBA_API_KEY",
        backend_class_path="camel.models.SambaModel",
        modeltype_predicate="is_sambanova",
    ),
    ProviderConfig(
        name="Reka",
        backend_class_path="camel.models.RekaModel",
        modeltype_predicate="is_reka",
    ),
    ProviderConfig(
        name="ZhipuAI",
        backend_class_path="camel.models.ZhipuAIModel",
        modeltype_predicate="is_zhipuai",
    ),
    ProviderConfig(
        name="Netmind",
        backend_class_path="camel.models.NetmindModel",
        modeltype_predicate="is_netmind",
    ),
    ProviderConfig(
        name="Nvidia",
        backend_class_path="camel.models.NvidiaModel",
        modeltype_predicate="is_nvidia",
        base_url_env_key="NVIDIA_API_BASE_URL",
        default_base_url="https://integrate.api.nvidia.com/v1",
    ),
    ProviderConfig(
        name="Qwen",
        backend_class_path="camel.models.QwenModel",
        modeltype_predicate="is_qwen",
        base_url_env_key="QWEN_API_BASE_URL",
        default_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    ),
    ProviderConfig(
        name="Yi",
        backend_class_path="camel.models.YiModel",
        modeltype_predicate="is_yi",
    ),
    ProviderConfig(
        name="InternLM",
        backend_class_path="camel.models.InternLMModel",
        modeltype_predicate="is_internlm",
    ),
    ProviderConfig(
        name="Moonshot",
        backend_class_path="camel.models.MoonshotModel",
        modeltype_predicate="is_moonshot",
    ),
    ProviderConfig(
        name="AIML",
        backend_class_path="camel.models.AIMLModel",
        modeltype_predicate="is_aiml",
    ),
    ProviderConfig(
        name="ModelScope",
        env_key="MODELSCOPE_SDK_TOKEN",
        backend_class_path="camel.models.ModelScopeModel",
        modeltype_predicate="is_modelscope",
        base_url_env_key="MODELSCOPE_API_BASE_URL",
        default_base_url="https://api-inference.modelscope.cn/v1/",
    ),
    ProviderConfig(
        name="WatsonX",
        backend_class_path="camel.models.WatsonXModel",
        modeltype_predicate="is_watsonx",
    ),
    ProviderConfig(
        name="Qianfan",
        backend_class_path="camel.models.QianfanModel",
        modeltype_predicate="is_qianfan",
        base_url_env_key="QIANFAN_API_BASE_URL",
        default_base_url="https://qianfan.baidubce.com/v2",
    ),
    ProviderConfig(
        name="Crynux",
        backend_class_path="camel.models.CrynuxModel",
        modeltype_predicate="is_crynux",
    ),
    ProviderConfig(
        name="Minimax",
        backend_class_path="camel.models.MinimaxModel",
        modeltype_predicate="is_minimax",
    ),
    ProviderConfig(
        name="Avian",
        backend_class_path="camel.models.AvianModel",
        modeltype_predicate="is_avian",
    ),
    ProviderConfig(
        name="AtlasCloud",
        backend_class_path="camel.models.AtlasCloudModel",
        modeltype_predicate="is_atlascloud",
        base_url_env_key="ATLASCLOUD_API_BASE_URL",
        default_base_url="https://api.atlascloud.ai/v1",
    ),
]


# ---------------------------------------------------------------------------
# Enum parser
# ---------------------------------------------------------------------------
def parse_enum_models() -> dict[str, set[str]]:
    r"""Group ModelType values by provider using ModelType.is_xxx."""
    from camel.types import ModelType

    provider_models: dict[str, set[str]] = {
        cfg.name: set() for cfg in PROVIDERS
    }
    predicate_by_provider = {
        cfg.name: cfg.modeltype_predicate for cfg in PROVIDERS
    }

    for model_type in ModelType:
        if model_type in {ModelType.DEFAULT, ModelType.STUB}:
            continue
        for provider_name, predicate in predicate_by_provider.items():
            if getattr(model_type, predicate):
                provider_models[provider_name].add(model_type.value)

    return provider_models


# ---------------------------------------------------------------------------
# Model fetcher using framework API
# ---------------------------------------------------------------------------
def _import_backend_class(class_path: str):
    """Dynamically import a model backend class from its dotted path."""
    module_path, class_name = class_path.rsplit(".", 1)
    import importlib

    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def fetch_models(config: ProviderConfig) -> Optional[set[str]]:
    """Fetch available model IDs from a provider using the framework API.

    Returns a set of model ID strings, or None on any error.
    """
    try:
        backend_cls = _import_backend_class(config.backend_class_path)
        env_key = _get_env_key(config)
        api_key = os.environ.get(env_key) or None
        url = (
            os.environ.get(config.base_url_env_key, config.default_base_url)
            if config.base_url_env_key
            else None
        )
        model_ids = backend_cls.list_available_models(
            api_key=api_key,
            url=url,
        )
        return set(model_ids)
    except Exception as e:
        print(f"  [{config.name}] API error: {e}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------
def compare_models(
    enum_models: set[str],
    api_models: set[str],
) -> tuple[set[str], set[str]]:
    """Return (possibly_deprecated, new_in_api)."""
    possibly_deprecated = enum_models - api_models
    new_in_api = api_models - enum_models
    return possibly_deprecated, new_in_api


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------
def _append_model_section(
    lines: list[str],
    title: str,
    results: list[ProviderResult],
    getter,
) -> None:
    matching = [r for r in results if getter(r)]
    if not matching:
        return
    lines.extend(["", title, ""])
    for result in matching:
        lines.append(f"### {result.name}")
        lines.append("")
        for model in sorted(getter(result)):
            lines.append(f"- `{model}`")
        lines.append("")


def generate_report(results: list[ProviderResult]) -> str:
    """Generate a Markdown report from provider results."""
    lines: list[str] = []
    lines.append("# Deprecated Models Check Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(
        "| Provider | Enum Count | API Count | "
        "Possibly Deprecated | New in API |"
    )
    lines.append(
        "|----------|-----------|-----------|--------------------:|----------:|"
    )

    for r in results:
        if r.skipped:
            lines.append(f"| {r.name} | {len(r.enum_models)} | - | - | - |")
        else:
            api_count = len(r.api_models) if r.api_models else 0
            lines.append(
                f"| {r.name} | {len(r.enum_models)} | {api_count}"
                f" | {len(r.possibly_deprecated)}"
                f" | {len(r.new_in_api)} |"
            )

    _append_model_section(
        lines,
        "## Possibly Deprecated Models",
        results,
        lambda r: r.possibly_deprecated,
    )

    # Skipped providers section
    skipped = [r for r in results if r.skipped]
    if skipped:
        lines.append("")
        lines.append("## Skipped Providers")
        lines.append("")
        for r in skipped:
            lines.append(f"- **{r.name}**: {r.skip_reason}")
        lines.append("")

    _append_model_section(
        lines,
        "## New Models in API (not in enum)",
        results,
        lambda r: r.new_in_api,
    )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def _skipped_result(
    name: str,
    enum_models: set[str],
    reason: str,
) -> ProviderResult:
    return ProviderResult(
        name=name,
        enum_models=enum_models,
        skipped=True,
        skip_reason=reason,
    )


def evaluate_provider(
    config: ProviderConfig,
    enum_models: set[str],
) -> ProviderResult:
    env_key = _get_env_key(config)
    api_key = os.environ.get(env_key, "")
    if config.auth_required and not api_key:
        return _skipped_result(
            config.name,
            enum_models,
            f"Missing env var `{env_key}`",
        )

    api_models = fetch_models(config)
    if api_models is None:
        return _skipped_result(
            config.name,
            enum_models,
            "API request failed (see stderr)",
        )

    deprecated, new = compare_models(enum_models, api_models)
    return ProviderResult(
        name=config.name,
        enum_models=enum_models,
        api_models=api_models,
        possibly_deprecated=deprecated,
        new_in_api=new,
    )


def main() -> None:
    print("Parsing ModelType enum...", file=sys.stderr)
    provider_models = parse_enum_models()

    results: list[ProviderResult] = []

    for config in PROVIDERS:
        enum_set = provider_models.get(config.name, set())
        print(
            f"Checking {config.name} ({len(enum_set)} enum models)...",
            file=sys.stderr,
        )
        results.append(evaluate_provider(config, enum_set))

    report = generate_report(results)

    # Write to stdout
    print(report)

    # Write to GITHUB_STEP_SUMMARY if available
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write(report)
            f.write("\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)
    sys.exit(0)
