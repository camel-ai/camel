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
from typing import Any, Dict, List, Optional, Union

from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.utils import MCPServer, api_keys_required


def _response_to_dict(obj: Any) -> Any:
    r"""Recursively converts a Plivo SDK response object into plain data."""
    if isinstance(obj, list):
        return [_response_to_dict(item) for item in obj]
    if hasattr(obj, "__dict__"):
        return {k: _response_to_dict(v) for k, v in vars(obj).items()}
    return obj


@MCPServer()
class PlivoToolkit(BaseToolkit):
    r"""A class representing a toolkit for Plivo communication operations.

    This toolkit provides methods to interact with the Plivo API, allowing
    agents to send SMS messages, place voice calls, run OTP verification
    sessions, and look up phone number information.

    Notes:
        To use this toolkit, set the following environment variables (or pass
        them to the constructor):
        - PLIVO_AUTH_ID: Your Plivo Auth ID.
        - PLIVO_AUTH_TOKEN: Your Plivo Auth Token.
        Both are available from the Plivo console at https://cx.plivo.com.
    """

    @api_keys_required(
        [
            ("auth_id", "PLIVO_AUTH_ID"),
            ("auth_token", "PLIVO_AUTH_TOKEN"),
        ]
    )
    def __init__(
        self,
        auth_id: Optional[str] = None,
        auth_token: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        r"""Initializes the PlivoToolkit.

        Args:
            auth_id (Optional[str]): The Plivo Auth ID. If not provided, it is
                read from the PLIVO_AUTH_ID environment variable.
                (default: :obj:`None`)
            auth_token (Optional[str]): The Plivo Auth Token. If not provided,
                it is read from the PLIVO_AUTH_TOKEN environment variable.
                (default: :obj:`None`)
            timeout (Optional[float]): The timeout for API requests.
                (default: :obj:`None`)
        """
        super().__init__(timeout=timeout)
        try:
            import plivo
        except ImportError:
            raise ImportError(
                "Please install the plivo package first. "
                "You can install it by running `pip install plivo`."
            )
        self.client = plivo.RestClient(
            auth_id=auth_id or os.environ.get("PLIVO_AUTH_ID"),
            auth_token=auth_token or os.environ.get("PLIVO_AUTH_TOKEN"),
        )

    def send_sms(
        self, from_number: str, to_number: str, message: str
    ) -> Union[Dict[str, Any], str]:
        r"""Sends an SMS message to one or more recipients.

        Args:
            from_number (str): The sender ID in E.164 format, e.g.
                ``+14150000002``. Must be a Plivo number or approved sender ID.
            to_number (str): The recipient in E.164 format. Multiple recipients
                are joined with ``<``, e.g. ``+14150000001<+14150000003``.
            message (str): The text body of the message.

        Returns:
            Union[Dict[str, Any], str]: A dictionary with the queued
                ``message_uuid`` list and ``api_id`` if successful, or an error
                message string if failed. A successful response means the
                message was queued, not yet delivered.
        """
        try:
            response = self.client.messages.create(
                src=from_number,
                dst=to_number,
                text=message,
            )
            return {
                "message": response.message,
                "message_uuid": response.message_uuid,
                "api_id": response.api_id,
            }
        except Exception as e:
            return f"Failed to send SMS: {e!s}"

    def make_call(
        self,
        from_number: str,
        to_number: str,
        answer_url: str,
        answer_method: str = "POST",
    ) -> Union[Dict[str, Any], str]:
        r"""Places an outbound voice call.

        Args:
            from_number (str): The caller ID in E.164 format, e.g.
                ``+14150000002``.
            to_number (str): The destination number in E.164 format.
            answer_url (str): A publicly reachable URL that Plivo fetches when
                the call is answered; it must return Plivo call-flow XML.
            answer_method (str): The HTTP method Plivo uses to fetch the answer
                URL, either ``GET`` or ``POST``. Use ``GET`` for a static file
                such as the Plivo demo answer XML. (default: :obj:`"POST"`)

        Returns:
            Union[Dict[str, Any], str]: A dictionary with the ``request_uuid``
                and ``api_id`` if the call was fired, or an error message
                string if failed.
        """
        method = answer_method.upper()
        if method not in ("GET", "POST"):
            return "Failed to make call: answer_method must be GET or POST"
        try:
            response = self.client.calls.create(
                from_=from_number,
                to_=to_number,
                answer_url=answer_url,
                answer_method=method,
            )
            return {
                "message": response.message,
                "request_uuid": response.request_uuid,
                "api_id": response.api_id,
            }
        except Exception as e:
            return f"Failed to make call: {e!s}"

    def send_otp(
        self, recipient: str, channel: str = "sms"
    ) -> Union[Dict[str, Any], str]:
        r"""Starts a Plivo Verify session that sends a one-time passcode.

        Args:
            recipient (str): The recipient's number in E.164 format.
            channel (str): The delivery channel, either ``sms`` or ``voice``.
                (default: :obj:`"sms"`)

        Returns:
            Union[Dict[str, Any], str]: A dictionary with the ``session_uuid``
                (needed to validate the code later) and ``api_request_id`` if
                successful, or an error message string if failed.
        """
        try:
            response = self.client.verify_session.create(
                recipient=recipient,
                channel=channel,
            )
            return {
                "session_uuid": response.session_uuid,
                "api_request_id": getattr(response, "api_request_id", None),
            }
        except Exception as e:
            return f"Failed to send OTP: {e!s}"

    def verify_otp(
        self, session_uuid: str, otp: str
    ) -> Union[Dict[str, Any], str]:
        r"""Validates the code a user entered against a Verify session.

        Args:
            session_uuid (str): The session UUID returned by
                :meth:`send_otp`. The code is validated against this session,
                not the phone number.
            otp (str): The one-time passcode the user provided.

        Returns:
            Union[Dict[str, Any], str]: A dictionary with a boolean
                ``verified`` flag and the raw ``message`` if the request
                succeeded, or an error message string if failed. ``verified``
                is True only when Plivo reports the session as validated; a
                non-success message is treated as not verified.
        """
        try:
            response = self.client.verify_session.validate(
                session_uuid=session_uuid,
                otp=otp,
            )
            result_message = getattr(response, "message", "") or ""
            verified = (
                "session validated successfully" in result_message.lower()
            )
            return {"verified": verified, "message": result_message}
        except Exception as e:
            return f"Failed to verify OTP: {e!s}"

    def lookup_number(self, number: str) -> Union[Dict[str, Any], str]:
        r"""Looks up carrier, line type, and formatting for a phone number.

        Args:
            number (str): The phone number to look up, in E.164 format, e.g.
                ``+14151234567``.

        Returns:
            Union[Dict[str, Any], str]: A dictionary with the ``country``,
                ``format``, and ``carrier`` details (``carrier.type`` is one
                of ``landline`` / ``mobile`` / ``voip``) if successful, or an
                error message string if failed. Carrier fields are best-effort
                and may be sparse for unallocated numbers.
        """
        try:
            response = self.client.lookup.get(number)
            return _response_to_dict(response)
        except Exception as e:
            return f"Failed to look up number: {e!s}"

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects for the
                toolkit methods.
        """
        return [
            FunctionTool(self.send_sms),
            FunctionTool(self.make_call),
            FunctionTool(self.send_otp),
            FunctionTool(self.verify_otp),
            FunctionTool(self.lookup_number),
        ]
