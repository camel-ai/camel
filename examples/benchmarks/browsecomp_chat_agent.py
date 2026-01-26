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

from camel.agents.chat_agent import ChatAgent
from camel.benchmarks.browsecomp import BrowseCompBenchmark
from camel.models.model_factory import ModelFactory
from camel.types.enums import ModelPlatformType, ModelType

if __name__ == '__main__':
    # Define model configuration
    model_config = {
        "model_platform": ModelPlatformType.DEFAULT,
        "model_type": ModelType.DEFAULT,
    }

    grader_agent = ChatAgent(
        "You are a helpful assistant.",
        model=ModelFactory.create(**model_config),
    )

    benchmark = BrowseCompBenchmark(processes=2)
    benchmark.load(num_examples=2)

    # This will process each example in parallel using separate agents
    # Pass the agent configuration instead of the agent itself
    benchmark.run(pipeline_template=grader_agent)
