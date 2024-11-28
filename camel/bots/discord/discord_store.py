from typing import Optional, List
from discord_installation import DiscordInstallation

class DiscordAsyncInstallationStore:
    """Manages all installation associated with a DiscordApp"""

    def __init__(self):
        self.installations = []

    async def async_save(self, installation: DiscordInstallation):
        """save an installation"""
        self.installations.append(installation)

    async def async_find_installations_by_guild(self, guild_id: str) -> Optional[DiscordInstallation]:
        """Find the installation by a guild id"""
        for inst in self.installations:
            if inst.guild_id == guild_id:
                return inst
        return None

    async def async_find_installation_by_token(self, bot_token: str) -> Optional[DiscordInstallation]:
        """find an installation by the token"""
        for inst in self.installations:
            if inst.bot_token == bot_token:
                return inst
        return None

    async def async_delete_installation(self, guild_id: str):
        """Delete an installation"""
        self.installations = [inst for inst in self.installations if inst.guild_id != guild_id]

    async def async_list_all_installations(self) -> List[DiscordInstallation]:
        """list all installations"""
        return self.installations