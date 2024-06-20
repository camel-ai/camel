# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
import asyncio
import os
from typing import Optional, List, Union

import discord
from discord import Message
from discord.ext import commands
from discord.ext.commands import DefaultHelpCommand, Context, errors
from pydantic import HttpUrl

LIMITED_CHANNEL = []


def check_example(ctx: Context):
    """ function for commands.check() """
    global LIMITED_CHANNEL
    return not LIMITED_CHANNEL or ctx.channel in LIMITED_CHANNEL


class BotCog(commands.Cog):
    def __init__(self, bot: "DiscordBot"):
        self.bot = bot

    @commands.hybrid_command()
    @commands.check(check_example)
    async def rag(self, ctx: Context, content: str):
        print(f"{content=}")
        user_raw_msg = content

        await ctx.reply(user_raw_msg)


class DiscordBot(commands.Bot):
    def __init__(
            self,
            channel_ids: Optional[List[int]] = None,
            command_prefix: str = "!",
            discord_guild: str = None,
            proxy: Optional[HttpUrl] = None
    ):
        super().__init__(
            command_prefix, 
            intents=discord.Intents.all(), 
            help_command=DefaultHelpCommand(), 
            proxy=proxy
        )

        self.discord_guild = discord_guild

        global LIMITED_CHANNEL
        self.channel_ids = channel_ids
        LIMITED_CHANNEL = channel_ids

    async def on_ready(self):
        print('We have logged in as "{0.user}@{0.user.id}'.format(self))

    async def setup_hook(self) -> None:
        # setup slash commands.
        if self.discord_guild:
            print("setup slash commands.")

            guild = discord.Object(id=self.discord_guild)
            print(f"{guild=}")
            self.tree.copy_global_to(guild=guild)
            app_commands = await self.tree.sync(guild=guild)
            print(f"{app_commands=}")

    async def on_message(self, message: Message, /) -> None:
        if message.author.id == message.guild.me.id:
            return

        if self.channel_ids and message.channel.id not in self.channel_ids:
            return

        # only reply to message when the bot is mentioned.
        if message.mentions and self.user in message.mentions:
            if message.attachments:
                # handle message with attachments.
                attachment: discord.Attachment = message.attachments[0]
                # application/pdf
                print(f"attachment type: {attachment.content_type}")

            # remove the @mentions from message.
            content: str = message.content.split("<@")[0]

            # reply to the message received.
            await message.reply(content)
            # send a message to channel
            # await message.channel.send(content)

    async def on_command_error(self, context: Context, exception: errors.CommandError, /) -> None:
        if context.invoked_with == 'help':
            return
        print(context, exception)


if __name__ == "__main__":
    discord_token = os.getenv("DISCORD_TOKEN")
    if not discord_token:
        discord_token = "Your Discord Token"

    bot = DiscordBot(
        proxy="Your proxy or None",
        discord_guild="Your discord guild ID or None, slash command will not work if None."
    )
    asyncio.run(bot.add_cog(BotCog(bot)))
    bot.run(token=discord_token)
