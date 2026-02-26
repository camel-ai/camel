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

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import MathToolkit
from camel.types import ModelPlatformType, ModelType


def on_request_usage(payload: dict) -> None:
    r"""Callback invoked after each non-streaming LLM request."""
    request_usage = payload["request_usage"]
    step_usage = payload["step_usage"]
    print(
        f"[request {payload['request_index']}] "
        f"response_id={payload['response_id']} "
        f"request_total_tokens={request_usage['total_tokens']} "
        f"step_total_tokens={step_usage['total_tokens']}"
    )


model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)

agent = ChatAgent(
    system_message=(
        "You are a helpful math assistant. "
        "Always use tools for arithmetic before giving the final answer."
    ),
    model=model,
    tools=MathToolkit().get_tools(),
    on_request_usage=on_request_usage,
)

response = agent.step("Calculate 123 + 456, then multiply the result by 2.")
print("\nFinal answer:")
print(response.msg.content)
print("\nStep usage:")
print(response.info.get("usage"))

'''
===============================================================================
[request 1] response_id=chatcmpl-DChD9WKCUdpDYfH6M5TOnWLrxaoTW
request_total_tokens=437 step_total_tokens=437
[request 2] response_id=chatcmpl-DChDA0sYqi9lHpRTy86SvSs339tQ9
request_total_tokens=470 step_total_tokens=907
[request 3] response_id=chatcmpl-DChDBFYQnSla6ZokAdbIzVA1Day0R
request_total_tokens=519 step_total_tokens=1426

Final answer:
The result of \( 123 + 456 \) is \( 579 \). When you multiply that by \( 2 \),
the final result is \( 1158 \).

Step usage:
{'prompt_tokens': 1346, 'completion_tokens': 80, 'total_tokens': 1426}
===============================================================================
'''
