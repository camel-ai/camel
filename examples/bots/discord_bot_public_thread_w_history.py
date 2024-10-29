import asyncio
import os
import logging
from typing import Optional
import discord
from camel.bots import DiscordApp

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ThreadBotAgent:
    r"""A simple agent to process Discord messages and provide history responses."""

    def __init__(self, history_limit: int = 100):
        self.history_limit = history_limit

    async def collect_history(self, channel: discord.TextChannel) -> str:
        r"""Collect recent history from the given channel.

        Args:
            channel (discord.TextChannel): The channel from which to collect history.

        Returns:
            str: A formatted string of recent messages in the channel.
        """
        history = []
        async for msg in channel.history(limit=self.history_limit):
            history.append(msg.content)
        return "Here is the channel history:\n" + "\n".join(history)


class ThreadDiscordBot(DiscordApp):
    r"""Custom Discord bot that creates a public thread and responds with channel history.

    Args:
        agent (ThreadBotAgent): The agent responsible for processing messages.
        token (Optional[str]): The token used to authenticate the bot with Discord.
        channel_ids (Optional[list[int]]): A list of Discord channel IDs where the bot is allowed to interact.
    """

    def __init__(self, agent: ThreadBotAgent, token: Optional[str] = None, channel_ids: Optional[list[int]] = None):
        super().__init__(token=token, channel_ids=channel_ids)
        self.agent = agent
        self._queue = asyncio.Queue()

    async def on_ready(self):
        r"""Log a message when the bot is ready to interact."""
        logger.info(f'Logged in as {self._client.user}')

    async def on_guild_join(self, guild):
        r"""Log a message when the bot joins a new guild / server.

        Args:
            guild (discord.Guild): The guild that the bot has joined.
        """
        logger.info(f"Joined new guild: {guild.name}")

    async def on_message(self, message: discord.Message) -> None:
        r"""Handle messages that mention the bot.

        Args:
            message (discord.Message): The message object received from Discord.
        """
        if message.author == self._client.user:
            return

        if not self._client.user or not self._client.user.mentioned_in(message):
            return

        await self._queue.put(message)

    async def process_message_queue(self):
        r"""Continuously processes messages from the queue and sends responses."""
        while True:
            message: "discord.Message" = await self._queue.get()
            try:
                if not isinstance(message.channel, discord.TextChannel):
                    error_message = "Cannot create a thread within a non-text channel."
                    await message.channel.send(error_message)
                    logger.warning(f"Attempted to create a thread within a non-text channel: {message.channel.name}")
                    continue
                thread = await message.channel.create_thread(
                    name=f"Discussion with {message.author.display_name}",
                    message=message,
                    type=discord.ChannelType.public_thread
                )
                logger.info(f"Created thread: {thread.name} in channel: {message.channel.name}")

                response = await self.agent.collect_history(message.channel)

                await thread.send(response)
                logger.info(f"Sent response in thread: {thread.name}")
            except discord.Forbidden:
                error_message = "I don't have permission to create a thread here."
                await message.channel.send(error_message)
                logger.warning(f"Permission denied for creating thread in channel: {message.channel.name}")
            except discord.HTTPException as e:
                error_message = f"Failed to create a thread: {e}"
                await message.channel.send(error_message)
                logger.error(f"HTTP exception while creating thread: {e}")
            except Exception as e:
                logger.exception(f"Unexpected error while processing message: {e}")
            finally:
                self._queue.task_done()


async def main():
    discord_token = os.getenv("DISCORD_BOT_TOKEN")
    if not discord_token:
        logger.error("Discord bot token not found. Please set DISCORD_BOT_TOKEN environment variable.")
        return

    agent = ThreadBotAgent()
    bot = ThreadDiscordBot(agent=agent, token=discord_token)
    await asyncio.gather(bot.start(), bot.process_message_queue())


if __name__ == "__main__":
    asyncio.run(main())
