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
from camel.toolkits import AgentToolkit
from camel.types import ModelPlatformType, ModelType

# Define system message for the parent agent
sys_msg = (
    "You are a manager agent that delegates tasks to sub-agents. "
    "Use agent_run_subagent with wait=True when you need a sub-agent result "
    "before you can continue. Use wait=False only if you intentionally want "
    "to do other work first and then call agent_get_task_output later."
)

# Create model and AgentToolkit
model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)

agent_toolkit = AgentToolkit()

# Create the parent agent and register the toolkit
parent_agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=agent_toolkit.get_tools(),
    toolkits_to_register_agent=[agent_toolkit],
)

# Ask the parent agent to delegate a research task to a sub-agent
usr_msg = (
    "Run a research sub-agent to summarize the key differences "
    "between Python asyncio and threading. "
    "Wait for the result and report it back to me."
)

response = parent_agent.step(usr_msg)
print(response.msgs[0].content)
"""
===============================================================================
Here is a summary of the key differences between Python's asyncio and
threading:

1. Concurrency Models
- asyncio: Uses asynchronous programming with an event loop, coroutines (async
def), and await expressions. It runs single-threaded concurrency with
cooperative task switching at await points. Designed for non-blocking I/O
operations.
- threading: Uses preemptive multitasking with multiple OS threads that can
run concurrently. Context switching is managed by the OS and can happen
anytime. Threads can block independently.

2. Use Cases
- asyncio: Ideal for I/O-bound, high-concurrency network code, suitable when
many simultaneous I/O operations or connections are involved. Less suitable
for CPU-bound tasks. Requires async-compatible libraries.
- threading: Good for I/O-bound tasks involving blocking or legacy blocking
APIs, some CPU-bound parallelism (limited by GIL). Useful with non-async
libraries and for real parallelism via C extensions or multiprocessing.

3. Performance Characteristics
- asyncio: Lower overhead than threads, scalable to thousands of tasks,
efficient for I/O-bound workloads. Runs on a single CPU core unless combined
with multiprocessing.
- threading: Higher overhead for thread management, limited CPU parallelism
due to Python's GIL, prone to race conditions requiring synchronization.

Summary Table:

| Aspect            | asyncio                            |
threading                         |
|-------------------|----------------------------------|
----------------------------------|
| Concurrency Model  | Single-threaded cooperative      | Multi-threaded
preemptive        |
| Switching         | Explicit await points             | OS-managed context
switching     |
| Suitable for      | High-concurrency I/O-bound tasks | Blocking I/O, some
CPU tasks     |
| Performance       | Low overhead, high scalability   | Higher overhead,
limited CPU parallelism due to GIL |
| Complexity        | Requires async programming model | Simpler but prone to
race conditions |
| Parallelism       | Single CPU core (multiprocessing possible) | Multiple
threads, limited by GIL |

Additional notes:
- asyncio requires async-compatible libraries and special handling for
blocking code.
- Threading requires careful synchronization to avoid data races.
- For CPU-bound parallelism, multiprocessing or native extensions are often
better than threading.

If you want, I can also provide example code snippets or deeper details on any
aspect.
===============================================================================
"""
