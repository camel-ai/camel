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

from typing import Any, List, Dict
import torch
# Compatible with openai sampling parameters
from vllm import SamplingParams
from transformers import GenerationConfig

def chat_completion_vllm(
    model: Any,
    tokenizer: Any,
    messages: List[Dict[str, str]],
    vllm_params: SamplingParams
):
    formatted_messages = [tokenizer.apply_chat_template(
        messages, tokenize=False)]
    output = model.generate(formatted_messages, vllm_params)
    return output

@torch.inference_mode()
def chat_completion_hf(
    model: Any,
    tokenizer: Any,
    messages: List[Dict[str, str]],
    hf_params: Dict[str, Any]
):

    # tokenizer hosted in huggingface hub may not have chat_template configed
    if tokenizer.chat_template is not None:
        input_ids = tokenizer.apply_chat_template(
            messages, return_tensors="pt").to("cuda")
    else:
        raise AttributeError(
            "Chat template not found in tokenizer, please provide a template")

    prefix_length = input_ids.shape[-1]
    out_ids = model.generate(input_ids=input_ids,
                             **hf_params)

    decoded = tokenizer.batch_decode(out_ids[:, prefix_length:],
                                     skip_special_tokens=True)
    print(hf_params, flush=True)
    print(out_ids.shape, flush=True)
    return decoded

def extract_vllm_param(request) -> SamplingParams:
    """
    Extract VLLM model loading parameters from request body
    ref: https://github.com/vllm-project/vllm/blob/main/vllm/sampling_params.py
    """
    # request = request.deepcopy()
    kwargs = dict()
    vllm_params = (
        "n",
        "best_of",
        "presence_penalty",
        "frequency_penalty",
        "repetition_penalty",
        "temperature",
        "top_p",
        "top_k",
        "min_p",
        "seed",
        "use_beam_search",
        "length_penalty",
        "early_stopping",
        "stop",
        "stop_token_ids",
        "include_stop_str_in_output",
        "ignore_eos",
        "max_tokens",
        "logprobs",
        "prompt_logprobs",
        "skip_special_tokens",
        "spaces_between_special_tokens",
        "logits_processors",         
    )
    for param in vllm_params:
        if param in request:
            kwargs[param] = request[param]

    return SamplingParams(**kwargs)

def extract_hf_param(model_repo_name, request) -> Dict[str, Any]:
    """
    Extract parameters in user requests to huggingface GenerateConfig
    Some unmatched paramters will be translated
    e.g. n (Openai/vllm) -> num_return_sequences (Huggingface)

    ref: https://huggingface.co/docs/transformers/en/main_classes/text_generation
    For unassigned parameters, use model default
    """

    kwargs = dict()
    hf_params = (
    # NOTE: Parameters that control the length of the output
        "max_new_tokens",
        "min_length",
        "min_new_tokens",
        "early_stopping",
        "max_time",

    # NOTE: Parameters that control the generation strategy used
        "do_sample",
        "num_beams" 
        "num_beam_groups"
        "penalty_alpha"
        "use_cache"

    # NOTE: Parameters for manipulation of the model output logits
        "temperature",
        "top_k",
        "top_p",
        "typical_p",
        "epsilon_cutoff",
        "eta_cutoff",
        "diversity_penalty",
        "repetition_penalty",
        "encoder_repetition_penalty",
        "length_penalty",
        "no_repeat_ngram_size",
        "bad_words_ids",
        "force_words_ids",
        "renormalize_logits",
        "constraints",
        "forced_bos_token_id",
        "forced_eos_token_id",
        "remove_invalid_values",
        "exponential_decay_length_penalty",
        "supress_tokens",
        "begin_supress_tokens",
        "force_decoder_ids",
        "sequence_bias",
        "guidance_scale",
        "low_memory",

    # NOTE: Parameters that define the output variables of `generate`
        "num_return_sequences",
        "output_attentions",
        "output_hidden_states",
        "output_scores",
        "output_logits",
        "return_dict_in_generate",

    # NOTE: Special tokens that can be used at generation time
        "pad_token_id",
        "bos_token_id",
        "eos_token_id",

    # NOTE: Generation parameters exclusive to encoder-decoder models
        "encoder_no_repeat_ngram_size",
        "decoder_start_token_id",

    # NOTE: Generation parameters exclusive to [assistant generatio
        "num_assistant_tokens",
        "num_assistant_tokens_schedule",

    # NOTE: Parameters specific to the caching mechanism
        "cache_implementation",
    )
    params_map = {
        "max_new_tokens": "max_tokens", 
        "num_return_sequences": "n",
    }

    for param in hf_params:
        openai_param = params_map.get(param, param)
        if openai_param in request:
            kwargs[param] = request[openai_param]
    config = GenerationConfig.from_pretrained(model_repo_name)
    config.update(**kwargs)
    return config.to_dict()