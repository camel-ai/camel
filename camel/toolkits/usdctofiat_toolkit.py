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

"""UsdctoFiatToolkit — CAMEL toolkit.

USDCtoFiat by Galleon Labs. Built on the public Peer/ZKP2P protocol.
Docs: https://usdctofiat.xyz/developers

Wraps ``usdctofiat.cashout(mode="fast"|"best")``, ``watch``,
``withdraw``/``close``, ``deposits``, and ``estimate``. Mode is required
on every priced or mutating call. There is no default to Fast or Best.
This toolkit never accepts a wallet private key — inject a signer
callback, or call cashout without one to receive unsigned
``{to, data, value, chainId}`` txs.

Install: ``pip install camel-ai[usdctofiat]`` or ``pip install usdctofiat``.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import MCPServer, dependencies_required

logger = logging.getLogger(__name__)

_BANNED_KEY_KWARGS = (
    "private_key",
    "privateKey",
    "key",
    "secret",
    "mnemonic",
    "wallet_key",
    "evm_private_key",
    "EVM_PRIVATE_KEY",
)

_OFFRAMP_KWARGS = (
    "curator_url",
    "indexer_url",
    "curator",
    "indexer",
    "referrer",
    "referrers",
    "extra_referrers",
    "referral_code",
)


@MCPServer()
class UsdctoFiatToolkit(BaseToolkit):
    r"""USDCtoFiat toolkit for CAMEL agents by Galleon Labs.

    Built on the public Peer/ZKP2P protocol.
    Docs: https://usdctofiat.xyz/developers

    Args:
        signer (Callable, optional): Callback
            ``(unsigned_tx) -> hash | {hash, deposit_id}``. Kept in the
            host runtime. Never a private key. (default: :obj:`None`)
        timeout (float, optional): Optional per-call timeout forwarded
            to BaseToolkit. (default: :obj:`None`)
    """

    @dependencies_required("usdctofiat")
    def __init__(
        self,
        signer: Callable[[Any], Any] | None = None,
        timeout: float | None = None,
        mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        r"""Initialize UsdctoFiatToolkit.

        Args:
            signer (Callable, optional): Injected signer callback. Never
                a private key. (default: :obj:`None`)
            timeout (float, optional): Per-call timeout.
                (default: :obj:`None`)
            mode (str, optional): Rejected if set. Mode must be passed
                on each cashout/estimate call. (default: :obj:`None`)
        """
        for banned in _BANNED_KEY_KWARGS:
            if banned in kwargs:
                raise TypeError(
                    "UsdctoFiatToolkit does not accept a private key. "
                    "Inject a signer callback or call cashout without "
                    "a signer to receive unsigned txs."
                )
        if mode is not None:
            raise TypeError(
                "UsdctoFiatToolkit does not default mode. "
                'Pass mode="fast" (0% / TOFIAT) or mode="best" '
                "(Delegate, 10 bps) on each cashout/estimate call."
            )
        super().__init__(timeout=timeout)
        from usdctofiat import create_offramp

        self.signer = signer
        self.offramp = create_offramp(
            **{
                key: kwargs.pop(key)
                for key in _OFFRAMP_KWARGS
                if key in kwargs
            }
        )
        logger.info(
            "UsdctoFiatToolkit ready. signer_injected=%s",
            self.signer is not None,
        )

    def usdctofiat_cashout(
        self,
        mode: str,
        amount: str,
        currency: str,
        platform: str,
        payee: str,
    ) -> str:
        r"""Cash out Base USDC to fiat via USDCtoFiat by Galleon Labs.

        mode is required. There is no default.
        - fast: Live market pricing with 0% spread / 0 bps.
        - best: Delegate, 10 bps.

        If a signer was injected, unsigned txs are submitted and the
        deposit id / tx hash are returned. Otherwise this returns
        unsigned ``{to, data, value, chainId}`` txs for the host to
        sign. Never pass a wallet private key to this toolkit.

        Args:
            mode (str): ``"fast"`` or ``"best"``. Required.
            amount (str): Human USDC amount (string or number). An int
                is six-decimal units.
            currency (str): Fiat ISO code, e.g. EUR, USD, GBP.
            platform (str): Payment rail, e.g. revolut, venmo, monzo.
            payee (str): Handle on that platform.

        Returns:
            str: JSON string with the cash-out result or unsigned
                prepare payload.
        """
        try:
            logger.info(
                "usdctofiat_cashout mode=%s currency=%s platform=%s",
                mode,
                currency,
                platform,
            )
            if self.signer is None:
                prepared = self.offramp.prepare(
                    mode=mode,
                    amount=amount,
                    currency=currency,
                    platform=platform,
                    payee=payee,
                )
                return _dumps(
                    {"prepared": _as_dict(prepared), "signed": False}
                )
            result = self.offramp.cashout(
                mode=mode,
                amount=amount,
                currency=currency,
                platform=platform,
                payee=payee,
                signer=self.signer,
            )
            return _dumps({"result": _as_dict(result), "signed": True})
        except Exception as exc:
            logger.error("usdctofiat_cashout failed: %s", exc)
            return _error(exc)

    def usdctofiat_watch(self, deposit_id: str) -> str:
        r"""Watch a USDCtoFiat deposit by id (indexer snapshot).

        Args:
            deposit_id (str): Fast composite resume key or Best numeric
                EscrowV2 id.

        Returns:
            str: JSON list of deposit snapshots.
        """
        try:
            rows = list(self.offramp.watch(deposit_id))
            return _dumps({"deposit_id": deposit_id, "snapshots": rows})
        except Exception as exc:
            logger.error("usdctofiat_watch failed: %s", exc)
            return _error(exc)

    def usdctofiat_withdraw(self, deposit_id: str) -> str:
        r"""Withdraw / close a USDCtoFiat deposit.

        Returns a signed result when a signer is injected, otherwise
        the unsigned withdraw tx.

        Args:
            deposit_id (str): EscrowV2 deposit id.

        Returns:
            str: JSON signed result or unsigned withdraw tx.
        """
        try:
            result = self.offramp.withdraw(deposit_id, signer=self.signer)
            return _dumps(_as_dict(result))
        except Exception as exc:
            logger.error("usdctofiat_withdraw failed: %s", exc)
            return _error(exc)

    def usdctofiat_close(self, deposit_id: str) -> str:
        r"""Alias of usdctofiat_withdraw. Unwind a Best or Fast deposit.

        Args:
            deposit_id (str): EscrowV2 deposit id.

        Returns:
            str: JSON signed result or unsigned withdraw tx.
        """
        return self.usdctofiat_withdraw(deposit_id)

    def usdctofiat_deposits(self, owner: str) -> str:
        r"""List USDCtoFiat deposits for an owner address.

        Args:
            owner (str): 0x depositor on Base.

        Returns:
            str: JSON list of deposits for the owner.
        """
        try:
            return _dumps(
                {"owner": owner, "deposits": self.offramp.deposits(owner)}
            )
        except Exception as exc:
            logger.error("usdctofiat_deposits failed: %s", exc)
            return _error(exc)

    def usdctofiat_estimate(
        self, mode: str, amount: str, currency: str
    ) -> str:
        r"""Estimate a USDCtoFiat cash-out. Not a locked quote.

        mode is required. fast = 0 bps seller spread. best = 10 bps
        manager fee.

        Args:
            mode (str): ``"fast"`` or ``"best"``. Required.
            amount (str): Human USDC amount.
            currency (str): Fiat ISO code.

        Returns:
            str: JSON estimate payload.
        """
        try:
            return _dumps(
                _as_dict(
                    self.offramp.estimate(
                        mode=mode, amount=amount, currency=currency
                    )
                )
            )
        except Exception as exc:
            logger.error("usdctofiat_estimate failed: %s", exc)
            return _error(exc)

    def get_tools(self) -> list[FunctionTool]:
        r"""Return FunctionTool wrappers for the USDCtoFiat actions.

        Returns:
            List[FunctionTool]: cashout, estimate, watch, withdraw,
                close, deposits.
        """
        return [
            FunctionTool(self.usdctofiat_cashout),
            FunctionTool(self.usdctofiat_estimate),
            FunctionTool(self.usdctofiat_watch),
            FunctionTool(self.usdctofiat_withdraw),
            FunctionTool(self.usdctofiat_close),
            FunctionTool(self.usdctofiat_deposits),
        ]


def _as_dict(value: Any) -> Any:
    if hasattr(value, "as_dict"):
        return value.as_dict()
    return value


def _dumps(payload: Any) -> str:
    return json.dumps(payload, indent=2, default=str)


def _error(exc: Exception) -> str:
    payload: dict[str, Any] = {
        "error": str(exc),
        "code": getattr(exc, "code", type(exc).__name__),
    }
    details = getattr(exc, "details", None)
    if details is not None:
        payload["details"] = details
    return _dumps(payload)
