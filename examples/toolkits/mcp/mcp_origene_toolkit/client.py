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

import asyncio

from camel.agents import ChatAgent
from camel.toolkits import OrigeneToolkit


async def main():
    r"""Main function demonstrating OrigeneToolkit usage with custom
    configuration.

    This example shows how to pass a custom config_dict to the
    OrigeneToolkit instead of using hardcoded configuration.
    """
    # Define custom configuration for MCP servers
    config_dict = {
        "mcpServers": {
            "chembl_mcp": {
                "url": "http://127.0.0.1:8788/chembl_mcp/mcp/",
                "mode": "streamable-http",
            }
        }
    }

    # Use async context manager for automatic connection management
    # Pass config_dict as parameter instead of hardcoding it
    async with OrigeneToolkit(config_dict=config_dict) as origene_toolkit:
        user_msg = "what can you do?"
        agent = ChatAgent(
            "You are named origene assistant.",
            model="gpt-4o",
            tools=[*origene_toolkit.get_tools()],
        )
        response = agent.step(user_msg)
        print(response.msgs[0].content)
    # Toolkit is automatically disconnected when exiting the context


'''
===============================================================================
I can assist you with a variety of tasks related to chemical compounds
and substances using the PubChem database. 
Here are some of the things I can do:

1. **Search for Compounds and Substances**:
   - Search by chemical name, SMILES string, or molecular formula.
   - Perform advanced searches using complex queries.

2. **Retrieve Detailed Information**:
   - Get detailed compound and substance information by PubChem CID or SID.
   - Retrieve compound properties like molecular weight, formula, XLogP, etc.
   - Get descriptions and related data for compounds, substances, and assays.

3. **Synonyms and Identifiers**:
   - Find synonyms for compounds and substances.
   - Get CAS Registry Numbers, CIDs, and SIDs.
   
4. **3D Structure and Conformers**:
   - Access 3D structures and conformer identifiers.
   
5. **Bioassay Activities**:
   - Summarize bioassay activities for compounds and substances.

6. **Download Data**:
   - Download images of chemical structures in PNG format.
   - Export compound properties to a CSV file.

If you have any specific requests or need information on a particular compound,
feel free to ask!
===============================================================================
'''

if __name__ == "__main__":
    asyncio.run(main())
