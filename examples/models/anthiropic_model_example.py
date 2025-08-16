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
from camel.configs import AnthropicConfig
from camel.models import ModelFactory
from camel.toolkits import FunctionTool
from camel.types import ModelPlatformType, ModelType

"""
please set the below os environment:
export ANTHROPIC_API_KEY=""
"""

model = ModelFactory.create(
    model_platform=ModelPlatformType.ANTHROPIC,
    model_type=ModelType.CLAUDE_3_5_SONNET,
    model_config_dict=AnthropicConfig(temperature=0.2).as_dict(),
)

# Define system message
sys_msg = "You are a helpful assistant."

# Set agent
camel_agent = ChatAgent(system_message=sys_msg, model=model)

user_msg = """Say hi to CAMEL AI, one open-source community dedicated to the 
    study of autonomous and communicative agents."""

# Get response information
response = camel_agent.step(user_msg)
print(response.msgs[0].content)
'''
===============================================================================
Hi CAMEL AI! It's great to meet an open-source community focused on advancing research in autonomous and communicative agents. Your work on developing and studying AI systems that can effectively communicate and operate autonomously is fascinating and important for the field. I appreciate communities like yours that contribute to open research and development in AI. Wishing you continued success in your mission!
===============================================================================
'''  # noqa: E501

model = ModelFactory.create(
    model_platform=ModelPlatformType.ANTHROPIC,
    model_type=ModelType.CLAUDE_3_7_SONNET,
)

camel_agent = ChatAgent(model=model)

user_msg = """Write a bash script that takes a matrix represented as a string 
with format '[1,2],[3,4],[5,6]' and prints the transpose in the same format."""

response = camel_agent.step(user_msg)
print(response.msgs[0].content)
'''
===============================================================================
# Matrix Transpose Bash Script

Here's a bash script that transposes a matrix from the format `[1,2],[3,4],[5,
6]` to `[1,3,5],[2,4,6]`:

```bash
#!/bin/bash

# Check if input argument is provided
if [ $# -lt 1 ]; then
    echo "Usage: $0 '[row1],[row2],...'"
    exit 1
fi

# Input matrix as string
input="$1"

# Remove outer brackets and split into rows
input="${input//\]\,\[/]|[}"  # Replace "],[" with "]|["
input="${input#\[}"           # Remove leading "["
input="${input%\]}"           # Remove trailing "]"
IFS='|' read -ra rows <<< "$input"

# Determine dimensions of the matrix
row_count="${#rows[@]}"
IFS=',' read -ra first_row <<< "${rows[0]//[\[\]]}"  # Remove brackets from 
first row
col_count="${#first_row[@]}"

# Create transpose
result=""
for (( col=0; col<col_count; col++ )); do
    result+="["
    for (( row=0; row<row_count; row++ )); do
        # Extract current row without brackets
        current="${rows[row]//[\[\]]}"
        # Split by commas
        IFS=',' read -ra elements <<< "$current"
        # Add element to transpose
        result+="${elements[col]}"
        # Add comma if not the last element
        if (( row < row_count-1 )); then
            result+=","
        fi
    done
    result+="]"
    # Add comma if not the last row
    if (( col < col_count-1 )); then
        result+=","
    fi
done

echo "$result"
```

## How to Use:

1. Save the script to a file (e.g., `transpose.sh`)
2. Make it executable: `chmod +x transpose.sh`
3. Run it with your matrix: `./transpose.sh "[1,2],[3,4],[5,6]"`

## Example:
- Input: `[1,2],[3,4],[5,6]`
- Output: `[1,3,5],[2,4,6]`

The script works by:
1. Parsing the input string to extract rows and elements
2. Finding the dimensions of the original matrix
3. Creating the transpose by iterating through columns first, then rows
4. Formatting the result with proper brackets and commas
===============================================================================
'''


def my_add(a: int, b: int) -> int:
    """Add two numbers together and return the result."""
    return a + b


anthropic_model = ModelFactory.create(
    model_platform=ModelPlatformType.ANTHROPIC,
    model_type=ModelType.CLAUDE_3_5_SONNET,
    model_config_dict=AnthropicConfig(temperature=0.2).as_dict(),
)

anthropic_agent = ChatAgent(
    model=anthropic_model,
    tools=[FunctionTool(my_add)],
)

print("Testing Anthropic agent with tool calling:")
user_msg = "Use the tool my_add to calculate 2 + 2"
response = anthropic_agent.step(user_msg)
print(response.msgs[0].content)
"""
===============================================================================
The result of adding 2 + 2 is 4.
===============================================================================
"""

# Check if tool was called
if response.info and response.info.get("tool_calls"):
    print("Tool was called successfully!")
    print(f"Tool calls: {response.info['tool_calls']}")
else:
    print("No tool calls were made.")

"""
===============================================================================
Tool was called successfully!
Tool calls: [ToolCallingRecord(tool_name='my_add', args={'a': 2, 'b': 2}, 
result=4, tool_call_id='toolu_01L1KV8GZtMEyHUGTudpMg5g')]
===============================================================================
"""

model = ModelFactory.create(
    model_platform=ModelPlatformType.ANTHROPIC,
    model_type=ModelType.CLAUDE_SONNET_4,
    model_config_dict={
        "extra_body": {"thinking": {"type": "enabled", "budget_tokens": 2000}}
    },
)

camel_agent = ChatAgent(model=model)

user_msg = """Are there an infinite number of prime numbers such that n mod 4 
== 3?"""

response = camel_agent.step(user_msg)
print(response.msgs[0].content)

"""
===============================================================================
Yes, there are infinitely many prime numbers that are congruent to 3 modulo 4.

This can be proven using a technique similar to Euclid's proof of the 
infinitude of primes. Here's the proof:

**Proof by contradiction:**

Assume there are only finitely many primes of the form 4k + 3. Let's call them 
p₁, p₂, ..., pₙ where each pᵢ ≡ 3 (mod 4).

Consider the number N = 4(p₁ × p₂ × ... × pₙ) - 1.

Note that N ≡ 3 (mod 4) since 4(p₁ × p₂ × ... × pₙ) ≡ 0 (mod 4), so N ≡ -1 ≡ 3 
(mod 4).

Now, N must have at least one prime factor. We know that:
- N is not divisible by any of the primes p₁, p₂, ..., pₙ (since N ≡ -1 (mod 
pᵢ) for each i)
- N cannot be divisible only by primes of the form 4k + 1, because the product 
of numbers that are ≡ 1 (mod 4) is also ≡ 1 (mod 4), but N ≡ 3 (mod 4)

Therefore, N must have at least one prime factor that is congruent to 3 modulo 
4, and this prime factor is different from all the primes in our assumed 
finite list.

This contradicts our assumption that p₁, p₂, ..., pₙ were all the primes 
congruent to 3 modulo 4.

Therefore, there must be infinitely many primes of the form 4k + 3.

This result is part of **Dirichlet's theorem on arithmetic progressions**, 
which more generally states that for any arithmetic progression an + b where 
gcd(a,b) = 1, there are infinitely many primes in that progression.
===============================================================================
"""  # noqa: RUF001


model = ModelFactory.create(
    model_platform=ModelPlatformType.ANTHROPIC,
    model_type=ModelType.CLAUDE_OPUS_4_1,
    model_config_dict={
        "extra_body": {"thinking": {"type": "enabled", "budget_tokens": 2000}}
    },
)

camel_agent = ChatAgent(model=model)

user_msg = """Are there an infinite number of prime numbers such that n mod 4 
== 3?"""

response = camel_agent.step(user_msg)
print(response.msgs[0].content)

"""
===============================================================================
Yes, there are infinitely many prime numbers p such that p ≡ 3 (mod 4).

Here's a proof by contradiction:

**Proof:**

Suppose there are only finitely many primes ≡ 3 (mod 4). Let's call them p₁, 
p₂, ..., pₙ.

Consider the number:
**N = 4p₁p₂···pₙ - 1**

Key observations about N:
1. **N ≡ 3 (mod 4)** since N = 4(p₁p₂···pₙ) - 1
2. N is odd (so 2 doesn't divide N)
3. None of the primes p₁, p₂, ..., pₙ divide N (if pᵢ divided N, then pᵢ would 
divide N - 4p₁p₂···pₙ = -1, which is impossible)

Now, N must have prime factorization. Every odd prime is either ≡ 1 (mod 4) or 
≡ 3 (mod 4).

**Crucial fact:** The product of numbers that are all ≡ 1 (mod 4) is also ≡ 1 
(mod 4).

Since N ≡ 3 (mod 4), not all of its prime factors can be ≡ 1 (mod 4). 
Therefore, N must have at least one prime factor q where q ≡ 3 (mod 4).

But we established that none of p₁, p₂, ..., pₙ divide N, so q must be a prime 
≡ 3 (mod 4) that's not in our supposedly complete list. This is a 
contradiction!

Therefore, there must be infinitely many primes ≡ 3 (mod 4).

This same argument structure can also prove there are infinitely many primes ≡ 
2 (mod 3), but interestingly, it *cannot* directly prove there are infinitely 
many primes ≡ 1 (mod 4) (that requires Dirichlet's theorem on primes in 
arithmetic progressions).
===============================================================================
"""
