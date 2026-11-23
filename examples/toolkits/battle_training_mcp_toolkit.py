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
"""battle.training MCP Server Example

This example connects CAMEL to battle.training — an arena where AI agents
fight rated bot battles — through its hosted MCP server at
https://api.battle.training/mcp (Streamable HTTP). No local server process
is needed.

The server's read tools are public, so the first part of the example runs
with no battle.training account and no LLM: it lists the tools, reads the
open ladders, the default ladder standings, and two example bots' records
by calling the MCP client directly.

If OPENAI_API_KEY is set, the second part hands the toolkit's tools to a
ChatAgent and asks it to summarize the standings. To use the server's
write tools (create_bot, upload_version, enrol_ladder, ...), add your
battle.training API key as a bearer token in the config's "headers".
"""

import asyncio
import os

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import MCPToolkit
from camel.types import ModelPlatformType, ModelType

# The operator's own bots on battle.training, used as read-only example
# subjects. Substitute any public bot name here.
EXAMPLE_BOTS = ["delynn-prime", "delynn-pyong"]

CONFIG_DICT = {
    "mcpServers": {
        "battle-training": {
            "url": "https://api.battle.training/mcp",
            # "headers": {"Authorization": "Bearer <redacted>"},
        }
    }
}


def _text(call_tool_result) -> str:
    """Flatten an MCP call-tool result into plain text."""
    return "\n".join(
        getattr(block, "text", str(block))
        for block in call_tool_result.content or []
    )


async def main():
    async with MCPToolkit(config_dict=CONFIG_DICT) as mcp_toolkit:
        # --- Read-only flow: direct MCP calls, no LLM required ---------
        client = mcp_toolkit.clients[0]

        mcp_tools = await client.list_mcp_tools()
        print("Available MCP tools:", [t.name for t in mcp_tools.tools])

        ladders = await client.call_tool("list_ladders", {})
        print("=== Open ladders ===")
        print(_text(ladders)[:600])

        ladder = await client.call_tool("get_ladder", {})
        print("=== Default ladder standings (excerpt) ===")
        print(_text(ladder)[:600])

        for bot_name in EXAMPLE_BOTS:
            bot = await client.call_tool("get_bot", {"name": bot_name})
            print(f"=== Bot {bot_name} (excerpt) ===")
            print(_text(bot)[:600])

        # --- Optional: let a ChatAgent summarize via the tools ---------
        if os.getenv("OPENAI_API_KEY"):
            model = ModelFactory.create(
                model_platform=ModelPlatformType.DEFAULT,
                model_type=ModelType.DEFAULT,
            )
            chat_agent = ChatAgent(
                system_message=(
                    "You are a scouting agent for battle.training. You "
                    "read public ladders and bot standings through the "
                    "battle.training MCP tools and summarize them. You "
                    "never modify anything."
                ),
                model=model,
                tools=[*mcp_toolkit.get_tools()],
            )
            response = await chat_agent.astep(
                "Read the current ladder standings and summarize the "
                f"top of the table and where the bots "
                f"{', '.join(EXAMPLE_BOTS)} sit."
            )
            print("=== Model Response ===")
            print(response.msgs[0].content)
        else:
            print(
                "OPENAI_API_KEY not set - skipping the optional ChatAgent "
                "summary. The direct read-tool calls above are the tested "
                "path of this example."
            )


# Run the async main function
if __name__ == "__main__":
    asyncio.run(main())

'''
===============================================================================
Available MCP tools: ['get_started', 'controller_api', 'get_starter',
'get_starter_sub', 'get_rules', 'create_account', 'whoami', 'create_bot',
'set_bot_x', 'set_operator_x', 'upload_version', 'get_bot', 'get_ladder',
'list_matches', 'get_match', 'list_ladders', 'get_cup', 'enrol_ladder',
'set_payout_wallet', 'scrimmage', 'get_live']
=== Open ladders ===
{
  "ladders": [
    {
      "slug": "public",
      "name": "Public ladder",
      "kind": "public",
      "status": "open",
      "enrolled": 401,
      ...
=== Default ladder standings (excerpt) ===
{
  "entries": [
    {
      "rank": 1,
      "bot": "daemon-amber",
      ...
=== Bot delynn-prime (excerpt) ===
{ "name": "delynn-prime", "theater": "armor", ... "rank": 391, "of": 401,
  "rating": 708, "wins": 24, "losses": 24, "draws": 12 }
=== Bot delynn-pyong (excerpt) ===
{ "name": "delynn-pyong", "theater": "air", ... "rank": 5, "of": 8,
  "rating": 1415, "wins": 15, "losses": 22, "draws": 32 }
OPENAI_API_KEY not set - skipping the optional ChatAgent summary. The
direct read-tool calls above are the tested path of this example.
===============================================================================
'''
