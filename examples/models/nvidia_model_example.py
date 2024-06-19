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
from camel.messages import BaseMessage
from camel.types import ModelType

# Define system message
sys_msg = BaseMessage.make_assistant_message(
    role_name="assistant",
    content="Ah, Paris, the City of Light! There are so many amazing things "
    "to see and do in this beautiful city ...",
)

# Set agent
camel_agent = ChatAgent(
    sys_msg,
    model_type=ModelType.NEMOTRON_4_REWARD,
)

user_msg = BaseMessage.make_user_message(
    role_name="user", content="I am going to Paris, what should I see?"
)
# Get response information
response = camel_agent.step(user_msg)
print(response.msgs[0].content)
'''
===============================================================================
helpfulness:1.6171875,correctness:1.6484375,coherence:3.3125,complexity:0.
546875,verbosity:0.515625
===============================================================================
'''
