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
from synthetic_datagen.agent_systems.single_agent import SingleAgent
from synthetic_datagen.method_factory import SyntheticDataGeneratorMethodType
from synthetic_datagen.pipeline import DataGeneratorPipeline
from synthetic_datagen.self_instruct.self_instruct_spec import SelfInstructSpec

spec = SelfInstructSpec()
spec.agent_system = SingleAgent()
generator = DataGeneratorPipeline(
    spec,
    method_type=SyntheticDataGeneratorMethodType.SELFINSTRUCT,
)
generator.run_generate()
generator.run_curate()
generator.run_evaluate()
