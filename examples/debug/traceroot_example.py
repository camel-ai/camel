#!/usr/bin/env python3
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

"""
Preparation before running:
1. Set environment variables:
   - TRACEROOT_ENABLED="true"           # Enable debugging

Note:
- Debugging and tracing will only be enabled if TRACEROOT_ENABLED=true
"""

import traceroot

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import MathToolkit
from camel.types import ModelPlatformType, ModelType

logger = traceroot.get_logger('camel')


@traceroot.trace()
def main():
    math_toolkit = [*MathToolkit().get_tools()]

    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    # Define system message
    sys_msg = "You are a helpful AI assistant, skilled at answering questions."
    logger.info("System message: %s", sys_msg)

    # Create agent
    camel_agent = ChatAgent(
        system_message=sys_msg, model=model, tools=math_toolkit
    )

    user_msg = "Calculate the square root after adding 222991 and 1111"
    logger.info("User message: %s", user_msg)

    response = camel_agent.step(user_msg)
    logger.info("Agent response: %s", response.msgs[0].content)


if __name__ == "__main__":
    main()
