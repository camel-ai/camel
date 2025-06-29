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
from camel.toolkits import OrigeneToolkit

agent = ChatAgent("You are named origene assistant.", model="gpt-4o-mini",tools=[*OrigeneToolkit().get_tools()])

user_msg = "what is the chemical structure of 1,2-dimethylbenzene?"


response = agent.step(user_msg)

print(response.msgs[0].content)

"""
===============================================================================
2025-06-29 21:27:51,409 - camel.camel.toolkits.mcp_toolkit - WARNING - MCPToolkit is not connected. Tools may not be available until connected.
2025-06-29 21:27:51,409 - camel.agents.chat_agent - WARNING - Model type 'gpt-4o-mini' provided without a platform. Using platform 'ModelPlatformType.DEFAULT'. Note: platform is not automatically inferred based on model type.
1,2-Dimethylbenzene, commonly known as orthoxylene (or o-xylene), is an aromatic hydrocarbon with the chemical formula \(C_8H_{10}\). Its structure consists of a benzene ring with two methyl groups (-CH₃) attached to adjacent carbon atoms.

The chemical structure can be represented as follows:

```
       CH3
        |
   C6H4-C-CH3
        |
```

Here, the benzene ring (C₆H₄) is shown in the center, with two methyl groups (CH₃) at the 1 and 2 positions relative to each other on the ring. In a more detailed structural representation, it can be depicted as:

```
      C
    // \\
   C     C
  ||     ||
   C     C
    \\ // 
      C
```

With the CH₃ groups on adjacent carbons in the benzene ring.


===============================================================================

"""
