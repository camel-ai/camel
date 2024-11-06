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

from typing import List, Optional

from pydantic import Field

from camel.configs.base_config import BaseConfig


class PHIConfig(BaseConfig):
    model: str = "microsoft/Phi-3.5-vision-instruct"
    trust_remote_code: bool = True
    max_model_len: int = 4096
    limit_mm_per_prompt: dict = Field(default_factory=lambda: {"image": 2})
    temperature: float = 0.0
    max_tokens: int = 128
    stop_token_ids: Optional[List[int]] = None
    method: str = "generate"
    question: str = ""

    class Config:
        arbitrary_types_allowed = True


PHI_API_PARAMS = {param for param in PHIConfig.model_fields.keys()}

"""
INFO 11-05 21:20:17 config.py:107] Replacing legacy 'type' key with 'rope_type'
WARNING 11-05 21:20:17 config.py:114] 
Replacing legacy rope_type 'su' with 'longrope'
INFO 11-05 21:20:20 llm_engine.py:237] 
Initializing an LLM engine (v0.6.3.post1) 
with config: model='microsoft/Phi-3.5-vision-instruct', 
speculative_config=None, 
tokenizer='microsoft/Phi-3.5-vision-instruct', skip_tokenizer_init=False, 
tokenizer_mode=auto, revision=None, 
override_neuron_config=None, rope_scaling=None, 
rope_theta=None, tokenizer_revision=None, trust_remote_code=True, 
dtype=torch.bfloat16, max_seq_len=4096, download_dir=None, 
load_format=LoadFormat.AUTO, tensor_parallel_size=1, pipeline_parallel_size=1, 
disable_custom_all_reduce=False, quantization=None, enforce_eager=False, 
kv_cache_dtype=auto, quantization_param_path=None, device_config=cuda, 
decoding_config=DecodingConfig(guided_decoding_backend='outlines'), 
observability_config=ObservabilityConfig(otlp_traces_endpoint=None, 
collect_model_forward_time=False, collect_model_execute_time=False), seed=0, 
served_model_name=microsoft/Phi-3.5-vision-instruct, num_scheduler_steps=1, 
chunked_prefill_enabled=False multi_step_stream_outputs=True, 
enable_prefix_caching=False, use_async_output_proc=True, 
use_cached_outputs=False, mm_processor_kwargs=None)
INFO 11-05 21:20:21 selector.py:247] 
Cannot use FlashAttention-2 backend due to sliding window.
INFO 11-05 21:20:21 model_runner.py:1056] 
Starting to load model microsoft/Phi-3.5-vision-instruct...
INFO 11-05 21:20:21 selector.py:247] 
Cannot use FlashAttention-2 backend due to sliding window.
INFO 11-05 21:20:21 selector.py:115] 
Using XFormers backend.
INFO 11-05 21:20:22 weight_utils.py:243] 
Using model weights format ['*.safetensors']

Loading safetensors checkpoint shards:   
0% Completed | 0/2 [00:00<?, ?it/s]

Loading safetensors checkpoint shards:  
50% Completed | 1/2 [00:00<00:00,  2.87it/s]

Loading safetensors checkpoint shards: 
100% Completed | 2/2 [00:00<00:00,  2.12it/s]

Loading safetensors checkpoint shards: 
100% Completed | 2/2 [00:00<00:00,  2.21it/s]

INFO 11-05 21:20:23 model_runner.py:1067] 
Loading model weights took 7.9324 GB

INFO 11-05 21:20:25 gpu_executor.py:122] 
# GPU blocks: 2153, # CPU blocks: 682
INFO 11-05 21:20:25 gpu_executor.py:126] 
Maximum concurrency for 4096 tokens per request: 8.41x
INFO 11-05 21:20:26 model_runner.py:1395] 
Capturing the model for CUDA graphs. 
This may lead to unexpected consequences if the model is not static. 
To run the model in eager mode, set 'enforce_eager=True' 
or use '--enforce-eager' in the CLI.
INFO 11-05 21:20:26 model_runner.py:1399] 
CUDA graphs can take additional 1~3 GiB memory per GPU. 
If you are running out of memory, 
consider decreasing `gpu_memory_utilization` or enforcing eager mode. 
You can also reduce the `max_num_seqs` as needed to decrease memory usage.
INFO 11-05 21:20:36 model_runner.py:1523] 
Graph capturing finished in 10 secs.
prompt_token_ids (old) 
[1, 32010, 29871, 13, 29966, 29989, 3027, 29918, 29896, 29989, 29958, 
13, 5816, 29915, 29879, 297, 278, 1967, 29973, 32007, 29871, 13, 32001]

Processed prompts:   0%|          | 0/1 
[00:00<?, ?it/s, est. speed input: 0.00 toks/s, output: 0.00 toks/s]
Processed prompts: 100%|██████████| 1/1 
[00:00<00:00,  1.37it/s, est. speed input: 
1062.35 toks/s, output: 57.72 toks/s]
Processed prompts: 100%|██████████| 1/1 
[00:00<00:00,  1.37it/s, est. speed input: 
1062.35 toks/s, output: 57.72 toks/s]
 The image shows a close-up of a young goat with a white and grey coat. 
 The goat has a playful expression with 
 its tongue sticking out and its ears perked up.
"""
