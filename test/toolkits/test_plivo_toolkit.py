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
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from camel.toolkits.plivo_toolkit import PlivoToolkit


@pytest.fixture
def plivo_toolkit():
    with patch("plivo.RestClient"):
        return PlivoToolkit(auth_id="test-auth-id", auth_token="test-token")


def test_init_missing_credentials(monkeypatch):
    monkeypatch.delenv("PLIVO_AUTH_ID", raising=False)
    monkeypatch.delenv("PLIVO_AUTH_TOKEN", raising=False)

    with pytest.raises(ValueError):
        PlivoToolkit()


def test_send_sms_success(plivo_toolkit):
    plivo_toolkit.client.messages.create.return_value = SimpleNamespace(
        message="message(s) queued",
        message_uuid=["5b40a428-bfc7-4daf-9d06-726c558bf3b8"],
        api_id="948b53a2-3f08-11e7-b6f4-061564b78b75",
    )

    result = plivo_toolkit.send_sms(
        from_number="+14150000002",
        to_number="+14150000001",
        message="hello",
    )

    assert result == {
        "message": "message(s) queued",
        "message_uuid": ["5b40a428-bfc7-4daf-9d06-726c558bf3b8"],
        "api_id": "948b53a2-3f08-11e7-b6f4-061564b78b75",
    }
    plivo_toolkit.client.messages.create.assert_called_once_with(
        src="+14150000002",
        dst="+14150000001",
        text="hello",
    )


def test_send_sms_failure(plivo_toolkit):
    plivo_toolkit.client.messages.create.side_effect = Exception("API Error")

    result = plivo_toolkit.send_sms(
        from_number="+14150000002",
        to_number="+14150000001",
        message="hello",
    )

    assert result == "Failed to send SMS: API Error"


def test_make_call_success(plivo_toolkit):
    plivo_toolkit.client.calls.create.return_value = SimpleNamespace(
        message="call fired",
        request_uuid="9834029e-58b6-11e1-b8b7-a5bd0e4e126f",
        api_id="97ceeb52-58b6-11e1-86da-77300b68f8bb",
    )

    result = plivo_toolkit.make_call(
        from_number="+14150000002",
        to_number="+14150000001",
        answer_url="https://example.com/answer",
    )

    assert result == {
        "message": "call fired",
        "request_uuid": "9834029e-58b6-11e1-b8b7-a5bd0e4e126f",
        "api_id": "97ceeb52-58b6-11e1-86da-77300b68f8bb",
    }
    plivo_toolkit.client.calls.create.assert_called_once_with(
        from_="+14150000002",
        to_="+14150000001",
        answer_url="https://example.com/answer",
        answer_method="POST",
    )


def test_make_call_get_method(plivo_toolkit):
    plivo_toolkit.client.calls.create.return_value = SimpleNamespace(
        message="call fired", request_uuid="req", api_id="api"
    )

    plivo_toolkit.make_call(
        from_number="+14150000002",
        to_number="+14150000001",
        answer_url="https://s3.amazonaws.com/static.plivo.com/answer.xml",
        answer_method="get",
    )

    plivo_toolkit.client.calls.create.assert_called_once_with(
        from_="+14150000002",
        to_="+14150000001",
        answer_url="https://s3.amazonaws.com/static.plivo.com/answer.xml",
        answer_method="GET",
    )


def test_make_call_rejects_bad_method(plivo_toolkit):
    result = plivo_toolkit.make_call(
        from_number="+14150000002",
        to_number="+14150000001",
        answer_url="https://example.com/answer",
        answer_method="DELETE",
    )

    assert "GET or POST" in result
    plivo_toolkit.client.calls.create.assert_not_called()


def test_send_otp_success(plivo_toolkit):
    plivo_toolkit.client.verify_session.create.return_value = SimpleNamespace(
        session_uuid="adsdafkjadshf123123",
        api_request_id="c1a2b3d4-0000-1111-2222-333344445555",
    )

    result = plivo_toolkit.send_otp(recipient="+14150000001")

    assert result == {
        "session_uuid": "adsdafkjadshf123123",
        "api_request_id": "c1a2b3d4-0000-1111-2222-333344445555",
    }
    plivo_toolkit.client.verify_session.create.assert_called_once_with(
        recipient="+14150000001",
        channel="sms",
    )


def test_verify_otp_success(plivo_toolkit):
    plivo_toolkit.client.verify_session.validate.return_value = (
        SimpleNamespace(message="session validated successfully.")
    )

    result = plivo_toolkit.verify_otp(
        session_uuid="adsdafkjadshf123123", otp="123456"
    )

    assert result == {
        "verified": True,
        "message": "session validated successfully.",
    }
    plivo_toolkit.client.verify_session.validate.assert_called_once_with(
        session_uuid="adsdafkjadshf123123",
        otp="123456",
    )


def test_verify_otp_wrong_code_not_verified(plivo_toolkit):
    # A 200 response with a non-success message must NOT be read as verified.
    plivo_toolkit.client.verify_session.validate.return_value = (
        SimpleNamespace(message="The passcode entered is incorrect.")
    )

    result = plivo_toolkit.verify_otp(
        session_uuid="adsdafkjadshf123123", otp="000000"
    )

    assert result == {
        "verified": False,
        "message": "The passcode entered is incorrect.",
    }


def test_lookup_number_success(plivo_toolkit):
    plivo_toolkit.client.lookup.get.return_value = SimpleNamespace(
        api_id="a35a2e7a-fd27-42e6-910c-33382f43240e",
        phone_number="+14154305555",
        country=SimpleNamespace(name="United States", iso2="US", iso3="USA"),
        format=SimpleNamespace(
            e164="+14154305555",
            national="(415) 430-5555",
            international="+1 415-430-5555",
            rfc3966="tel:+1-415-430-5555",
        ),
        carrier=SimpleNamespace(
            mobile_country_code="310",
            mobile_network_code="150",
            name="Cingular Wireless",
            type="mobile",
            ported="yes",
        ),
        resource_uri="/v1/Number/+14154305555?type=carrier",
    )

    result = plivo_toolkit.lookup_number(number="+14154305555")

    assert result["phone_number"] == "+14154305555"
    assert result["country"]["iso2"] == "US"
    assert result["carrier"]["name"] == "Cingular Wireless"
    assert result["carrier"]["type"] == "mobile"
    plivo_toolkit.client.lookup.get.assert_called_once_with("+14154305555")


def test_lookup_number_failure(plivo_toolkit):
    plivo_toolkit.client.lookup.get.side_effect = Exception("Invalid number")

    result = plivo_toolkit.lookup_number(number="not-a-number")

    assert result == "Failed to look up number: Invalid number"


def test_get_tools(plivo_toolkit):
    tools = plivo_toolkit.get_tools()

    assert len(tools) == 5
    for tool in tools:
        assert hasattr(tool, "func") and callable(tool.func)
