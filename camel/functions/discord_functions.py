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

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from discord import Client


def _login_discord(
    discord_token: Optional[str] = None,
    application_id: Optional[int] = None,
) -> Client:
    r"""Authenticate using the Discord API.

    Args:
        discord_token (Optional[str]): The Discord authentication token.
        application_id (Optional[int]): The client's application ID.

    Returns:
        Client: A Client object for interacting with the Discord API.

    Raises:
        ImportError: If the discord package is not installed.
        ValueError: If the discord_token is not provided.
    """
    import os

    try:
        import discord
    except ImportError as e:
        raise ImportError(
            "Cannot import discord. Please install the package with `pip install discord`."
        ) from e

    if discord_token is None:
        discord_token = os.getenv("DISCORD_TOKEN")
    if discord_token is None:
        raise ValueError(
            "Must specify `discord_token` or set the environment variable `DISCORD_TOKEN`."
        )

    client = discord.Client(application_id=application_id)  # type: ignore[call-arg]
    client.login(discord_token)  # type: ignore[unused-coroutine]
    return client


def get_client_info(
    discord_token: Optional[str] = None, application_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    r"""Retrieve user and message information from the Discord client.

    Args:
        discord_token (Optional[str]): The Discord authentication token.
        application_id (Optional[int]): The client's application ID.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing user
            information and cached messages.
    """
    discord_client = _login_discord(discord_token, application_id)

    cached_messages = [
        message.clean_content()
        for message in discord_client.cached_messages()  # type: ignore[operator]
    ]

    user_info = {
        "user_name": discord_client.user().name,  # type: ignore[operator,misc]
        "user_id": discord_client.user().id,  # type: ignore[operator,misc]
        "user_discriminator": discord_client.user().discriminator,  # type: ignore[operator,misc]
    }

    combined_info = [user_info, *cached_messages]
    return combined_info
