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
from camel.toolkits import FunctionTool, ZeroGPUToolkit

toolkit = ZeroGPUToolkit(
    api_key="your-api-key",
    project_id="your-project-id",
)


# =========================
# Direct Toolkit Usage
# =========================

print("=== Summarization ===")
print(toolkit.summarize("AI is transforming industries rapidly."))

print("\n=== Classification ===")
print(toolkit.classify_iab("Latest football match results"))

print("\n=== PII Redaction ===")
print(toolkit.redact_pii("Contact John at john@example.com"))


# =========================
# Agent Integration
# =========================

agent = ChatAgent(
    system_message="You are a helpful assistant.",
    tools=[
        FunctionTool(toolkit.summarize),
        FunctionTool(toolkit.classify_iab),
    ],
)

response = agent.step(
    input_message="Summarize this: AI is revolutionizing healthcare.",
    response_format=None,
)

print("\n=== Agent Response ===")
print(response.msgs[0].content)
