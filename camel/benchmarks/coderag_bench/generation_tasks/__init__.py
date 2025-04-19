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

from . import humaneval

GENERATION_TASK_REGISTRY = {
    "humaneval": humaneval.HumanEvalGenerationWrapper,
    # "mbpp": mbpp.MBPPGenerationWrapper,  # future
}

def get_generation_task_wrapper(task_name):
    if task_name not in GENERATION_TASK_REGISTRY:
        raise ValueError(f"Unknown task: {task_name}")
    return GENERATION_TASK_REGISTRY[task_name]