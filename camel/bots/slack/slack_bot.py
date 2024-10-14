import logging
import os
from typing import TYPE_CHECKING, Optional

from slack_sdk.oauth.installation_store.async_installation_store import (
    AsyncInstallationStore,
)

from camel.bots.slack.models import (
    SlackEventBody,
    SlackEventProfile,
)
from camel.utils import dependencies_required

if TYPE_CHECKING:
    from slack_bolt.context.async_context import AsyncBoltContext
    from slack_bolt.context.say.async_say import AsyncSay
    from slack_sdk.web.async_client import AsyncWebClient

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class SlackBot:
    @dependencies_required('slack_bolt')
    def __init__(
        self,
        token: Optional[str] = None,
        scopes: Optional[str] = None,
        signing_secret: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri_path: str = "/slack/oauth_redirect",
        installation_store: Optional[AsyncInstallationStore] = None,
    ):
        from slack_bolt.adapter.starlette.async_handler import (
            AsyncSlackRequestHandler,
        )
        from slack_bolt.app.async_app import AsyncApp
        from slack_bolt.oauth.async_oauth_settings import AsyncOAuthSettings

        self.token = token or os.getenv("SLACK_TOKEN")
        self.scopes = scopes or os.getenv("SLACK_SCOPES")
        self.signing_secret = signing_secret or os.getenv(
            "SLACK_SIGNING_SECRET"
        )
        self.client_id = client_id or os.getenv("SLACK_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("SLACK_CLIENT_SECRET")

        if not all([self.token, self.scopes, self.signing_secret]):
            raise ValueError(
                "`SLACK_TOKEN`, `SLACK_SCOPES`, and `SLACK_SIGNING_SECRET` "
                "environment variables must be set. Get it here: "
                "`https://api.slack.com/apps`."
            )

        self._app = AsyncApp(
            logger=logger,
            signing_secret=self.signing_secret,
            installation_store=installation_store,
            token=self.token,
        )

        if client_id and client_secret:
            self._app.oauth_settings = AsyncOAuthSettings(
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=self.scopes,
                redirect_uri_path=redirect_uri_path,
            )

        self._handler = AsyncSlackRequestHandler(self._app)
        self.setup_handlers()

    def setup_handlers(self):
        self._app.event("app_mention")(self.app_mention)
        self._app.event("message")(self.on_message)

    def run(
        self,
        port: int = 3000,
        path: str = "/slack/events",
        host: Optional[str] = None,
    ) -> None:
        self._app.start(port, path, host)

    async def app_mention(
        self,
        context: "AsyncBoltContext",
        client: "AsyncWebClient",
        event: dict,
        body: dict,
    ):
        logger.info(body)

    async def on_message(
        self,
        context: "AsyncBoltContext",
        client: "AsyncWebClient",
        event: dict,
        body: dict,
        say: "AsyncSay",
    ):
        await context.ack()

        event_profile = SlackEventProfile(**event)
        event_body = SlackEventBody(**body)

        logger.info("on_message, context: {}".format(context))
        logger.info("on_message, client: {}".format(client))
        logger.info("on_message, event_profile: {}".format(event_profile))
        logger.info("on_message, event_body: {}".format(event_body))
        logger.info("on_message, say: {}".format(say))

        await say("Hello, world!")


if __name__ == "__main__":
    bot = SlackBot()
    bot.run(3000)
