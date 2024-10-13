from typing import Optional

from slack_bolt.adapter.starlette.async_handler import AsyncSlackRequestHandler
from slack_bolt.app.async_app import AsyncApp
from slack_bolt.oauth.async_oauth_settings import AsyncOAuthSettings
from slack_sdk.oauth.installation_store.async_installation_store import (
    AsyncInstallationStore,
)


class SlackApp:
    def __init__(
            self,
            token: str,
            scopes: str,
            signing_secret: str,
            client_id: Optional[str] = None,
            client_secret: Optional[str] = None,
            redirect_uri_path: str = "/slack/oauth_redirect",
            installation_store: Optional[AsyncInstallationStore] = None,
    ):
        self._app = AsyncApp(
            oauth_settings=AsyncOAuthSettings(
                client_id=client_id,
                client_secret=client_secret,
                scopes=scopes,
                redirect_uri_path=redirect_uri_path,
            ),
            signing_secret=signing_secret,
            installation_store=installation_store,
            token=token,
        )

        self._handler = AsyncSlackRequestHandler(self._app)
        self.setup_handlers()

    def setup_handlers(self):
        self._app.event("app_mention")(self.app_mention)
        self._app.event("message")(self.on_message)
        self._app.event("message.im")(self.on_message)

    def start(self):
        self._app.start(3000)

    def app_mention(self, context, event, say):
        say("Hello!")

    def on_message(self, event, say):
        say("Hello!")
