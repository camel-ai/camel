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

from typing import Optional

from .discord_installation import DiscordInstallation


class DiscordBaseInstallationStore:
    r"""Abstract base class for managing Discord installations.

    This class defines the interface for database operations related to storing
    and retrieving Discord installation data. Subclasses must implement these
    methods to handle database-specific logic.
    """

    async def init(self):
        r"""Initializes the database connection or structure."""
        pass

    async def save(self, installation: DiscordInstallation):
        r"""Saves or updates a Discord installation record."""
        pass

    async def find_by_guild(
        self, guild_id: str
    ) -> Optional[DiscordInstallation]:
        r"""Finds an installation record by guild ID."""
        pass

    async def delete(self, guild_id: str):
        r"""Deletes an installation record by guild ID."""
        pass


class DiscordSQLiteInstallationStore(DiscordBaseInstallationStore):
    r"""SQLite-based implementation for managing Discord installations.

    This class provides methods for initializing the database, saving,
    retrieving, and deleting installation records using SQLite.

    Attributes:
        database (str): Path to the SQLite database file.
    """

    def __init__(self, database: str):
        r"""Initializes the SQLite installation store.

        Args:
            database (str): Path to the SQLite database file.
        """
        self.database = database

    async def init(self):
        r"""Initializes the database by creating the required table if it
        does not exist."""
        import aiosqlite

        async with aiosqlite.connect(self.database) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS discord_installations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id TEXT NOT NULL UNIQUE,
                    access_token TEXT NOT NULL,
                    refresh_token TEXT NOT NULL,
                    installed_at DATETIME NOT NULL,
                    token_expires_at DATETIME
                );
                """
            )
            await db.commit()

    async def save(self, installation: DiscordInstallation):
        r"""Saves a new installation record or updates an existing one.

        Args:
            installation (DiscordInstallation): The installation data to save.
        """
        import aiosqlite

        async with aiosqlite.connect(self.database) as db:
            await db.execute(
                """
                INSERT INTO discord_installations (
                    guild_id, access_token, refresh_token, 
                    installed_at, token_expires_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    access_token = excluded.access_token,
                    refresh_token = excluded.refresh_token,
                    token_expires_at = excluded.token_expires_at;
                """,
                [
                    installation.guild_id,
                    installation.access_token,
                    installation.refresh_token,
                    installation.installed_at,
                    installation.token_expires_at,
                ],
            )
            await db.commit()

    async def find_by_guild(
        self, guild_id: str
    ) -> Optional[DiscordInstallation]:
        r"""Finds an installation record by guild ID.

        Args:
            guild_id (str): The guild ID to search for.

        Returns:
            Optional[DiscordInstallation]: The installation record if found,
                otherwise None.
        """
        import aiosqlite

        async with aiosqlite.connect(self.database) as db:
            async with db.execute(
                "SELECT guild_id, access_token, refresh_token, "
                "installed_at, token_expires_at FROM discord_installations "
                "WHERE guild_id = ?",
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

    async def delete(self, guild_id: str):
        r"""Deletes an installation record by guild ID.

        Args:
            guild_id (str): The guild ID of the record to delete.
        """
        import aiosqlite

        async with aiosqlite.connect(self.database) as db:
            await db.execute(
                "DELETE FROM discord_installations WHERE guild_id = ?",
                [guild_id],
            )
            await db.commit()
