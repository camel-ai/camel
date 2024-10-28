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
from camel.agents import ChatAgent
from camel.configs import PHIConfig
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

# Example image URLs
IMAGE_URLS = [
    "https://upload.wikimedia.org/wikipedia/commons/d/da/2015_Kaczka_krzy%C5%BCowka_w_wodzie_%28samiec%29.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/7/77/002_The_lion_king_Snyggve_in_the_Serengeti_National_Park_Photo_by_Giles_Laurent.jpg",
]

# Create VLLMConfig
phi_config = PHIConfig(
    model="microsoft/Phi-3.5-vision-instruct",
    image_urls=IMAGE_URLS,
    question="What is the content of each image?",
)

# Create VLLMModel
phi_model = ModelFactory.create(
    model_platform=ModelPlatformType.PHI,
    model_type=ModelType.PHI_3_5_VISION,
    model_config_dict=phi_config.dict(),
)

# Define system message
sys_msg = BaseMessage.make_assistant_message(
    role_name="Assistant", content="You are a helpful assistant."
)

# Set agent
camel_agent = ChatAgent(system_message=sys_msg, model=phi_model)

user_msg = BaseMessage.make_user_message(
    role_name="User",
    content="""Say hi to CAMEL AI, one open-source community dedicated to the 
    study of autonomous and communicative agents.""",
)

# Get response information
response = camel_agent.step(user_msg)
print(response.msgs[0].content)

"""
===============================================================================
INFO 09-20 15:54:42 llm_engine.py:223] 
    Initializing an LLM engine (v0.6.1.post2) 
    with config: model='microsoft/Phi-3.5-vision-instruct', 
    speculative_config=None, tokenizer='microsoft/Phi-3.5-vision-instruct', 
    skip_tokenizer_init=False, tokenizer_mode=auto, revision=None, 
    override_neuron_config=None, rope_scaling=None, rope_theta=None, 
    tokenizer_revision=None, trust_remote_code=True, dtype=torch.bfloat16, 
    max_seq_len=4096, download_dir=None, load_format=LoadFormat.AUTO, 
    tensor_parallel_size=1, pipeline_parallel_size=1, 
    disable_custom_all_reduce=False, 
    quantization=None, enforce_eager=False, kv_cache_dtype=auto, 
    quantization_param_path=None, device_config=cuda, 
    decoding_config=DecodingConfig(guided_decoding_backend='outlines'), 
    observability_config=ObservabilityConfig(otlp_traces_endpoint=None, 
    collect_model_forward_time=False, collect_model_execute_time=False),
    seed=0, served_model_name=microsoft/Phi-3.5-vision-instruct, 
    use_v2_block_manager=False, num_scheduler_steps=1, 
    enable_prefix_caching=False, use_async_output_proc=True)
INFO 09-20 15:54:42 selector.py:240] 
    Cannot use FlashAttention-2 backend due to sliding window.
INFO 09-20 15:54:42 selector.py:116] Using XFormers backend.
    /home/mi/anaconda3/envs/camel/lib/python3.10/site-packages/xformers/ops/fmha/flash.py:211: 
    FutureWarning: `torch.library.impl_abstract` 
    was renamed to `torch.library.register_fake`. 
    Please use that instead; we will remove 
    `torch.library.impl_abstract` in a future version of PyTorch.
    @torch.library.impl_abstract("xformers_flash::flash_fwd")
    /home/mi/anaconda3/envs/camel/lib/python3.10/site-packages/xformers/ops/fmha/flash.py:344: 
    FutureWarning: `torch.library.impl_abstract` 
    was renamed to `torch.library.register_fake`. 
    Please use that instead; we will remove 
    `torch.library.impl_abstract` in a future version of PyTorch.
    @torch.library.impl_abstract("xformers_flash::flash_bwd")
INFO 09-20 15:54:43 model_runner.py:997] 
    Starting to load model microsoft/Phi-3.5-vision-instruct...
INFO 09-20 15:54:43 selector.py:240] 
    Cannot use FlashAttention-2 backend due to sliding window.
INFO 09-20 15:54:43 selector.py:116] Using XFormers backend.
INFO 09-20 15:54:44 weight_utils.py:242] 
    Using model weights format ['*.safetensors']
Loading safetensors checkpoint shards:   0% Completed | 0/2 [00:00<?, ?it/s]
Loading safetensors checkpoint shards:  
                                50% Completed | 1/2 [00:00<00:00,  3.10it/s]
Loading safetensors checkpoint shards: 
                                100% Completed | 2/2 [00:00<00:00,  2.48it/s]
Loading safetensors checkpoint shards: 
                                100% Completed | 2/2 [00:00<00:00,  2.56it/s]

INFO 09-20 15:54:46 model_runner.py:1008] Loading model weights took 7.7498 GB
    /home/mi/anaconda3/envs/camel/lib/python3.10/site-packages/transformers/models/auto/image_processing_auto.py:513: 
    FutureWarning: The image_processor_class argument 
    is deprecated and will be removed in v4.42. 
    Please use `slow_image_processor_class`, 
    or `fast_image_processor_class` instead
    warnings.warn(
INFO 09-20 15:54:47 gpu_executor.py:122] # GPU blocks: 2197, # CPU blocks: 682
INFO 09-20 15:54:48 model_runner.py:1311] Capturing the model for CUDA graphs. 
    This may lead to unexpected consequences if the model is not static. 
    To run the model in eager mode, 
    set 'enforce_eager=True' or use '--enforce-eager' in the CLI.
INFO 09-20 15:54:48 model_runner.py:1315] 
    CUDA graphs can take additional 1~3 GiB memory per GPU. 
    If you are running out of memory, 
    consider decreasing `gpu_memory_utilization` or enforcing eager mode. 
    You can also reduce the `max_num_seqs` as needed to decrease memory usage.
INFO 09-20 15:54:57 model_runner.py:1430] Graph capturing finished in 9 secs.
    Processed prompts: 100%|██████████████████████████████████| 
    1/1 [00:01<00:00,  1.43s/it, est. 
    speed input: 1090.18 toks/s, output: 53.32 toks/s]
 

The first image shows a duck floating on water, 
with its reflection visible on the surface. 
The duck has a green head, yellow bill, 
and a brown body with white patches. 
The second image depicts a lion sitting in a grassy field. 
The lion has a golden mane and is looking directly at the camera.
===============================================================================
"""
