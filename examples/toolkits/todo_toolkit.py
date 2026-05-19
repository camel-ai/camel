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
from camel.toolkits import MathToolkit, TodoToolkit
from camel.types import ModelPlatformType, ModelType

# Define system message
sys_msg = (
    "You are a math assistant that solves problems step by step. "
    "You have a todo list to track each calculation step. "
    "For EVERY step: first update the todo list (mark current step "
    "in_progress), then call the math tool to compute, then update "
    "the todo list again (mark that step completed). "
    "Always rewrite the full todo list when updating."
)

# Set model config and initialize toolkit
todo_toolkit = TodoToolkit()
math_toolkit = MathToolkit()
tools = todo_toolkit.get_tools() + math_toolkit.get_tools()

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.GPT_5_4,
)

# Set agent
camel_agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=tools,
)


def print_todos(label: str):
    r"""Helper to print the current todo state."""
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print('=' * 60)
    for item in todo_toolkit.todos:
        print(f"  [{item.status:>11}] {item.content}")
    print()


usr_msg = (
    "A company has 3 product lines with monthly revenues: "
    "Product A = $1200, Product B = $850, Product C = $2100. "
    "Solve step by step using the math tools:\n"
    "1. Add Product A + Product B revenues\n"
    "2. Add that result to Product C to get total monthly revenue\n"
    "3. Multiply total monthly revenue by 12 for annual revenue\n"
    "4. Calculate 15% tax on the annual revenue\n"
    "5. Subtract the tax from annual revenue to get net annual revenue\n"
    "Track each step in the todo list as you go."
)

response = camel_agent.step(usr_msg)
print_todos("Final state")
print(f"Agent response:\n{response.msgs[0].content}")

'''
===============================================================================
============================================================
  Final state
============================================================
  [  completed] Add Product A and Product B revenues
  [  completed] Add Product C to get total monthly revenue
  [  completed] Multiply total monthly revenue by 12 for annual revenue
  [  completed] Calculate 15% tax on annual revenue
  [  completed] Subtract tax from annual revenue to get net annual revenue

Agent response:
Here is the step-by-step calculation:

1. Product A + Product B
   $1200 + $850 = $2050

2. Add Product C for total monthly revenue
   $2050 + $2100 = $4150

3. Annual revenue
   $4150 x 12 = $49,800

4. 15% tax on annual revenue
   $49,800 x 0.15 = $7,470

5. Net annual revenue
   $49,800 - $7,470 = $42,330

Final answers:
- Total monthly revenue: $4,150
- Annual revenue: $49,800
- Tax at 15%: $7,470
- Net annual revenue: $42,330
===============================================================================
'''
