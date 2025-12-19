# flake8: noqa
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
from camel.benchmarks.tbench import TBench
from camel.logger import get_logger
from camel.messages.base import BaseMessage
from camel.models import BaseModelBackend, ModelFactory
from camel.types import ModelPlatformType, ModelType

logger = get_logger(__name__)

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4_1,
)
camel_agent = ChatAgent(
    system_message="you are a helpful Terminal agent assistant.",
    model=model,
)

TBench_instance = TBench(
    name="TerminalBench",
    data_dir="data/tbench",
    save_to="tbench_results",
    processes=1,
)
print(TBench_instance.run(agent=camel_agent, subset=2))


"""
Running tasks (1/1, Accuracy: 100.00%) - Last: hello-world ✓ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:01:18
id=UUID('dfe29eda-ef75-43dd-a373-b99bbcca66d5') results=[TrialResults(id=UUID('f9196481-edc4-4215-b497-6d1bc9725ab3'), 
trial_name='hello-world.1-of-1.2025-10-13__14-44-15', task_id='hello-world', instruction='Create a file called hello.txt in
 the current directory. Write "Hello, world!" to it. Make sure it ends in a newline. Don\'t make any other files or folders.', 
 is_resolved=True, failure_mode=<FailureMode.UNSET: 'unset'>, parser_results={'test_hello_file_exists': 
 <UnitTestStatus.PASSED: 'passed'>, 'test_hello_file_content': <UnitTestStatus.PASSED: 'passed'>}, 
 recording_path='2025-10-13__14-44-15/hello-world/hello-world.1-of-1.2025-10-13__14-44-15/sessions/agent.cast',
total_input_tokens=1475, total_output_tokens=67, trial_started_at='2025-10-13T09:14:16.299415+00:00', 
trial_ended_at='2025-10-13T09:15:27.454845+00:00', agent_started_at='2025-10-13T09:14:22.889708+00:00',
agent_ended_at='2025-10-13T09:14:52.742704+00:00', test_started_at='2025-10-13T09:14:53.973209+00:00', 
test_ended_at='2025-10-13T09:15:17.089077+00:00')] pass_at_k={} n_resolved=1 n_unresolved=0 resolved_ids=['hello-world'] unresolved_ids=[] accuracy=1.0
"""
