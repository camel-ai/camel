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
from datetime import datetime
from typing import Optional


class DiscordInstallation:
    r"""Represents an installation of a Discord application in a
        specific guild (server).

    Attributes:
        guild_id (str): The unique identifier for the Discord guild (server)
            where the application is installed.
        access_token (str): The access token used to authenticate API requests
            for the installed application.
        refresh_token (str): The token used to refresh the access token when
            it expires.
        installed_at (datetime): The timestamp indicating when the application
            was installed in the guild.
        token_expires_at (Optional[datetime]): The optional timestamp
            indicating when the access token will expire. Defaults to None
            if the token does not have an expiration time.
    """

    def __init__(
        self,
        guild_id: str,
        access_token: str,
        refresh_token: str,
        installed_at: datetime,
        token_expires_at: Optional[datetime] = None,
    ):
        r"""Initialize the DiscordInstallation.

        Args:
            guild_id (str): The unique identifier for the Discord guild
                (server) where the application is installed.
            access_token (str): The access token used to authenticate API
                requests for the installed application.
            refresh_token (str): The token used to refresh the access token
                when it expires.
            installed_at (datetime): The timestamp indicating when the
                application was installed in the guild.
            token_expires_at (Optional[datetime]): The optional timestamp
                indicating when the access token will expire. Defaults to None
                if the token does not have an expiration time.
                (default: :obj:`None`)
        """
        self.guild_id = guild_id
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.installed_at = installed_at
        self.token_expires_at = token_expires_at
