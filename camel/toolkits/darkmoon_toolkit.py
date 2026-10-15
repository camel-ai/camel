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
import os
import time
from typing import Any
from urllib.parse import quote

import httpx

from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit, manual_timeout
from camel.utils import MCPServer, api_keys_required

logger = get_logger(__name__)

_TERMINAL_EVENTS = frozenset({"run_completed", "run_error"})
_DEFAULT_REQUEST_TIMEOUT = 60.0


class DarkmoonAPIError(Exception):
    r"""Raised when the Darkmoon Dashboard API rejects or fails a call."""


@MCPServer()
class DarkmoonToolkit(BaseToolkit):
    r"""A class representing a toolkit for Darkmoon penetration testing.

    `Darkmoon <https://github.com/ASCIT31/Dark-Moon>`_ is a self-hosted
    autonomous AI penetration testing platform. This toolkit lets an agent
    start a Darkmoon campaign against a target you are authorised to test,
    list campaigns, and read back the findings (vulnerabilities and severity
    statistics) that Darkmoon recorded.

    Notes:
        - The toolkit talks to the Darkmoon Dashboard API of an instance you
          operate yourself (there is no public hosted endpoint). It logs in
          with ``POST /api/v1/auth/login`` and reuses the returned JWT.
        - The Darkmoon engine and CLI are open source (GPL-3.0); the Dashboard
          API used here is part of the Pro edition. Darkmoon's Pro
          remediation-to-pull-request feature is intentionally not exposed.
        - Only run assessments against systems you own or are explicitly
          authorised to test. Findings can include false positives and must
          be reviewed by a human.
        - Set DARKMOON_BASE_URL, DARKMOON_USERNAME and DARKMOON_PASSWORD (or
          pass them to the constructor).
    """

    @api_keys_required(
        [
            ("base_url", "DARKMOON_BASE_URL"),
            ("username", "DARKMOON_USERNAME"),
            ("password", "DARKMOON_PASSWORD"),
        ]
    )
    def __init__(
        self,
        base_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        timeout: float | None = None,
    ):
        r"""Initializes the DarkmoonToolkit.

        Args:
            base_url (Optional[str]): Base URL of the Darkmoon Dashboard API,
                e.g. ``http://localhost:8000``. If not provided, it is read
                from the DARKMOON_BASE_URL environment variable.
                (default: :obj:`None`)
            username (Optional[str]): The dashboard username. If not provided,
                it is read from the DARKMOON_USERNAME environment variable.
                (default: :obj:`None`)
            password (Optional[str]): The dashboard password. If not provided,
                it is read from the DARKMOON_PASSWORD environment variable.
                (default: :obj:`None`)
            timeout (Optional[float]): The timeout in seconds for each API
                request. (default: :obj:`None`, which uses 60 seconds)
        """
        super().__init__(timeout=timeout)
        self._base_url = str(
            base_url or os.environ.get("DARKMOON_BASE_URL")
        ).rstrip("/")
        self._username = str(username or os.environ.get("DARKMOON_USERNAME"))
        self._password = str(password or os.environ.get("DARKMOON_PASSWORD"))
        self._client = httpx.Client(
            timeout=timeout or _DEFAULT_REQUEST_TIMEOUT
        )
        self._token: str | None = None

    def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        authenticated: bool = True,
    ) -> Any:
        r"""Sends one request to the Darkmoon Dashboard API.

        Raises:
            DarkmoonAPIError: If the request fails or the API returns an
                error status. The message never contains credentials.
        """
        headers = {"Content-Type": "application/json"}
        if authenticated:
            headers["Authorization"] = f"Bearer {self._login()}"
        try:
            response = self._client.request(
                method, f"{self._base_url}{path}", headers=headers, json=body
            )
        except httpx.HTTPError as e:
            raise DarkmoonAPIError(f"request failed: {e!s}") from e
        try:
            payload: Any = response.json()
        except ValueError:
            payload = response.text
        if response.status_code >= 400:
            detail = (
                payload.get("detail") if isinstance(payload, dict) else None
            )
            raise DarkmoonAPIError(
                f"API error {response.status_code}: "
                f"{detail if isinstance(detail, str) and detail else 'failed'}"
            )
        return payload

    def _login(self) -> str:
        r"""Logs in once and caches the JWT for later calls."""
        if self._token:
            return self._token
        payload = self._request(
            "POST",
            "/api/v1/auth/login",
            {"username": self._username, "password": self._password},
            authenticated=False,
        )
        token = payload.get("token") if isinstance(payload, dict) else None
        if not token:
            raise DarkmoonAPIError("login did not return a token")
        self._token = str(token)
        return self._token

    def _campaigns(self) -> list[dict[str, Any]]:
        r"""Returns the raw campaign list."""
        payload = self._request("GET", "/api/v1/campaigns")
        data = payload.get("data") if isinstance(payload, dict) else None
        return data if isinstance(data, list) else []

    def _findings(self, campaign_id: str) -> dict[str, Any]:
        r"""Returns the findings and severity statistics of a campaign."""
        payload = self._request(
            "GET",
            "/api/v1/vulnerabilities"
            f"?campaign_id={quote(campaign_id, safe='')}",
        )
        body = payload if isinstance(payload, dict) else {}
        return {
            "campaign_id": campaign_id,
            "total": body.get("total") or 0,
            "stats": body.get("stats") or {},
            "findings": body.get("data") or [],
        }

    def darkmoon_list_campaigns(self) -> dict[str, Any] | str:
        r"""Lists the Darkmoon campaigns visible to the dashboard user.

        Returns:
            Union[Dict[str, Any], str]: A dictionary with the ``total`` count
                and the ``campaigns`` list (each with its id) if successful,
                or an error message string if failed.
        """
        try:
            campaigns = self._campaigns()
            return {"total": len(campaigns), "campaigns": campaigns}
        except DarkmoonAPIError as e:
            return f"Failed to list Darkmoon campaigns: {e!s}"

    def darkmoon_get_findings(self, campaign_id: str) -> dict[str, Any] | str:
        r"""Returns the findings Darkmoon recorded for a campaign.

        Findings may contain false positives and need human review.

        Args:
            campaign_id (str): The Darkmoon campaign id, e.g.
                ``camp_20260922_abc123``. Use `darkmoon_list_campaigns` to
                discover ids.

        Returns:
            Union[Dict[str, Any], str]: A dictionary with ``campaign_id``,
                ``total``, severity ``stats`` and the ``findings`` list if
                successful, or an error message string if failed.
        """
        campaign_id = (campaign_id or "").strip()
        if not campaign_id:
            return "Failed to get Darkmoon findings: campaign_id is required"
        try:
            return self._findings(campaign_id)
        except DarkmoonAPIError as e:
            return f"Failed to get Darkmoon findings: {e!s}"

    @manual_timeout
    def darkmoon_run_pentest(
        self,
        target: str,
        wait_for_completion: bool = True,
        program: str | None = None,
        focus: str | None = None,
        severity: str | None = None,
        max_wait_seconds: int = 1800,
        poll_interval_seconds: float = 5.0,
    ) -> dict[str, Any] | str:
        r"""Starts an autonomous Darkmoon pentest against one target.

        Only use targets you own or are explicitly authorised to test. A run
        can take many minutes; when ``wait_for_completion`` is true this
        method polls the run log until it finishes (or ``max_wait_seconds``
        elapses) and then returns the findings of the campaign created by
        this run.

        Args:
            target (str): The host, URL or scope to assess.
            wait_for_completion (bool): Whether to wait for the run to finish
                and return its findings. If false, only the run id is
                returned. (default: :obj:`True`)
            program (Optional[str]): An optional program name or rules of
                engagement note. (default: :obj:`None`)
            focus (Optional[str]): Optional comma separated focus areas, e.g.
                ``"auth, injection"``. (default: :obj:`None`)
            severity (Optional[str]): Optional minimum severity to report.
                (default: :obj:`None`)
            max_wait_seconds (int): Maximum seconds to wait for the run when
                ``wait_for_completion`` is true. (default: :obj:`1800`)
            poll_interval_seconds (float): Seconds between run status checks.
                (default: :obj:`5.0`)

        Returns:
            Union[Dict[str, Any], str]: With ``wait_for_completion`` false, a
                dictionary with ``status`` and ``run_id``. Otherwise a
                dictionary with ``run_id``, ``campaign_id``, ``timed_out``,
                ``total``, ``stats`` and ``findings``. An error message
                string is returned if failed.
        """
        target = (target or "").strip()
        if not target:
            return "Failed to run Darkmoon pentest: target is required"

        params: dict[str, Any] = {"target": target}
        if program and program.strip():
            params["program"] = program.strip()
        areas = [p.strip() for p in (focus or "").split(",") if p.strip()]
        if areas:
            params["focus"] = areas
        if severity and severity.strip():
            params["severity"] = severity.strip()

        try:
            known_ids = {c.get("id") for c in self._campaigns()}
            handle = self._request("POST", "/api/v1/run/campaign", params)
            run_id = handle.get("run_id") if isinstance(handle, dict) else None
            if not run_id:
                raise DarkmoonAPIError("no run id returned")
            if not wait_for_completion:
                return {
                    "status": "started",
                    "run_id": run_id,
                    "target": target,
                }

            timed_out = self._wait_for_run(
                str(run_id), max_wait_seconds, poll_interval_seconds
            )
            campaign = self._resolve_campaign(known_ids, target)
            result: dict[str, Any] = {
                "run_id": run_id,
                "campaign_id": campaign.get("id") if campaign else None,
                "timed_out": timed_out,
                "total": 0,
                "stats": {},
                "findings": [],
            }
            if campaign and campaign.get("id"):
                result.update(self._findings(str(campaign["id"])))
                result["run_id"] = run_id
                result["timed_out"] = timed_out
            return result
        except DarkmoonAPIError as e:
            return f"Failed to run Darkmoon pentest: {e!s}"

    def _wait_for_run(
        self, run_id: str, max_wait_seconds: int, poll_interval: float
    ) -> bool:
        r"""Polls the run log until a terminal event.

        Returns:
            bool: True if the wait timed out.
        """
        deadline = time.monotonic() + max_wait_seconds
        path = f"/api/v1/run/logs/{quote(run_id, safe='')}"
        while True:
            try:
                payload = self._request("GET", path)
            except DarkmoonAPIError as e:
                # The log does not exist until the run writes its first event.
                if "404" not in str(e):
                    raise
                payload = {}
            events = payload.get("data") if isinstance(payload, dict) else None
            if any(
                isinstance(ev, dict) and ev.get("type") in _TERMINAL_EVENTS
                for ev in events or []
            ):
                return False
            if time.monotonic() >= deadline:
                return True
            time.sleep(poll_interval)

    def _resolve_campaign(
        self, known_ids: set, target: str
    ) -> dict[str, Any] | None:
        r"""Finds the campaign created by this run.

        The trigger endpoint returns a run id only, so only campaigns that did
        not exist before the run are considered; a stale campaign is never
        reported as the result of this run.
        """
        fresh = [c for c in self._campaigns() if c.get("id") not in known_ids]
        if not fresh:
            return None
        fresh.sort(key=lambda c: str(c.get("date") or ""), reverse=True)
        host = target.lower()
        for campaign in fresh:
            if host in str(campaign.get("id", "")).lower():
                return campaign
        return fresh[0]

    def get_tools(self) -> list[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects for the
                toolkit methods.
        """
        return [
            FunctionTool(self.darkmoon_run_pentest),
            FunctionTool(self.darkmoon_get_findings),
            FunctionTool(self.darkmoon_list_campaigns),
        ]
