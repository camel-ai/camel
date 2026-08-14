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

"""Mocked unit tests for UsdctoFiatToolkit."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("usdctofiat")

from usdctofiat import ModeRequired  # noqa: E402
from usdctofiat.types import (  # noqa: E402
    CashoutResult,
    Estimate,
    PreparedCashout,
    UnsignedTx,
)

from camel.toolkits.usdctofiat_toolkit import UsdctoFiatToolkit  # noqa: E402


def _prepared(mode: str = "fast") -> PreparedCashout:
    return PreparedCashout(
        mode=mode,  # type: ignore[arg-type]
        txs=[
            UnsignedTx(
                to="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                data="0x095ea7b3",
            ),
            UnsignedTx(
                to="0x777777779d229cdF3110e9de47943791c26300Ef",
                data="0xcreate",
            ),
        ],
        steps=(
            ["approve", "createDeposit"]
            if mode == "fast"
            else ["approve", "createDeposit", "setRateManager"]
        ),
        payee_details_hash="0x11" + "ab" * 31,
        amount_units=100_000_000,
        platform="revolut",
        currency="EUR",
        attribution={
            "referral_code": "TOFIAT",
            "referrers": ["galleonlabs"],
        },
    )


@pytest.fixture
def mock_offramp():
    client = MagicMock()
    client.prepare.return_value = _prepared("fast")
    client.cashout.return_value = CashoutResult(
        deposit_id="42",
        tx_hash="0x" + "ab" * 32,
        mode="fast",
        tx_hashes=["0x" + "ab" * 32],
        prepared=_prepared("fast"),
    )
    client.estimate.return_value = Estimate(
        mode="fast",
        amount_units=100_000_000,
        currency="EUR",
        rate="1",
        receive_amount="100",
        spread_bps=0,
        manager_fee_bps=0,
    )
    client.deposits.return_value = [{"id": "42", "status": "ACTIVE"}]
    client.watch.return_value = iter([{"id": "42", "status": "ACTIVE"}])
    client.withdraw.return_value = UnsignedTx(
        to="0x777777779d229cdF3110e9de47943791c26300Ef",
        data="0xwithdraw",
    )
    return client


@pytest.fixture
def tools(mock_offramp):
    with patch("usdctofiat.create_offramp", return_value=mock_offramp):
        yield UsdctoFiatToolkit(), mock_offramp


def test_docstring_discloses_product_and_docs():
    import camel.toolkits.usdctofiat_toolkit as module

    text = f"{UsdctoFiatToolkit.__doc__ or ''} {module.__doc__ or ''}"
    lowered = text.lower()
    assert "usdctofiat" in lowered
    assert "galleon" in lowered
    assert "usdctofiat.xyz/developers" in lowered


def test_mode_is_not_a_constructor_default(mock_offramp):
    with patch("usdctofiat.create_offramp", return_value=mock_offramp):
        with pytest.raises(TypeError, match="does not default mode"):
            UsdctoFiatToolkit(mode="fast")
        with pytest.raises(TypeError, match="does not default mode"):
            UsdctoFiatToolkit(mode="best")
        UsdctoFiatToolkit()


def test_no_private_key_constructor(mock_offramp):
    with patch("usdctofiat.create_offramp", return_value=mock_offramp):
        with pytest.raises(TypeError, match="does not accept a private key"):
            UsdctoFiatToolkit(private_key="0xabc")
        with pytest.raises(TypeError, match="does not accept a private key"):
            UsdctoFiatToolkit(evm_private_key="0xabc")
        kit = UsdctoFiatToolkit()
        assert not hasattr(kit, "private_key")
        assert kit.signer is None


def test_get_tools_registers_prefixed_names(mock_offramp):
    with patch("usdctofiat.create_offramp", return_value=mock_offramp):
        names = {
            tool.get_function_name()
            for tool in UsdctoFiatToolkit().get_tools()
        }
        assert names == {
            "usdctofiat_cashout",
            "usdctofiat_estimate",
            "usdctofiat_watch",
            "usdctofiat_withdraw",
            "usdctofiat_close",
            "usdctofiat_deposits",
        }


def test_cashout_without_signer_returns_unsigned_prepare(tools):
    kit, offramp = tools
    payload = json.loads(
        kit.usdctofiat_cashout(
            mode="fast",
            amount="100",
            currency="EUR",
            platform="revolut",
            payee="alice",
        )
    )
    assert payload["signed"] is False
    assert payload["prepared"]["mode"] == "fast"
    assert payload["prepared"]["steps"] == ["approve", "createDeposit"]
    assert payload["prepared"]["attribution"]["referral_code"] == "TOFIAT"
    offramp.prepare.assert_called_once()
    offramp.cashout.assert_not_called()


def test_cashout_with_injected_signer(mock_offramp):
    def signer(tx):
        return {"hash": "0x" + "cd" * 32, "deposit_id": "42"}

    with patch("usdctofiat.create_offramp", return_value=mock_offramp):
        kit = UsdctoFiatToolkit(signer=signer)
        payload = json.loads(
            kit.usdctofiat_cashout(
                mode="fast",
                amount="10",
                currency="GBP",
                platform="monzo",
                payee="alice",
            )
        )
        assert payload["signed"] is True
        assert payload["result"]["deposit_id"] == "42"
        assert payload["result"]["mode"] == "fast"
        mock_offramp.cashout.assert_called_once()
        kwargs = mock_offramp.cashout.call_args.kwargs
        assert kwargs["mode"] == "fast"
        assert kwargs["signer"] is signer


def test_cashout_mode_required_is_returned_as_json(tools):
    kit, offramp = tools
    offramp.prepare.side_effect = ModeRequired()
    payload = json.loads(
        kit.usdctofiat_cashout(
            mode="",
            amount="100",
            currency="EUR",
            platform="revolut",
            payee="alice",
        )
    )
    assert "mode is required" in payload["error"]
    assert payload["code"] == "VALIDATION"


def test_estimate_watch_withdraw_deposits(tools):
    kit, offramp = tools
    estimate = json.loads(
        kit.usdctofiat_estimate(mode="fast", amount="100", currency="EUR")
    )
    assert estimate["spread_bps"] == 0
    assert estimate["manager_fee_bps"] == 0
    assert estimate["mode"] == "fast"

    watched = json.loads(kit.usdctofiat_watch("42"))
    assert watched["snapshots"][0]["status"] == "ACTIVE"

    rows = json.loads(
        kit.usdctofiat_deposits("0x1111111111111111111111111111111111111111")
    )
    assert rows["deposits"][0]["id"] == "42"

    withdrawn = json.loads(kit.usdctofiat_withdraw("42"))
    assert withdrawn["to"].lower().endswith("ef")
    closed = json.loads(kit.usdctofiat_close("42"))
    assert closed["data"] == "0xwithdraw"


def test_estimate_mode_required(tools):
    kit, offramp = tools
    offramp.estimate.side_effect = ModeRequired()
    payload = json.loads(
        kit.usdctofiat_estimate(mode="slow", amount="100", currency="EUR")
    )
    assert "mode is required" in payload["error"]


def test_example_discloses_galleon_and_mode():
    text = (
        (
            Path(__file__).resolve().parents[2]
            / "examples"
            / "toolkits"
            / "usdctofiat_toolkit.py"
        )
        .read_text()
        .lower()
    )
    assert "usdctofiat by galleon labs" in text
    assert "usdctofiat.xyz/developers" in text
    assert "mode is required" in text
    assert "private key" in text
