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
from typing import Any, ClassVar, Dict, List, Optional, Tuple, Union
from urllib.parse import quote_plus, urlencode

import requests

from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool


class ZohoMailToolkit(BaseToolkit):
    r"""Zoho Mail Toolkit for CAMEL

    Args:
        access_token (str): OAuth access token used for API requests.
        account_id (str): Zoho Mail numeric account identifier.
        datacenter (str, optional): Datacenter key in {"com", "eu", "in",
            "au", "cn"}. (default: :obj:`"com"`)
    """

    # Map datacenter keys to accounts domain
    DC_MAP: ClassVar[Dict[str, str]] = {
        "com": "https://accounts.zoho.com",
        "eu": "https://accounts.zoho.eu",
        "in": "https://accounts.zoho.in",
        "au": "https://accounts.zoho.com.au",
        "cn": "https://accounts.zoho.com.cn",
    }

    # Map datacenter keys to mail API domain
    MAIL_DC_MAP: ClassVar[Dict[str, str]] = {
        "com": "https://mail.zoho.com",
        "eu": "https://mail.zoho.eu",
        "in": "https://mail.zoho.in",
        "au": "https://mail.zoho.com.au",
        "cn": "https://mail.zoho.com.cn",
    }

    def __init__(
        self, access_token: str, account_id: str, datacenter: str = "com"
    ):
        r"""
        Initialize toolkit with OAuth token and account context.

        Args:
            access_token (str): OAuth access token.

            account_id (str): Zoho Mail numeric account identifier.
            datacenter (str, optional): Datacenter key (default: :obj:`"com"`).
        """
        self.access_token = access_token
        self.account_id = account_id
        self.datacenter = datacenter
        self.base_url = self.MAIL_DC_MAP.get(
            datacenter, self.MAIL_DC_MAP["com"]
        )
        self.accounts_base = self.DC_MAP.get(
            datacenter, self.DC_MAP["com"]
        )  # accounts domain

    def _request_json(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        r"""HTTP JSON request with Zoho OAuth header.

        Args:
            method (str): HTTP method.
            url (str): URL to request.
            params (dict, optional): Query parameters.
            json (dict, optional): JSON body.
        """
        headers = {
            "Authorization": f"Zoho-oauthtoken {self.access_token}",
            "Content-Type": "application/json",
        }
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "error": str(e),
                "status_code": getattr(e.response, "status_code", None),
                "response": getattr(e.response, "text", None),
                "request_url": url,
                "request_params": params,
                "request_json": json,
            }

    def _resolve_folder_id(self, folder_id_or_name: str) -> Optional[str]:
        r"""Resolve human name like 'inbox' to folderId by listing folders.

        Args:
            folder_id_or_name (str): Folder name or ID.

        Returns:
            Optional[str]: Numeric folderId as string, or None if not found.
        """
        if folder_id_or_name and str(folder_id_or_name).isdigit():
            return str(folder_id_or_name)
        try:
            url = f"{self.base_url}/api/accounts/{self.account_id}/folders"
            resp = self._request_json("GET", url)
            items = (
                resp
                if isinstance(resp, list)
                else resp.get("data") or resp.get("folders") or []
            )
            target = str(folder_id_or_name).strip().lower()
            for f in items:
                if not isinstance(f, dict):
                    continue
                fid = f.get("folderId") or f.get("id") or f.get("folder_id")
                names = []
                for key in (
                    "folderName",
                    "displayName",
                    "name",
                    "systemFolder",
                    "folderType",
                    "type",
                ):
                    v = f.get(key)
                    if isinstance(v, str):
                        names.append(v.strip().lower())
                if target in names and fid is not None:
                    return str(fid)
            # Secondary: prefix match
            for f in items:
                if not isinstance(f, dict):
                    continue
                fid = f.get("folderId") or f.get("id")
                for key in ("folderName", "displayName", "name"):
                    v = f.get(key)
                    if (
                        isinstance(v, str)
                        and v.strip().lower().startswith(target)
                        and fid is not None
                    ):
                        return str(fid)
        except Exception:
            return None
        return None

    # ---------------
    # Accounts helper
    # ---------------
    @staticmethod
    def resolve_account_id_static(
        dc: str, token: str, identifier: str
    ) -> Tuple[str, str]:
        r"""Resolve a Zoho Mail numeric account id and a default from email.

        Args:
            dc (str): Datacenter key in {"com", "eu", "in", "au", "cn"}.
            token (str): OAuth access token.
            identifier (str): Numeric id or email address; empty to auto-pick.

        Returns:
            Tuple[str, str]: (account_id, default_from_email). Empty strings
                if not resolved.
        """
        base_map = {
            "com": "https://mail.zoho.com",
            "eu": "https://mail.zoho.eu",
            "in": "https://mail.zoho.in",
            "au": "https://mail.zoho.com.au",
            "cn": "https://mail.zoho.com.cn",
        }
        mail_base = base_map.get(dc, base_map["com"])  # default com
        try:
            resp = requests.get(
                f"{mail_base}/api/accounts",
                headers={"Authorization": f"Zoho-oauthtoken {token}"},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            items = (
                data
                if isinstance(data, list)
                else data.get("data") or data.get("accounts") or []
            )
            if not items:
                return "", ""
            # Numeric id check
            if identifier and identifier.isdigit():
                for acc in items:
                    acc_id = str(
                        acc.get("accountId")
                        or acc.get("id")
                        or acc.get("account_id")
                        or ""
                    )
                    if acc_id == identifier:
                        emails: List[str] = []
                        for key in (
                            "emailAddress",
                            "primaryEmailAddress",
                            "email",
                        ):
                            v = acc.get(key)
                            if isinstance(v, str):
                                emails.append(v)
                            elif isinstance(v, list):
                                emails.extend(
                                    [e for e in v if isinstance(e, str)]
                                )
                        return identifier, (emails[0] if emails else "")
            # Email match
            if identifier and "@" in identifier:
                target = identifier.lower()
                for acc in items:
                    candidate_emails: List[str] = []
                    for key in (
                        "emailAddress",
                        "primaryEmailAddress",
                        "email",
                    ):
                        v = acc.get(key)
                        if isinstance(v, str):
                            candidate_emails.append(v.lower())
                        elif isinstance(v, list):
                            for elem in v:
                                if isinstance(elem, str):
                                    candidate_emails.append(elem.lower())
                                elif isinstance(elem, dict):
                                    for k in ("email", "address", "value"):
                                        val = elem.get(k)
                                        if isinstance(val, str):
                                            candidate_emails.append(
                                                val.lower()
                                            )
                    if target in candidate_emails:
                        acc_id = str(
                            acc.get("accountId")
                            or acc.get("id")
                            or acc.get("account_id")
                            or ""
                        )
                        return acc_id, (
                            candidate_emails[0] if candidate_emails else ""
                        )
            # Fallback: first account
            acc = items[0]
            acc_id = str(
                acc.get("accountId")
                or acc.get("id")
                or acc.get("account_id")
                or ""
            )
            first_emails: List[str] = []
            for key in ("emailAddress", "primaryEmailAddress", "email"):
                v = acc.get(key)
                if isinstance(v, str):
                    first_emails.append(v)
                elif isinstance(v, list):
                    first_emails.extend([e for e in v if isinstance(e, str)])
            return acc_id, (first_emails[0] if first_emails else "")
        except requests.RequestException:
            return "", ""

    # ---------------
    # OAuth helpers
    # ---------------
    @staticmethod
    def build_authorize_url(
        *,
        client_type: str,
        client_id: str,
        scope: str,
        redirect_uri: Optional[str] = None,
        access_type: str = "offline",
        prompt: Optional[str] = "consent",
        state: Optional[str] = None,
        dc: str = "com",
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> str:
        r"""Build OAuth authorization URL for Zoho.

        Args:
            client_type (str): One of "server", "client", "mobile",
                "non-browser".
            client_id (str): OAuth client id.
            scope (str): Comma-separated scopes string.
            redirect_uri (str, optional): Redirect URI registered in Zoho.
            access_type (str, optional): "offline" or "online".
            prompt (str, optional): Consent prompt behavior.
            state (str, optional): Opaque state value.
            dc (str, optional): Datacenter key (default: :obj:`"com"`).
            extra_params (dict, optional): Extra query params to include.

        Returns:
            str: Fully qualified authorize URL.
        """
        if dc not in ZohoMailToolkit.DC_MAP:
            supported = list(ZohoMailToolkit.DC_MAP.keys())
            raise ValueError(
                f"Unknown datacenter '{dc}'. Supported: {supported}"
            )
        base = ZohoMailToolkit.DC_MAP[dc]

        response_type_map = {
            "server": "code",
            "client": "token",
            "mobile": "code",
            "non-browser": "code",
        }
        client_type_lower = client_type.lower()
        if client_type_lower not in response_type_map:
            raise ValueError(
                "Unsupported client_type. Use server|client|mobile|non-browser"
            )
        response_type = response_type_map[client_type_lower]
        if response_type in ("code", "token") and not redirect_uri:
            raise ValueError("redirect_uri is required for this client type")

        params: Dict[str, Any] = {
            "scope": scope,
            "client_id": client_id,
            "response_type": response_type,
            "redirect_uri": redirect_uri,
            "access_type": access_type,
        }
        if prompt:
            params["prompt"] = prompt
        if state:
            params["state"] = state
        if extra_params:
            params.update(extra_params)
        qs = urlencode(
            {k: v for k, v in params.items() if v is not None},
            doseq=True,
            quote_via=quote_plus,
        )
        return f"{base}/oauth/v2/auth?{qs}"

    def exchange_code_for_token(
        self,
        *,
        code: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scope: Optional[str] = None,
    ) -> Dict[str, Any]:
        r"""Exchange authorization code for access (and refresh) token.

        Args:
            code (str): Authorization code returned to the redirect URI.
            client_id (str): OAuth client id.
            client_secret (str): OAuth client secret.
            redirect_uri (str): Redirect URI used during authorization.
            scope (str, optional): Optional scopes to reiterate.

        Returns:
            Dict[str, Any]: Token response payload.
        """
        url = f"{self.accounts_base}/oauth/v2/token"
        params: Dict[str, Any] = {
            "code": code,
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
        }
        if scope:
            params["scope"] = scope
        return self._request_json("POST", url, params=params)

    def refresh_access_token(
        self,
        *,
        refresh_token: str,
        client_id: str,
        client_secret: str,
        scope: Optional[str] = None,
    ) -> Dict[str, Any]:
        r"""Refresh an access token via a refresh token.

        Args:
            refresh_token (str): Valid refresh token.
            client_id (str): OAuth client id.
            client_secret (str): OAuth client secret.
            scope (str, optional): Optional scopes to reiterate.

        Returns:
            Dict[str, Any]: Token response payload.
        """
        url = f"{self.accounts_base}/oauth/v2/token"
        params: Dict[str, Any] = {
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
        }
        if scope:
            params["scope"] = scope
        return self._request_json("POST", url, params=params)

    def revoke_token(self, token: str) -> Dict[str, Any]:
        r"""Revoke a refresh or access token.

        Args:
            token (str): Refresh or access token to revoke.

        Returns:
            Dict[str, Any]: Revocation status payload.
        """
        url = f"{self.accounts_base}/oauth/v2/token/revoke"
        params = {"token": token}
        resp = self._request_json("POST", url, params=params)
        if "error" not in resp:
            return {"status_code": 200, "ok": True}
        return resp

    def _join_recipients(
        self, recipients: Optional[Union[List[str], List[Dict[str, Any]]]]
    ) -> Optional[str]:
        r"""Convert list of recipients to comma-separated string per Zoho API.

        Args:
            recipients (Optional[Union[List[str], List[Dict[str, Any]]]]):
                List of recipients.

        Returns:
            Optional[str]: Comma-separated string of recipients.
        """
        if not recipients:
            return None
        emails: List[str] = []
        for recipient in recipients:
            if isinstance(recipient, str):
                emails.append(recipient)
            elif isinstance(recipient, dict) and recipient.get("email"):
                emails.append(str(recipient["email"]))
        return ",".join(emails) if emails else None

    # ---------------
    # Actions
    # ---------------

    def _add_recipients(
        self,
        payload: Dict[str, Any],
        *,
        to: Optional[Union[List[str], List[Dict[str, Any]]]] = None,
        cc: Optional[Union[List[str], List[Dict[str, Any]]]] = None,
        bcc: Optional[Union[List[str], List[Dict[str, Any]]]] = None,
    ) -> None:
        r"""Helper to append recipient fields to payload if present.

        Args:
            payload (Dict[str, Any]): Payload to append recipients to.
            to (Optional[Union[List[str], List[Dict[str, Any]]]]):
                To recipients.
            cc (Optional[Union[List[str], List[Dict[str, Any]]]]):
                CC recipients.
            bcc (Optional[Union[List[str], List[Dict[str, Any]]]]):
                BCC recipients.
        """
        to_str = self._join_recipients(to)
        if to_str:
            payload["toAddress"] = to_str
        cc_str = self._join_recipients(cc)
        if cc_str:
            payload["ccAddress"] = cc_str
        bcc_str = self._join_recipients(bcc)
        if bcc_str:
            payload["bccAddress"] = bcc_str

    def send_email(
        self,
        to: Union[List[str], List[Dict[str, Any]]],
        subject: str,
        content: str,
        from_email: Optional[str] = None,
        cc: Optional[Union[List[str], List[Dict[str, Any]]]] = None,
        bcc: Optional[Union[List[str], List[Dict[str, Any]]]] = None,
        is_html: bool = True,
        encoding: str = "UTF-8",
    ) -> Dict[str, Any]:
        r"""
        Action: Send Email (OAuth Scope: ZohoMail.messages)

        Args:
            to (Union[List[str], List[Dict[str, Any]]]):
                List of recipients (email strings or dicts with 'email').
            subject: Email subject
            content: Email content/body
            from_email: Sender email (optional, uses default if not provided)
            cc: CC recipients (optional)
            bcc: BCC recipients (optional)
            is_html: Whether content is HTML (default: True)
            encoding: Email encoding (default: UTF-8)

        Returns:
            API response as dictionary
        """
        url = f"{self.base_url}/api/accounts/{self.account_id}/messages"

        # Convert recipients to comma-separated string as required by
        # Zoho Mail API

        payload = {
            "fromAddress": from_email
            or f"noreply@{self.account_id.split('.')[0]}.zohomail.com",
            "subject": subject,
            "content": content,
            "mailFormat": "html" if is_html else "plaintext",
            "encoding": encoding,
        }

        self._add_recipients(payload, to=to, cc=cc, bcc=bcc)
        return self._request_json("POST", url, json=payload)

    def send_template_email(
        self,
        to: Union[List[str], List[Dict[str, Any]]],
        template_id: str,
        template_data: Optional[Dict[str, Any]] = None,
        from_email: Optional[str] = None,
        cc: Optional[Union[List[str], List[Dict[str, Any]]]] = None,
        bcc: Optional[Union[List[str], List[Dict[str, Any]]]] = None,
        subject: Optional[str] = None,
    ) -> Dict[str, Any]:
        r"""
        Action: Send Template Mail (OAuth Scope: ZohoMail.messages)

        Args:
            to (Union[List[str], List[Dict[str, Any]]]):
                List of recipients (EmailRecipient objects or email strings).
            template_id: Template ID to use
            template_data: Data to populate template variables (optional)
            from_email: Sender email (optional)
            cc: CC recipients (optional)
            bcc: BCC recipients (optional)
            subject: Email subject (optional, uses template default if
                not provided)

        Returns:
            API response as dictionary
        """
        url = f"{self.base_url}/api/accounts/{self.account_id}/messages"

        # Convert recipients to comma-separated string as required by
        # Zoho Mail API

        payload = {
            "fromAddress": from_email
            or f"noreply@{self.account_id.split('.')[0]}.zohomail.com",
            "templateId": template_id,
            "mailFormat": "html",
        }

        self._add_recipients(payload, to=to, cc=cc, bcc=bcc)
        if subject:
            payload["subject"] = subject
        if template_data:
            payload["templateData"] = template_data
        return self._request_json("POST", url, json=payload)

    def create_draft(
        self,
        to: Union[List[str], List[Dict[str, Any]]],
        subject: str,
        content: str,
        from_email: Optional[str] = None,
        cc: Optional[Union[List[str], List[Dict[str, Any]]]] = None,
        bcc: Optional[Union[List[str], List[Dict[str, Any]]]] = None,
        is_html: bool = True,
        encoding: str = "UTF-8",
        mode: str = "draft",
    ) -> Dict[str, Any]:
        r"""
        Action: Create Draft (OAuth Scope: ZohoMail.messages)

        Args:
            to: List of recipients (EmailRecipient objects or email strings)
            subject: Email subject
            content: Email content/body
            from_email: Sender email (optional)
            cc: CC recipients (optional)
            bcc: BCC recipients (optional)
            is_html: Whether content is HTML (default: True)
            encoding: Email encoding (default: UTF-8)

        Returns:
            API response as dictionary
        """
        url = f"{self.base_url}/api/accounts/{self.account_id}/messages"

        # Convert recipients to comma-separated string as required by
        # Zoho Mail API

        payload: Dict[str, Any] = {
            "mode": "template" if str(mode).lower() == "template" else "draft",
            "subject": subject,
            "content": content,
            "mailFormat": "html" if is_html else "plaintext",
        }
        # Only include fromAddress if explicitly provided (some orgs
        # restrict this field)
        if from_email:
            payload["fromAddress"] = from_email
        # Encoding is optional; include only if explicitly set
        if encoding:
            payload["encoding"] = encoding
        self._add_recipients(payload, to=to, cc=cc, bcc=bcc)
        return self._request_json("POST", url, json=payload)

    def create_folder(
        self, name: str, parent_id: Optional[Union[str, int]] = None
    ) -> Dict[str, Any]:
        r"""
        Action: Create Folder (OAuth Scope: ZohoMail.messages)

        Args:
            name (str): Folder name.
            parent_id (Optional[Union[str, int]]): Parent folder ID (optional).
        """
        url = f"{self.base_url}/api/accounts/{self.account_id}/folders"
        payload: Dict[str, Any] = {"folderName": name}
        if parent_id is not None:
            payload["parentId"] = str(parent_id)
        return self._request_json("POST", url, json=payload)

    def create_tag(
        self, name: str, color: Optional[str] = None
    ) -> Dict[str, Any]:
        r"""Action: Create Tag (OAuth Scope: ZohoMail.labels)

        Creates a tag/label for emails.
        """
        url = f"{self.base_url}/api/accounts/{self.account_id}/labels"
        # Per API, expected keys are displayName (required) and optional
        # color (hex)
        payload: Dict[str, Any] = {"displayName": name}
        if color:
            payload["color"] = color
        return self._request_json("POST", url, json=payload)

    def create_task(
        self,
        title: str,
        description: Optional[str] = None,
        due_in_epoch_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        r"""Action: Create Task (OAuth Scope: ZohoMail.tasks )

        Creates a task in Zoho Mail Tasks.
        """
        url = f"{self.base_url}/api/accounts/{self.account_id}/tasks"
        payload: Dict[str, Any] = {"title": title}
        if description:
            payload["description"] = description
        if due_in_epoch_ms is not None:
            payload["dueDateInMillis"] = int(due_in_epoch_ms)
        return self._request_json("POST", url, json=payload)

    # ---------------
    # Triggers (Polling)
    # ---------------
    def trigger_new_email_poll(
        self,
        folder_id: str,
        since_epoch_seconds: Optional[int] = None,
        limit: int = 20,
        sort_order: str = "desc",
    ) -> Dict[str, Any]:
        r"""Trigger: New Email (Polling)

        Retrieves recent emails from a folder. Optionally filter
        client-side using since_epoch_seconds.

        Args:
            folder_id (str): Folder ID.
            since_epoch_seconds (Optional[int]): Since epoch seconds.
            limit (int): Limit.
            sort_order (str): Sort order.
        """
        url = f"{self.base_url}/api/accounts/{self.account_id}/messages/view"
        resolved_folder_id = self._resolve_folder_id(folder_id)
        # Zoho expects sortorder boolean: true (asc), false (desc).
        # Default start is 1.
        params: Dict[str, Any] = {
            "folderId": resolved_folder_id or folder_id,
            "start": 1,
            "limit": limit,
            "sortorder": True
            if str(sort_order).lower() in ("asc", "true", "1")
            else False,
            "sortBy": "date",
        }
        resp = self._request_json("GET", url, params=params)
        if (
            since_epoch_seconds
            and isinstance(resp, dict)
            and isinstance(resp.get("data"), list)
        ):
            threshold_ms = int(since_epoch_seconds) * 1000
            filtered = [
                m
                for m in resp["data"]
                if isinstance(m, dict)
                and int(m.get("receivedTimeInMillis", 0)) >= threshold_ms
            ]
            resp = {**resp, "data": filtered}
        return resp

    def trigger_new_email_matching_search_poll(
        self,
        query: str,
        folder_id: Optional[str] = None,
        start: int = 1,
        limit: int = 20,
        include_to: bool = False,
        received_time_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        r"""Trigger: New Email Matching Search (Polling)

        Retrieves emails based on a search query.

        Args:
            query (str): Search query.
            folder_id (Optional[str]): Folder ID.
            start (int): Start.
            limit (int): Limit.
            include_to (bool): Include to.
            received_time_ms (Optional[int]): Received time milliseconds.
        """
        url = f"{self.base_url}/api/accounts/{self.account_id}/messages/search"
        # Zoho expects 'searchKey' instead of 'query'.
        params: Dict[str, Any] = {
            "searchKey": query,
            "start": start,
            "limit": limit,
        }
        if include_to:
            params["includeto"] = True
        if received_time_ms is not None:
            params["receivedTime"] = int(received_time_ms)
        # Note: folderId is not supported in search API; omit to avoid
        # EXTRA_PARAM_FOUND
        return self._request_json("GET", url, params=params)

    def trigger_new_tagged_email_poll(
        self,
        tag_id: Union[str, int],
        folder_id: Optional[str] = None,
        start: int = 0,
        limit: int = 20,
    ) -> Dict[str, Any]:
        r"""Trigger: New Tagged Email (Polling)

        Retrieves emails that have the specified tag/label.

        Args:
            tag_id (Union[str, int]): Tag ID.
            folder_id (Optional[str]): Folder ID.
            start (int): Start.
            limit (int): Limit.

        Returns:
            API response as dictionary
        """
        # Use search with label filter if available; fallback to folder
        # filter plus client-side tag check if needed
        url = f"{self.base_url}/api/accounts/{self.account_id}/messages/search"
        query = f"label:{tag_id}"
        params: Dict[str, Any] = {
            "query": query,
            "start": start,
            "limit": limit,
        }
        if folder_id:
            resolved_folder_id = self._resolve_folder_id(folder_id)
            params["folderId"] = resolved_folder_id or folder_id
        return self._request_json("GET", url, params=params)

    def get_tools(self) -> List[FunctionTool]:
        return [
            FunctionTool(self.send_email),
            FunctionTool(self.send_template_email),
            FunctionTool(self.create_draft),
            FunctionTool(self.create_folder),
            FunctionTool(self.create_tag),
            FunctionTool(self.create_task),
            FunctionTool(self.trigger_new_email_poll),
            FunctionTool(self.trigger_new_email_matching_search_poll),
            FunctionTool(self.trigger_new_tagged_email_poll),
        ]
