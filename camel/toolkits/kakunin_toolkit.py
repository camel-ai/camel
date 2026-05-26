"""
kakunin_toolkit.py — Kakunin compliance toolkit for CAMEL-AI

Intended PR target: camel-ai/camel at camel/toolkits/kakunin_toolkit.py

Provides KakuninToolkit(BaseToolkit) with four FunctionTools:
  - verify_agent_certificate
  - check_agent_scope
  - get_risk_score
  - emit_behavior_event

No kakunin SDK dependency — calls the Kakunin REST API directly via httpx.

Install extras: pip install camel-ai httpx
"""

from __future__ import annotations

from typing import Any

import httpx

try:
    from camel.toolkits import BaseToolkit, FunctionTool
    from camel.toolkits.base import OpenAIFunction
except ImportError as e:
    raise ImportError(
        "camel-ai is required: pip install camel-ai"
    ) from e


_DEFAULT_BASE = "https://api.kakunin.ai/v1"


class KakuninToolkit(BaseToolkit):
    """
    CAMEL toolkit for Kakunin AI agent compliance infrastructure.

    Kakunin issues X.509 certificates to AI agents, monitors behavioral
    risk in real-time, and produces MiCA / EU AI Act audit trails.

    Args:
        api_key: Kakunin API key (``kak_live_...`` or ``kak_test_...``).
        base_url: Override the API base URL (defaults to production).
        timeout: HTTP timeout in seconds (default 10).

    Example::

        from camel.agents import ChatAgent
        from camel.models import ModelFactory
        from camel.toolkits.kakunin_toolkit import KakuninToolkit

        toolkit = KakuninToolkit(api_key="kak_live_...")
        agent = ChatAgent(model=model, tools=toolkit.get_tools())
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = _DEFAULT_BASE,
        timeout: float = 10.0,
    ) -> None:
        super().__init__()
        self._api_key = api_key
        self._base = base_url.rstrip("/")
        self._timeout = timeout

    # ── private HTTP helper ─────────────────────────────────────────────────

    def _get(self, path: str) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self._api_key}"}
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.get(f"{self._base}{path}", headers=headers)
            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(f"{self._base}{path}", json=body, headers=headers)
            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]

    # ── tools ───────────────────────────────────────────────────────────────

    def verify_agent_certificate(self, agent_id: str) -> dict[str, Any]:
        """
        Verify the X.509 certificate of an AI agent.

        Returns certificate status, active scope permissions, expiry date,
        and revocation history. Use this before trusting an agent's claims.

        Args:
            agent_id (str): Kakunin agent ID (e.g. ``agt-abc123``).

        Returns:
            dict: certificate_status, scopes, valid_until, serial_number.
        """
        # Public verify endpoint — no auth required
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.get(f"https://api.kakunin.ai/v1/verify/{agent_id}")
            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]

    def check_agent_scope(self, agent_id: str, action: str) -> dict[str, Any]:
        """
        Check whether a specific action is within an agent's permitted scope.

        Args:
            agent_id (str): Kakunin agent ID.
            action (str): Action to check (e.g. ``trade.execute``, ``data.write``).

        Returns:
            dict: allowed (bool), action, permitted_scopes list.
        """
        data = self._get(f"/agents/{agent_id}")
        permitted: list[str] = (data.get("metadata") or {}).get("scopes", [])
        return {
            "agent_id": agent_id,
            "action": action,
            "allowed": action in permitted,
            "permitted_scopes": permitted,
        }

    def get_risk_score(self, agent_id: str) -> dict[str, Any]:
        """
        Return the current behavioral risk score for an AI agent.

        Risk bands: low (<0.3) · medium (>=0.3) · high (>=0.75) ·
        critical (>=0.85, auto-revocation threshold).

        Args:
            agent_id (str): Kakunin agent ID.

        Returns:
            dict: score (0.0–1.0), band, agent_id.
        """
        data = self._get(f"/agents/{agent_id}")
        score: float = (data.get("metadata") or {}).get("risk_score", 0.0)
        if score >= 0.85:
            band = "critical"
        elif score >= 0.75:
            band = "high"
        elif score >= 0.3:
            band = "medium"
        else:
            band = "low"
        return {"agent_id": agent_id, "score": score, "band": band}

    def emit_behavior_event(
        self,
        agent_id: str,
        action_type: str,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Emit a behavioral event for an AI agent to Kakunin's audit trail.

        Valid action_type values: api_call, authentication_attempt,
        authentication_failure, data_access, data_mutation,
        transaction_initiated, transaction_anomaly,
        unauthorized_access_attempt, message_signed,
        message_verification_failed.

        Args:
            agent_id (str): Kakunin agent ID.
            action_type (str): One of the canonical Kakunin event types.
            details (dict, optional): Extra context to store with the event.

        Returns:
            dict: event_id, agent_id, action_type.
        """
        result = self._post(
            "/events",
            {"agent_id": agent_id, "action_type": action_type, "details": details or {}},
        )
        return {
            "event_id": result.get("id"),
            "agent_id": agent_id,
            "action_type": action_type,
        }

    # ── BaseToolkit protocol ────────────────────────────────────────────────

    def get_tools(self) -> list[FunctionTool]:
        """Return CAMEL FunctionTool objects for all four Kakunin operations."""
        return [
            FunctionTool(self.verify_agent_certificate),
            FunctionTool(self.check_agent_scope),
            FunctionTool(self.get_risk_score),
            FunctionTool(self.emit_behavior_event),
        ]
