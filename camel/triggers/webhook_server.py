# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
r"""A small shared HTTP server that dispatches requests to webhook triggers.

Runs on the manager's asyncio event loop using ``aiohttp`` (installed via the
``triggers`` extra). One server instance is shared by all webhook triggers; it
routes ``(method, path)`` to the registered :class:`~camel.triggers.
webhook_trigger.WebhookTrigger` and validates signatures before delivering.
"""

import json
from typing import TYPE_CHECKING, Dict, Tuple

from camel.logger import get_logger

if TYPE_CHECKING:
    from .webhook_trigger import WebhookTrigger

logger = get_logger(__name__)


def _require_aiohttp():
    try:
        from aiohttp import web

        return web
    except ImportError as e:
        raise ImportError(
            "Webhook triggers require the 'aiohttp' package. Install the "
            "trigger extra: pip install 'camel-ai[triggers]'."
        ) from e


class WebhookServer:
    r"""Lazily-started aiohttp server shared by all webhook triggers.

    Args:
        host (str): Bind host. Defaults to ``"127.0.0.1"``.
        port (int): Bind port. Defaults to ``8080``.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8080) -> None:
        self.host = host
        self.port = port
        # (method, path) -> trigger
        self._routes: Dict[Tuple[str, str], "WebhookTrigger"] = {}
        self._runner = None  # aiohttp AppRunner
        self._started = False

    def register(self, trigger: "WebhookTrigger") -> None:
        r"""Register a webhook trigger's route.

        Raises:
            ValueError: If the (method, path) pair is already taken.
        """
        key = (trigger.method, trigger.path)
        if key in self._routes:
            raise ValueError(
                f"Webhook path '{trigger.path}' ({trigger.method}) is already "
                f"registered by another trigger."
            )
        self._routes[key] = trigger

    def unregister(self, trigger: "WebhookTrigger") -> None:
        r"""Remove a webhook trigger's route."""
        self._routes.pop((trigger.method, trigger.path), None)

    async def _handle(self, request):
        web = _require_aiohttp()
        key = (request.method, request.path)
        trigger = self._routes.get(key)
        if trigger is None:
            return web.Response(status=404, text="No such webhook.")

        raw = await request.read()
        signature = request.headers.get("X-Signature")
        if not trigger.verify_signature(raw, signature):
            logger.warning(
                f"Rejected webhook on {request.path}: bad signature."
            )
            return web.Response(status=401, text="Invalid signature.")

        body: Dict = {}
        if raw:
            try:
                body = json.loads(raw.decode())
            except (json.JSONDecodeError, UnicodeDecodeError):
                body = {"raw": raw.decode(errors="replace")}
        body.setdefault("_headers", dict(request.headers))
        trigger.deliver(body)
        return web.Response(status=202, text="Accepted.")

    async def start(self) -> None:
        r"""Start the server if not already running (idempotent)."""
        if self._started:
            return
        web = _require_aiohttp()
        app = web.Application()
        # Catch-all: route by (method, path) inside the handler so triggers
        # can be added/removed without rebuilding the app.
        app.router.add_route("*", "/{tail:.*}", self._handle)
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self.host, self.port)
        await site.start()
        self._started = True
        logger.info(
            f"Webhook server listening on http://{self.host}:{self.port}"
        )

    async def stop(self) -> None:
        r"""Stop the server if running."""
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None
        self._started = False

    @property
    def is_running(self) -> bool:
        return self._started
