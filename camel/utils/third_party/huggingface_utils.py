# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
from __future__ import annotations

from typing import Any, Dict, Optional

from huggingface_hub import HfApi
from transformers.models.auto.configuration_auto import (
    AutoConfig,
    config_class_to_model_type,
)
from transformers.models.auto.tokenization_auto import (
    TOKENIZER_MAPPING,
    get_tokenizer_config,
)
from transformers.tokenization_utils_base import (
    ADDED_TOKENS_FILE,
    FULL_TOKENIZER_FILE,
    SPECIAL_TOKENS_MAP_FILE,
    TOKENIZER_CONFIG_FILE,
)
from transformers.utils import (
    CONFIG_NAME,
    GENERATION_CONFIG_NAME,
    SAFE_WEIGHTS_INDEX_NAME,
    SAFE_WEIGHTS_NAME,
    WEIGHTS_INDEX_NAME,
    WEIGHTS_NAME,
    cached_file,
    extract_commit_hash,
)

from camel.termui import ui


def if_hf_repo_exists(repo_id: str):
    """
    Check if a huggingface repo exists
    """
    hf_api = HfApi()
    model_info = hf_api.model_info(repo_id)
    if model_info is None:
        return False
    else:
        return True


def hf_download_config(repo_id: str) -> None:
    """
    Download the config.json file of a pre-trained model from HuggingFace
    model hub
    """
    if not if_hf_repo_exists(repo_id):
        ui.error(f"Model {repo_id} not found in Hugging Face model hub")
        return
    try:
        cached_file(
            repo_id,
            CONFIG_NAME,
            _raise_exceptions_for_gated_repo=False,
            _raise_exceptions_for_missing_entries=False,
            _raise_exceptions_for_connection_errors=False,
        )
    except Exception:
        ui.error(f"Failed to download `config.json` for {repo_id}.")
        raise


def hf_fetch_commit_hash(repo_id) -> Optional[str]:
    """
    Fetch latest commit hash for of the repo from HuggingFace model hub
    """
    # HF always make a call to the config file first (which may be absent)
    # to get the commit hash as soon as possible
    if if_hf_repo_exists(repo_id):
        try:
            resolved_config_file = cached_file(
                repo_id,
                CONFIG_NAME,
            )
        except Exception:
            ui.error(f"Failed to download `config.json` for {repo_id}.")
            raise
        else:
            commit_hash = extract_commit_hash(resolved_config_file, repo_id)
            return commit_hash
    else:
        ui.error(f"Model {repo_id} not found in Hugging Face model hub")
    return None


def hf_download_model(repo_id: str, ) -> None:
    """
    Download a pre-trained model from HuggingFace model hub

    """
    if not if_hf_repo_exists(repo_id):
        ui.error(f"Model {repo_id} not found in Hugging Face model hub")
        return
    cached_file_kwargs: Dict[str, Any] = {
        "_raise_exceptions_for_gated_repo": False,
        "_raise_exceptions_for_missing_entries": False,
    }
    file_type_list = (SAFE_WEIGHTS_NAME, SAFE_WEIGHTS_INDEX_NAME, WEIGHTS_NAME,
                      WEIGHTS_INDEX_NAME)
    for file_type in file_type_list:
        resolved_archive_file = cached_file(
            repo_id,
            file_type,
            **cached_file_kwargs,
        )
        if resolved_archive_file is not None:
            break
    if resolved_archive_file is None:
        ui.error(f"Failed to download model {repo_id}."
                 f"No valid `.bin` or `.safetensors` file found on"
                 f"https://huggingface.co/{repo_id}")


def hf_download_generation_config(repo_id: str, ) -> None:
    """
    Download the generation_config.json file of a pre-trained model from
    HuggingFace model hub
    """
    try:
        cached_file(
            repo_id,
            GENERATION_CONFIG_NAME,
        )
    except Exception:
        ui.error(f"Failed to download generation_config.json for {repo_id}."
                 f"No valid `generation_config.json` file found on"
                 f"https://huggingface.co/{repo_id}")
        raise


def hf_download_tokenizer(
    repo_id: str,
    commit_hash: Optional[str] = None,
) -> None:
    tokenizer_config = get_tokenizer_config(repo_id, commit_hash=commit_hash)
    config_tokenizer_class = tokenizer_config.get("tokenizer_class")
    # specify model type and corresponding tokenizer files
    if config_tokenizer_class is None:
        config = AutoConfig.from_pretrained(repo_id)
        config_tokenizer_class = config.tokenizer_class

    additional_files_names = {
        "added_tokens_file": ADDED_TOKENS_FILE,  # kept only for legacy
        "special_tokens_map_file":
        SPECIAL_TOKENS_MAP_FILE,  # kept only for legacy
        "tokenizer_config_file": TOKENIZER_CONFIG_FILE,
        # tokenizer_file used to initialize a slow from a fast.
        # Properly copy the `addedTokens` instead of adding in random orders
        "tokenizer_file": FULL_TOKENIZER_FILE,
    }
    model_type = config_class_to_model_type(type(config).__name__)
    if model_type is not None:
        tokenizer_class_py, tokenizer_class_fast = TOKENIZER_MAPPING[type(
            config)]

    for tokenizer in (tokenizer_class_fast, tokenizer_class_py):
        if tokenizer is not None:
            vocab_files = {
                **tokenizer.vocab_files_names,
                **additional_files_names
            }
            for _, file_name in vocab_files.items():
                cached_file(
                    repo_id,
                    file_name,
                    commit_hash=commit_hash,
                    _raise_exceptions_for_gated_repo=False,
                    _raise_exceptions_for_missing_entries=False,
                    _raise_exceptions_for_connection_errors=False,
                )


def hf_download_tokenizer_config(repo_id: str) -> None:
    cached_file(
        repo_id,
        TOKENIZER_CONFIG_FILE,
        _raise_exceptions_for_gated_repo=False,
        _raise_exceptions_for_missing_entries=False,
        _raise_exceptions_for_connection_errors=False,
    )
