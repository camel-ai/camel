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
from typing import Any, Dict, Optional

from aiohttp import web

from camel.logger import get_logger
from camel.triggers.base_trigger import (
    BaseTrigger,
    TriggerEvent,
    TriggerState,
    TriggerType,
)

logger = get_logger(__name__)


class WebhookTrigger(BaseTrigger):
    """Webhook trigger for external HTTP events"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.server: Optional[web.Application] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None

    def validate_config(self, config: Dict[str, Any]) -> bool:
        required_fields = ["port", "path"]
        return all(field in config for field in required_fields)

    async def initialize(self) -> bool:
        if not self.validate_config(self.config):
            return False

        self.server = web.Application()
        self.server.router.add_post(self.config["path"], self._handle_webhook)
        return True

    async def activate(self) -> bool:
        if not self.server:
            await self.initialize()

        self.runner = web.AppRunner(self.server)
        await self.runner.setup()

        self.site = web.TCPSite(
            self.runner,
            self.config.get("host", "localhost"),
            self.config["port"],
        )
        await self.site.start()
        self.state = TriggerState.ACTIVE
        return True

    async def deactivate(self) -> bool:
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        self.state = TriggerState.INACTIVE
        return True

    async def test_connection(self) -> bool:
        # Test if port is available
        try:
            test_app = web.Application()
            test_runner = web.AppRunner(test_app)
            await test_runner.setup()
            test_site = web.TCPSite(
                test_runner, "localhost", self.config["port"]
            )
            await test_site.start()
            await test_site.stop()
            await test_runner.cleanup()
            return True
        except:
            return False

    async def _handle_webhook(self, request: web.Request) -> web.Response:
        try:
            payload = await request.json()
            headers = dict(request.headers)

            event = await self.process_trigger_event(
                {
                    "payload": payload,
                    "headers": headers,
                    "method": request.method,
                    "url": str(request.url),
                }
            )

            await self._emit_trigger_event(event)
            return web.json_response({"status": "success"})
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def process_trigger_event(self, event_data: Any) -> TriggerEvent:
        return TriggerEvent(
            trigger_id=self.trigger_id,
            trigger_type=TriggerType.WEBHOOK,
            timestamp=datetime.now(),
            payload=event_data["payload"],
            metadata={
                "headers": event_data["headers"],
                "method": event_data["method"],
                "url": event_data["url"],
            },
        )
