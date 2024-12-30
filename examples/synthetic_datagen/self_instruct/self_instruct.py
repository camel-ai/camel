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
from camel.datagen.self_instruct import SelfInstructPipeline

agent = ChatAgent()

pipeline = SelfInstructPipeline(
    agent=agent,
    seed='seed_tasks.jsonl',
    num_machine_instructions=5,
    data_output_path='./data_output.json',
    human_to_machine_ratio=(6, 2),
)

pipeline.generate()
