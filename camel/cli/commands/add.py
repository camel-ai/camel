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

import click

# NOTE: Huggingface does not provide an easy way to download only necessary
# files like their `from_pretrained()` methods. The whole procedure during
# "from_pretrained" is too complicate and spread across several functions &
# files. I only keep the core.
# See transformers.modeling_utils.PreTrainedModel.from_pretrained

# TODO: Not 100% sure in offline mode


@click.command()
@click.argument("repo_id", type=str)
def add(repo_id):
    """
    Download a pre-trained model from Hugging Face model hub
    """
    # lazy import to avoid lag when --help flag is used
    from camel.utils.third_party.huggingface_utils import (
        hf_download_config,
        hf_download_generation_config,
        hf_download_model,
        hf_download_tokenizer,
        hf_download_tokenizer_config,
    )
    hf_download_config(repo_id)
    hf_download_model(repo_id)
    hf_download_generation_config(repo_id)
    hf_download_tokenizer(repo_id)
    hf_download_tokenizer_config(repo_id)
