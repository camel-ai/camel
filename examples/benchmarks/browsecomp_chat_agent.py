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

    # Create a benchmark instance with output file "report.html"
    # it samples 2 examples and uses 2 parallel processes for efficiency
    # set num_example=None in case of running full benchmark.
    benchmark = BrowseCompBenchmark("report.html", num_examples=2, processes=2)

    # This will process each example in parallel using separate agents
    # Pass the agent configuration instead of the agent itself
    benchmark.run(pipeline_template=grader_agent)

    # Validate the results using the configured model
    # This will generate a report.html file with the evaluation results
    # The output AGGRECATION METRICS are rates:
    # {'is_correct': 0.0, 'is_incorrect': 1.0} means is_incorrect=100%
    benchmark.validate(grader=grader_agent)
