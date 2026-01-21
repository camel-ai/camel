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
    model_type=ModelType.CLAUDE_3_HAIKU,
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
Hi CAMEL AI! I'm an AI assistant created by Anthropic. I'm happy to chat and help out however I can. Let me know if you have any questions or if there's anything I can assist with.
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
Here's a bash script that takes a matrix represented as a string with the format '[1,2],[3,4],[5,6]' and prints its transpose in the same format:

```bash
#!/bin/bash

# Check if an argument is provided
if [ $# -ne 1 ]; then
    echo "Usage: $0 '[1,2],[3,4],[5,6]'"
    exit 1
fi

matrix=$1

# Remove any spaces from the input
matrix=${matrix// /}

# Extract rows using regex
if [[ ! $matrix =~ ^\[([0-9,]+)\](,\[([0-9,]+)\])*$ ]]; then
    echo "Invalid matrix format. Expected format: '[1,2],[3,4],[5,6]'"
    exit 1
fi

# Split the matrix into rows
IFS='],[' read -ra rows <<< "${matrix//[\[\]]/}"

# Determine the number of columns from the first row
IFS=',' read -ra first_row <<< "${rows[0]}"
num_cols=${#first_row[@]}
num_rows=${#rows[@]}

# Initialize an empty array to store the transposed matrix
declare -A transposed

# Fill the transposed matrix
for ((i=0; i<num_rows; i++)); do
    IFS=',' read -ra row_values <<< "${rows[i]}"
    for ((j=0; j<num_cols; j++)); do
        transposed[$j,$i]=${row_values[j]}
    done
done

# Build the output string
result=""
for ((i=0; i<num_cols; i++)); do
    result+="["
    for ((j=0; j<num_rows; j++)); do
        result+="${transposed[$i,$j]}"
        if ((j < num_rows-1)); then
            result+=","
        fi
    done
    result+="]"
    if ((i < num_cols-1)); then
        result+=","
    fi
done

echo "$result"
```

Usage example:
```
$ ./transpose.sh '[1,2],[3,4],[5,6]'
[1,3,5],[2,4,6]
```

The script works as follows:
1. It checks if an input argument is provided
2. It removes any spaces from the input
3. It validates the input format
4. It splits the matrix into rows
5. It determines the number of columns and rows
6. It creates a transposed matrix by swapping rows and columns
7. It builds the output string in the required format
8. It prints the transposed matrix

The transpose operation converts rows into columns and vice versa, so a matrix like '[1,2],[3,4],[5,6]' (which represents a 3x2 matrix) becomes '[1,3,5],[2,4,6]' (a 2x3 matrix).
'''  # noqa: E501


def my_add(a: int, b: int) -> int:
    """Add two numbers together and return the result."""
    return a + b


anthropic_model = ModelFactory.create(
    model_platform=ModelPlatformType.ANTHROPIC,
    model_type=ModelType.CLAUDE_3_5_HAIKU,
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
The result of adding 2 and 2 is 4, as calculated by the my_add tool.
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
Tool calls: [ToolCallingRecord(tool_name='my_add', args={'a': 2, 'b': 2}, result=4, tool_call_id='toolu_019iGVdtjmzai2pwmCkX3f5T', images=None)]
===============================================================================
"""  # noqa: E501

model = ModelFactory.create(
    model_platform=ModelPlatformType.ANTHROPIC,
    model_type=ModelType.CLAUDE_SONNET_4_5,
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

This can be proven using a clever argument similar to Euclid's proof of the
infinitude of primes:

**Proof:**

Suppose there are only finitely many primes ≡ 3 (mod 4), say p₁, p₂, ..., pₖ.

Consider the number:
N = 4(p₁ · p₂ · ... · pₖ) - 1

Note that N ≡ -1 ≡ 3 (mod 4).

Now, N must have at least one prime divisor q where q ≡ 3 (mod 4). Why?
Because:
- The product of numbers that are ≡ 1 (mod 4) is also ≡ 1 (mod 4)
- Since N ≡ 3 (mod 4), it cannot be factored solely into primes ≡ 1 (mod 4)
- (Note: 2 ∤ N since N is odd)

This prime divisor q cannot be any of p₁, p₂, ..., pₖ because:
- q divides N = 4(p₁ · p₂ · ... · pₖ) - 1
- If q = pᵢ for some i, then q would divide both N and 4(p₁ · p₂ · ... · pₖ)
- Therefore q would divide their difference, which is 1 — a contradiction

So we've found a new prime ≡ 3 (mod 4) not in our original list, contradicting
our assumption.

Therefore, there are infinitely many primes ≡ 3 (mod 4). ∎
===============================================================================
"""


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
Yes, there are infinitely many primes congruent to 3 modulo 4.

Here's a classic elementary proof by contradiction:

**Proof:**

Suppose there are only finitely many primes ≡ 3 (mod 4). Let's call them p₁, p₂, ..., pₖ.

Consider the number:
N = 4p₁p₂...pₖ - 1

Note that N ≡ 3 (mod 4) since N = 4(p₁p₂...pₖ) - 1.

Now, N must have prime factorization. Let's analyze the primes that divide N:

1) N is odd (since N ≡ 3 (mod 4)), so 2 doesn't divide N.

2) None of p₁, p₂, ..., pₖ divide N, because if pᵢ divided N, then pᵢ would divide N - 4p₁p₂...pₖ = -1, which is impossible.

3) Every odd prime is either ≡ 1 (mod 4) or ≡ 3 (mod 4).

4) The product of primes that are all ≡ 1 (mod 4) is also ≡ 1 (mod 4), since 1 * 1 * ... * 1 ≡ 1 (mod 4).

5) Since N ≡ 3 (mod 4), at least one prime factor of N must be ≡ 3 (mod 4).

6) But this prime cannot be any of p₁, p₂, ..., pₖ (from point 2), so there must be another prime ≡ 3 (mod 4).

This contradicts our assumption that p₁, p₂, ..., pₖ were all such primes.

Therefore, there are infinitely many primes ≡ 3 (mod 4).

**Note:** This is actually a special case of Dirichlet's theorem on primes in arithmetic progressions, which states that for coprime integers a and d, there are infinitely many primes p such that p ≡ a (mod d).
===============================================================================
"""  # noqa: E501
