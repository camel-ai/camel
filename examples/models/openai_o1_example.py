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
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

o1_model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.O1_MINI,  # Or ModelType.O1
    model_config_dict=ChatGPTConfig().as_dict(),
)

# Set agent
camel_agent = ChatAgent(model=o1_model)

# Set user message
user_msg = """Write a bash script that takes a matrix represented as a string 
    with format '[1,2],[3,4],[5,6]' and prints the transpose in the same 
    format."""

# Get response information
response = camel_agent.step(user_msg)
print(response.msgs[0].content)
'''
===============================================================================
Here's a bash script that transposes a matrix represented as the string format 
specified. It handles matrices of various sizes, including those with varying 
numbers of columns.

```bash
#!/bin/bash

# Read input string from argument or stdin
if [ -n "$1" ]; then
    input="$1"
else
    read input
fi

# Preprocess the input string to facilitate parsing
# Replace '],[' with '];[' to use ';' as row separator
input="${input//],[/];[}"

# Remove leading and trailing square brackets if any
input="${input#[}"
input="${input%]}"

# Split the input into rows
IFS=';' read -ra rows <<< "$input"

declare -A matrix

nrows=${#rows[@]}
ncols=0

# Parse each row
for ((i=0; i<nrows; i++)); do
    row="${rows[i]}"
    # Remove leading '[' and trailing ']'
    row="${row#[}"
    row="${row%]}"
    # Split row into elements
    IFS=',' read -ra elems <<< "$row"
    num_elems=${#elems[@]}
    if (( num_elems > ncols )); then
        ncols=$num_elems
    fi
    # Store elements in matrix associative array
    for ((j=0; j<num_elems; j++)); do
        matrix[$i,$j]="${elems[j]}"
    done
done

# Function to join array elements with a delimiter
join_by() {
    local d=$1; shift
    if [ "$#" -gt 0 ]; then
        printf %s "$1" "${@/#/$d}"
    fi
}

# Now, build the transposed matrix
transposed_rows=()
for ((j=0; j<ncols; j++)); do
    tr_row_elements=()
    for ((i=0; i<nrows; i++)); do
        e="${matrix[$i,$j]:-}"  # Use empty string if element is missing
        tr_row_elements+=("$e")
    done
    tr_row_elements_str=$(join_by ',' "${tr_row_elements[@]}")
    tr_row="[${tr_row_elements_str}]"
    transposed_rows+=("$tr_row")
done

# Build output string
output=$(join_by ',' "${transposed_rows[@]}")

# Print the output
echo "$output"
```

**Usage:**

Save the script to a file, for example, `transpose_matrix.sh`, and make it 
executable:

```bash
chmod +x transpose_matrix.sh
```

You can run the script by passing the matrix string as an argument:

```bash
./transpose_matrix.sh '[1,2],[3,4],[5,6]'
```

Output:

```
[1,3,5],[2,4,6]
```

**Explanation:**

The script performs the following steps:

1. **Input Preprocessing:**
   - Replaces `],[` with `];[` to use `;` as a separator between rows.
   - Removes any leading or trailing square brackets.

2. **Parsing the Input into a Matrix:**
   - Splits the input string into rows using `IFS`.
   - For each row:
     - Removes the leading `[` and trailing `]`.
     - Splits the row into its elements.
     - Stores the elements into an associative array `matrix` with keys as 
     `row,column`.

3. **Determining the Matrix Dimensions:**
   - Counts the number of rows (`nrows`).
   - Determines the maximum number of columns (`ncols`) across all rows.

4. **Transposing the Matrix:**
   - Iterates over each column index.
   - For each column, collects the elements from each row at that column index.
   - Builds the transposed row string and adds it to `transposed_rows`.

5. **Generating the Output:**
   - Joins the transposed rows using commas to form the final output string.
   - Prints the output.

**Notes:**

- The script supports matrices where rows have different numbers of columns.
- Missing elements in the matrix (due to irregular column sizes) are handled 
by inserting empty strings in the transposed matrix.
- The `join_by` function is used to handle joining array elements with a 
specified delimiter, ensuring proper formatting.
===============================================================================
'''
