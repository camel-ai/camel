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
Clean example demonstrating the improved context handoff design.

Key improvements:
- Agent manages its own state (no circular dependency)
- Toolkit focuses on file operations and summarization
- Clear separation of concerns
"""

from camel.agents import ChatAgent
from camel.models.model_factory import ModelFactory
from camel.toolkits.context_summarizer_toolkit import ContextSummarizerToolkit
from camel.types import ModelPlatformType, ModelType

# Create shared model
model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
)

print("=== Clean Context Handoff Example ===\n")

# ========= PHASE 1: Agent1 conversation and context saving =========
print("--- Phase 1: Agent1 Initial Conversation ---")

# Create Agent1
agent1 = ChatAgent(
    system_message="You are a helpful cooking assistant.",
    model=model,
    agent_id="cooking_agent_001",
)

# Agent1 uses toolkit for context management
toolkit1 = ContextSummarizerToolkit(
    agent=agent1,
    working_directory="./clean_handoff_context",
)
agent1.add_tools(toolkit1.get_tools())

# Conversation with Agent1
response1 = agent1.step(
    "Hi! I'm Sarah. Help me make fresh pasta. I have both "
    "all-purpose and semolina flour."
)
print(f"Agent1: {response1.msgs[0].content[:100]}...")

'''
Agent1: Hi Sarah! I'd love to help you make fresh pasta. 
Since you have both all-purpose and semolina flour,...
'''

# Agent1 saves its conversation
save_result = toolkit1.summarize_full_conversation_history()
print(f"Save result: {save_result}")

# Get the summary file path
summary_file = toolkit1.working_directory / "agent_memory_summary.md"
print(f"Summary saved to: {summary_file}\n")

# ========= PHASE 2: Agent2 loads context and continues =========
print("--- Phase 2: Agent2 Context Loading ---")

# Create Agent2 (completely independent)
agent2 = ChatAgent(
    system_message="You are a helpful cooking assistant.",
    model=model,
    agent_id="cooking_agent_002",
)

# Agent2 loads context using its own method
load_result = agent2.load_context_summary(str(summary_file))
print(f"Load result: {load_result}")

# Test context continuity
print("\n--- Testing Context Continuity ---")
response2 = agent2.step(
    "Hi again! What was my name and what flour combination "
    "did we discuss for pasta?"
)
print(f"Agent2: {response2.msgs[0].content}")

'''
Agent2: Hi Sarah! We discussed using a combination of all-purpose flour and 
semolina flour for making your fresh pasta. This mix can help improve the 
texture of the dough. If you have any questions or need further assistance 
with your pasta-making, feel free to ask!
'''

print("\n--- Natural Continuation ---")
response3 = agent2.step("Perfect! Now help me make a sauce for the pasta.")
print(f"Agent2: {response3.msgs[0].content[:200]}...")

'''
Agent2: Sure, Sarah! Here's a simple yet delicious sauce that pairs 
beautifully with fresh pasta. Let's make a classic garlic and olive oil sauce 
(Aglio e Olio):
### Garlic and Olive Oil Sauce (Aglio e Olio)...
'''

print("\n=== Clean Design Benefits ===")
