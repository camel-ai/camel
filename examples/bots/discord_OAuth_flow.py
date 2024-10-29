from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
import httpx
import os
import logging
from typing import Optional

CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:8000/callback"
TOKEN_URL = "https://discord.com/api/oauth2/token"
USER_URL = "https://discord.com/api/users/@me"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

class DiscordOAuth:
    r"""A class representing the Discord OAuth process.

    This class is responsible for generating the OAuth URL, exchanging the authorization code
    for an access token, and retrieving user information from Discord.

    Attributes:
        client_id (str): The client ID of the Discord application.
        client_secret (str): The client secret of the Discord application.
        redirect_uri (str): The redirect URI for OAuth callbacks.
    """
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str) -> None:
        r"""Initialize the DiscordOAuth instance.

        Args:
            client_id (str): The client ID of the Discord application.
            client_secret (str): The client secret of the Discord application.
            redirect_uri (str): The redirect URI for OAuth callbacks.
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def get_oauth_url(self) -> str:
        r"""Generate the OAuth URL for user authorization.

        Returns:
            str: The URL that users should visit to authorize the application.
        """
        return (
            f"https://discord.com/api/oauth2/authorize?client_id={self.client_id}"
            f"&redirect_uri={self.redirect_uri}&response_type=code&scope=identify%20guilds"
        )

    async def exchange_code_for_token(self, code: str) -> Optional[str]:
        r"""Exchange the authorization code for an access token.

        Args:
            code (str): The authorization code received from Discord after user authorization.

        Returns:
            Optional[str]: The access token if successful, otherwise None.
        """
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(TOKEN_URL, data=data, headers=headers)
            response_data = response.json()
            return response_data.get("access_token")

    async def get_user_info(self, access_token: str) -> dict:
        r"""Retrieve user information using the access token.

        Args:
            access_token (str): The access token received from Discord.

        Returns:
            dict: The user information retrieved from Discord.
        """
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        async with httpx.AsyncClient() as client:
            user_response = await client.get(USER_URL, headers=headers)
            return user_response.json()


oauth_client = DiscordOAuth(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI)

@app.get("/")
async def home():
    r"""Redirect the user to the Discord OAuth URL.

    Returns:
        RedirectResponse: A response that redirects the user to the Discord OAuth authorization page.
    """
    oauth_url = oauth_client.get_oauth_url()
    return RedirectResponse(oauth_url)

@app.get("/callback")
async def callback(
  code: str,
  state: Optional[str] = None
):
    r"""Handle the OAuth callback from Discord.

    Args:
        request (Request): The incoming request object containing the authorization code.

    Returns:
        dict: The user information if successful, otherwise an error message.
    """
    code = request.query_params.get("code")
    if not code:
        return {"error": "No code returned"}

    access_token = await oauth_client.exchange_code_for_token(code)
    if not access_token:
        return {"error": "Failed to obtain access token"}

    user_data = await oauth_client.get_user_info(access_token)
    return user_data


def initiate_oauth_flow() -> str:
    r"""Initiate the OAuth flow by generating the authorization URL.

    Returns:
        str: The URL that users should visit to authorize the application.
    """
    return oauth_client.get_oauth_url()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
