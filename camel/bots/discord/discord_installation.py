from datetime import datetime
from typing import Optional

class DiscordInstallation:
    def __init__(self, guild_id: str, access_token: str, refresh_token: str,
                 installed_at: datetime, token_expires_at: Optional[datetime] = None):
        self.guild_id = guild_id
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.installed_at = installed_at
        self.token_expires_at = token_expires_at