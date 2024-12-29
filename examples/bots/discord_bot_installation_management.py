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
import os

import uvicorn
from discord import Message
from starlette.responses import RedirectResponse

from camel.bots.discord import DiscordApp, DiscordSQLiteInstallationStore


class DiscordBot(DiscordApp):
    async def on_message(self, message: 'Message') -> None:
        if message.author == self._client.user:
            return

        if self.channel_ids and message.channel.id not in self.channel_ids:
            return

        if not self._client.user or not self._client.user.mentioned_in(
            message
        ):
            return

        installation = await self.installation_store.find_by_guild(
            str(message.guild.id)
        )
        if installation:
            await message.channel.send("Found installation.")
        else:
            await message.channel.send("No installation found for this guild.")


async def main():
    installation_store = DiscordSQLiteInstallationStore(
        database="./discord_installations.db"
    )
    await installation_store.init()

    discord_bot = DiscordBot(
        token=os.getenv("DISCORD_BOT_TOKEN"),
        client_id=os.getenv("DISCORD_BOT_CLIENT_ID"),
        client_secret=os.getenv("DISCORD_BOT_CLIENT_SECRET"),
        redirect_uri=os.getenv("DISCORD_BOT_REDIRECT_URL"),
        installation_store=installation_store,
    )

    @discord_bot.app.get(os.getenv("DISCORD_BOT_REDIRECT_URI"))
    async def oauth_redirect(code: str, guild_id: str):
        if not code:
            return {"error": "No code provided"}

        response = await discord_bot.exchange_code_for_token_response(code)
        if not response:
            return {"error": "Failed to obtain access token"}

        access_token = response.get("access_token")
        refresh_token = response.get("refresh_token")
        expires_in = response.get("expires_in")

        await discord_bot.save_installation(
            guild_id, access_token, refresh_token, expires_in
        )
        return RedirectResponse(url=f"https://discord.com/channels/{guild_id}")

    server_task = asyncio.create_task(
        uvicorn.Server(
            uvicorn.Config(discord_bot.app, host="0.0.0.0", port=8000)
        ).serve()
    )

    bot_task = asyncio.create_task(discord_bot.start())

    await asyncio.gather(server_task, bot_task)


if __name__ == "__main__":
    asyncio.run(main())
