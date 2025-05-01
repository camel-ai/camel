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

import os

from camel.runtime import DaytonaRuntime
from camel.toolkits.function_tool import FunctionTool


def sample_function(x: int, y: int) -> int:
    return x + y


# Initialize the runtime with the API key
runtime = DaytonaRuntime(
    api_key=os.environ.get('DAYTONA_API_KEY'),
    api_url=os.environ.get('DAYTONA_API_URL'),
    language="python",
)

# Build the sandbox
runtime.build()

# Add the function to the runtime
runtime.add(
    funcs=FunctionTool(sample_function),
    entrypoint="sample_function_entry",
)

# Execute the function in the sandbox
result = runtime.tools_map["sample_function"](5, y=10)
print(f"Result: {result}")

# Clean up
runtime.stop()


"""
===============================================================================
Result: 15
===============================================================================
"""
