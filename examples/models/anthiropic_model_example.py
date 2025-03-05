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

# Use the extended thinking model with Claude 3.7 Sonnet
config = AnthropicConfig(
    thinking={"type": "enabled", "budget_tokens": 2048}
).as_dict()

model = ModelFactory.create(
    model_platform=ModelPlatformType.ANTHROPIC,
    model_type=ModelType.CLAUDE_3_7_SONNET,
    model_config_dict=config,
)

camel_agent = ChatAgent(model=model)

user_msg = """Write a bash script that takes a matrix represented as a string with 
format '[1,2],[3,4],[5,6]' and prints the transpose in the same format.
"""  # noqa: E501

response = camel_agent.step(user_msg)
print(response.msgs[0].content)
'''
===============================================================================
# Matrix Transpose Bash Script

Here's a bash script that transposes a matrix from the format `[1,2],[3,4],[5,6]` to `[1,3,5],[2,4,6]`:

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
IFS=',' read -ra first_row <<< "${rows[0]//[\[\]]}"  # Remove brackets from first row
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
'''  # noqa: E501
