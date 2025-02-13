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

import time

from camel.toolkits.base import BaseToolkit


class MockToolkit(BaseToolkit):
    def time_consuming_tool(self):
        time.sleep(2)
        return "Time consuming tool run successfully!"

    def fast_tool(self):
        return "Fast tool run successfully!"


toolkit = MockToolkit(timeout=0.5)

result_1 = toolkit.time_consuming_tool()
result_2 = toolkit.fast_tool()

print(result_1)
print(result_2)
"""
===============================================================================
Function time_consuming_tool execution timed out, exceeded 0.5 seconds.
Fast tool run successfully!
===============================================================================
"""
