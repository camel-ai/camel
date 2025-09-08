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

from camel.agents import ChatAgent
from camel.benchmarks import APIBenchBenchmark

# Set up the agent to be benchmarked
agent = ChatAgent()

# Set up the APIBench Benchmark
benchmark = APIBenchBenchmark(
    data_dir="APIBenchDatasets", save_to="APIBenchResults.jsonl"
)

# Download the benchmark data
benchmark.download()

# Set the subset to be benchmarked
subset_name = 'torchhub'

# Run the benchmark
result = benchmark.run(agent, subset_name, subset=10)

# Please note that APIBench does not use 'real function call'
# but instead includes API documentation in the questions
# for the agent to reference.
# An example question including the API documentation is printed below.
print(
    "\nExample question including API documentation:\n",
    benchmark._data['questions'][0]['text'],
)
'''
===============================================================================
Example question including API documentation:
  What is an API that can be used to classify sports activities in videos?\n
 Use this API documentation for reference:  
 {"domain": "Video Classification", "framework": "PyTorch", 
 "functionality": "3D ResNet", "api_name": "slow_r50", 
 "api_call": "torch.hub.load(repo_or_dir='facebookresearch/pytorchvideo', 
 model='slow_r50', pretrained=True)", "api_arguments": {"pretrained": "True"}, 
 "python_environment_requirements": ["torch", "json", "urllib", 
 "pytorchvideo", 
 "torchvision", "torchaudio", "torchtext", "torcharrow", "TorchData", 
 "TorchRec", "TorchServe", "PyTorch on XLA Devices"], 
 "example_code": ["import torch", 
 "model = torch.hub.load('facebookresearch/pytorchvideo', 
 'slow_r50', pretrained=True)", 
 "device = 'cpu'", "model = model.eval()", "model = model.to(device)"], 
 "performance": {"dataset": "Kinetics 400", 
 "accuracy": {"top_1": 74.58, "top_5": 91.63}, 
 "Flops (G)": 54.52, "Params (M)": 32.45}, 
 "description": "The 3D ResNet model is a Resnet-style video classification 
 network pretrained on the Kinetics 400 dataset. It is based on the 
 architecture from the paper 'SlowFast Networks for Video Recognition' 
 by Christoph Feichtenhofer et al."}}
===============================================================================
'''

print("Total:", result["total"])
print("Correct:", result["correct"])
print("Hallucination:", result["hallucination"])
'''
===============================================================================
Total: 10
Correct: 10
Hallucination: 0
===============================================================================
'''
