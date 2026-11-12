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
r"""Event-based trigger: fires when an HTTP webhook is received.

Unlike the schedule trigger (which drives itself by sleeping), a webhook
trigger is *passive*: it registers a path on a shared
:class:`WebhookServer` and fires whenever a matching request arrives. The
server is started lazily by the manager and shared across all webhook
triggers, so the agent can create many hooks on different paths against one
listening port.
"""

import asyncio
import hashlib
import hmac
from typing import Any, Dict, Optional

from camel.logger import get_logger

from .base import (
    BaseTrigger,
    EmitFn,
    new_idempotency_suffix,
    register_trigger,
)

logger = get_logger(__name__)


@register_trigger("webhook")
class WebhookTrigger(BaseTrigger):
    r"""A trigger that fires on an incoming HTTP request.

    Config shape (``TriggerSpec.config``):

    - ``path`` (str): URL path to listen on, e.g. ``"/hooks/ci"``. Must be
      unique across webhook triggers.
    - ``method`` (str): HTTP method to match (default ``"POST"``).
    - ``secret`` (Optional[str]): If set, requests must carry a valid
      ``X-Signature`` HMAC-SHA256 of the raw body, or they are rejected.

    The trigger does not own a socket; it consumes deliveries pushed by the
    shared :class:`WebhookServer` into an internal queue. ``run`` simply waits
    for deliveries and emits an event per request, carrying the parsed body as
    structured ``data``.
    """

    def __init__(self, spec) -> None:
        super().__init__(spec)
        self._queue: "asyncio.Queue[Dict[str, Any]]" = asyncio.Queue()

    @classmethod
    def validate_config(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        path = config.get("path")
        if not isinstance(path, str) or not path.startswith("/"):
            raise ValueError(
                "webhook config requires a 'path' starting with '/'."
            )
        method = str(config.get("method", "POST")).upper()
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            raise ValueError(f"Unsupported webhook method: {method}.")
        out: Dict[str, Any] = {"path": path, "method": method}
        secret = config.get("secret")
        if secret is not None:
            if not isinstance(secret, str) or not secret:
                raise ValueError(
                    "webhook 'secret' must be a non-empty string."
                )
            out["secret"] = secret
        return out

    @property
    def path(self) -> str:
        return self.spec.config["path"]

    @property
    def method(self) -> str:
        return self.spec.config.get("method", "POST")

    def verify_signature(
        self, raw_body: bytes, signature: Optional[str]
    ) -> bool:
        r"""Validate an HMAC-SHA256 signature if a secret is configured.

        Returns ``True`` when no secret is set (open hook) or when the
        signature matches.
        """
        secret = self.spec.config.get("secret")
        if not secret:
            return True
        if not signature:
            return False
        expected = hmac.new(
            secret.encode(), raw_body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def deliver(self, body: Dict[str, Any]) -> None:
        r"""Push a received request body into the trigger's queue.

        Called by :class:`WebhookServer` on the event loop thread.
        """
        self._queue.put_nowait(body)

    async def run(self, emit: EmitFn) -> None:
        while True:
            body = await self._queue.get()
            if not self.spec.enabled or self._is_exhausted():
                # Drop deliveries while paused/exhausted.
                continue
            event = self._build_event(
                slot_key=new_idempotency_suffix(), data=body
            )
            await emit(event)
