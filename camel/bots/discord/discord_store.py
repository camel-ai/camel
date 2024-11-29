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
import logging
from logging import Logger
from typing import List, Optional

import aiosqlite

from .discord_installation import DiscordInstallation


class DiscordAsyncInstallationStore:
    """Manages all installation associated with a DiscordApp"""

    def __init__(self, *, database: str, logger: Optional[Logger] = None):
        self.database = database
        self.init_called = False
        self._logger = logger or logging.getLogger(__name__)

    @property
    def logger(self) -> Logger:
        if self._logger is None:
            self._logger = logging.getLogger(__name__)
        return self._logger

    async def init(self):
        try:
            async with aiosqlite.connect(self.database) as conn:
                await conn.execute(
                    "SELECT count(1) FROM discord_installations;"
                )
                self.logger.debug(f"Database {self.database} is initialized")
        except Exception:
            await self.create_tables()
        self.init_called = True

    async def connect(self):
        if not self.init_called:
            await self.init()
        return await aiosqlite.connect(self.database)

    async def create_tables(self):
        async with aiosqlite.connect(self.database) as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS discord_installations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id TEXT NOT NULL,
                    access_token TEXT NOT NULL,
                    refresh_token TEXT NOT NULL,
                    installed_at DATETIME NOT NULL,
                    token_expires_at DATETIME
                );
                """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS discord_installations_idx 
                ON discord_installations (
                    guild_id,
                    installed_at
                );
                """
            )
            self.logger.debug(
                f"Tables have been created (database: {self.database})"
            )
            await conn.commit()

    async def async_save(self, installation: DiscordInstallation):
        async with await self.connect() as conn:
            await conn.execute(
                """
                INSERT INTO discord_installations (
                    guild_id,
                    access_token,
                    refresh_token,
                    installed_at,
                    token_expires_at
                )
                VALUES (?, ?, ?, ?, ?);
                """,
                [
                    installation.guild_id,
                    installation.access_token,
                    installation.refresh_token,
                    installation.installed_at,
                    installation.token_expires_at,
                ],
            )
            self.logger.debug(
                f"New row in discord_installations has been "
                f"created (database: {self.database})"
            )
            await conn.commit()

    async def async_find_installations_by_guild(
        self, guild_id: str
    ) -> Optional[DiscordInstallation]:
        try:
            async with await self.connect() as conn:
                async with conn.execute(
                    """
                    SELECT
                        guild_id,
                        access_token,
                        refresh_token,
                        installed_at,
                        token_expires_at
                    FROM
                        discord_installations
                    WHERE
                        guild_id = ?
                    ORDER BY installed_at DESC
                    LIMIT 1
                    """,
                    [guild_id],
                ) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        return DiscordInstallation(
                            guild_id=row[0],
                            access_token=row[1],
                            refresh_token=row[2],
                            installed_at=row[3],
                            token_expires_at=row[4],
                        )
                    return None
        except Exception as e:
            message = (
                f"Failed to find installation data for guild: {guild_id}: {e}"
            )
            self.logger.exception(message)
            return None

    async def async_find_installation_by_token(
        self, bot_token: str
    ) -> Optional[DiscordInstallation]:
        try:
            async with await self.connect() as conn:
                async with conn.execute(
                    """
                    SELECT
                        guild_id,
                        access_token,
                        refresh_token,
                        installed_at,
                        token_expires_at
                    FROM
                        discord_installations
                    WHERE
                        access_token = ?
                    ORDER BY installed_at DESC
                    LIMIT 1
                    """,
                    [bot_token],
                ) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        return DiscordInstallation(
                            guild_id=row[0],
                            access_token=row[1],
                            refresh_token=row[2],
                            installed_at=row[3],
                            token_expires_at=row[4],
                        )
                    return None
        except Exception as e:
            message = (
                f"Failed to find installation data by token: {bot_token}: {e}"
            )
            self.logger.exception(message)
            return None

    async def async_delete_installation(self, guild_id: str):
        try:
            async with await self.connect() as conn:
                await conn.execute(
                    """
                    DELETE FROM discord_installations
                    WHERE guild_id = ?
                    """,
                    [guild_id],
                )
                await conn.commit()
        except Exception as e:
            message = (
                f"Failed to delete installation data "
                f"for guild: {guild_id}: {e}"
            )
            self.logger.exception(message)

    async def async_list_all_installations(self) -> List[DiscordInstallation]:
        try:
            async with await self.connect() as conn:
                async with conn.execute(
                    """
                    SELECT
                        guild_id,
                        access_token,
                        refresh_token,
                        installed_at,
                        token_expires_at
                    FROM
                        discord_installations
                    ORDER BY installed_at DESC
                    """
                ) as cursor:
                    rows = await cursor.fetchall()
                    return [
                        DiscordInstallation(
                            guild_id=row[0],
                            access_token=row[1],
                            refresh_token=row[2],
                            installed_at=row[3],
                            token_expires_at=row[4],
                        )
                        for row in rows
                    ]
        except Exception as e:
            message = f"Failed to list all installations: {e}"
            self.logger.exception(message)
            return []
