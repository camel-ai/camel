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

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from fastapi import HTTPException
from camel.types.server_types import HFModelLoadingParam
from camel.utils import PYDANTIC_V2
from vllm import LLM

def load_model(
    model: str,
    vllm: bool,
    hf_param: HFModelLoadingParam,
):
    """
    General entry of loading a model in CAMEL project
    """
    if vllm:
        llm, tokenizer = load_vllm_model(model)
    else:
        # device input check
        hf_param = hf_param.model_dump() if PYDANTIC_V2 else hf_param.dict() # type: ignore
        device = hf_param["device_map"]
        if isinstance(device, str):
            if device not in {"cuda", "cpu"}:
                raise ValueError(f"Invalid device {device}, expect one of 'cuda' and 'cpu'.")
        if isinstance(device, int):
            gpu_nums = get_gpu_nums()
            if device >= gpu_nums:
                raise ValueError(f"Invalid device number {device}, only have {tuple(range(gpu_nums))}.")

        llm, tokenizer = load_HF_model(model, hf_param)
    return llm, tokenizer

def load_HF_model(hf_model, configs):
    """
    Load a model from Hugging Face model hub
    """
    try:
        model = AutoModelForCausalLM.from_pretrained(
            hf_model,
            **configs
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    try:
        tokenizer = AutoTokenizer.from_pretrained(
            hf_model
            )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

    return model, tokenizer

def load_vllm_model(model: str):
    llm = LLM(model)
    tokenizer = llm.get_tokenizer()
    return llm, tokenizer

def get_gpu_nums() -> int:
    return torch.cuda.device_count()