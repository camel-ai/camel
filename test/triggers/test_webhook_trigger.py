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
from typing import Any, Dict, Optional
from unittest.mock import MagicMock

import pytest
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase

from camel.triggers.base_trigger import TriggerState, TriggerType
from camel.triggers.webhook_trigger import (
    HttpMethod,
    WebhookAuth,
    WebhookConfig,
    WebhookTrigger,
)


class MockWebhookAuth(WebhookAuth):
    """Mock authentication handler for testing"""

    def __init__(self, should_pass: bool = True):
        self.should_pass = should_pass
        self.verify_called = False

    def verify_webhook_request(self, request: Any, raw_body: bytes) -> bool:
        self.verify_called = True
        return self.should_pass

    def get_verification_response(
        self, request: Any, raw_body: bytes
    ) -> Optional[Dict[str, Any]]:
        # Simulate verification challenge response
        return None


def test_webhook_trigger_initialization_basic():
    """Test basic WebhookTrigger initialization with minimal config"""
    trigger = WebhookTrigger(
        trigger_id="test_webhook",
        name="Test Webhook",
        description="A test webhook trigger",
        port=8080,
        path="/webhook",
    )

    assert trigger.trigger_id == "test_webhook"
    assert trigger.name == "Test Webhook"
    assert trigger.port == 8080
    assert trigger.path == "/webhook"
    assert trigger.host == "localhost"
    assert trigger.state == TriggerState.INACTIVE


def test_webhook_trigger_initialization_with_config():
    """Test initialization with custom WebhookConfig"""
    config = WebhookConfig(
        allowed_methods=[HttpMethod.POST, HttpMethod.GET],
        max_payload_size=2 * 1024 * 1024,
        custom_headers={"X-Custom": "value"},
    )

    trigger = WebhookTrigger(
        trigger_id="test_webhook",
        name="Test Webhook",
        description="A test webhook trigger",
        port=8080,
        path="/webhook",
        host="0.0.0.0",
        webhook_config=config,
    )

    assert trigger.host == "0.0.0.0"
    assert trigger.webhook_config.max_payload_size == 2 * 1024 * 1024
    assert HttpMethod.GET in trigger.webhook_config.allowed_methods


def test_webhook_trigger_initialization_with_auth():
    """Test initialization with authentication handler"""
    auth_handler = MockWebhookAuth()

    trigger = WebhookTrigger(
        trigger_id="test_webhook",
        name="Test Webhook",
        description="A test webhook trigger",
        port=8080,
        path="/webhook",
        auth_handler=auth_handler,
    )

    assert trigger.auth_handler is auth_handler


def test_webhook_trigger_invalid_port():
    """Test that invalid port raises ValueError"""
    with pytest.raises(ValueError, match="Port must be in range"):
        WebhookTrigger(
            trigger_id="test_webhook",
            name="Test Webhook",
            description="A test webhook trigger",
            port=70000,
            path="/webhook",
        )


def test_webhook_trigger_invalid_path():
    """Test that invalid path raises ValueError"""
    with pytest.raises(ValueError, match="Path must start with"):
        WebhookTrigger(
            trigger_id="test_webhook",
            name="Test Webhook",
            description="A test webhook trigger",
            port=8080,
            path="webhook",
        )


def test_validate_config_valid():
    """Test config validation with valid configuration"""
    trigger = WebhookTrigger(
        trigger_id="test_webhook",
        name="Test Webhook",
        description="A test webhook trigger",
        port=8080,
        path="/webhook",
    )

    config = {
        "port": 9090,
        "path": "/test",
        "host": "localhost",
    }

    assert trigger.validate_config(config) is True


def test_validate_config_missing_fields():
    """Test config validation with missing required fields"""
    trigger = WebhookTrigger(
        trigger_id="test_webhook",
        name="Test Webhook",
        description="A test webhook trigger",
        port=8080,
        path="/webhook",
    )

    config = {
        "port": 8080,
    }

    assert trigger.validate_config(config) is False


def test_validate_config_invalid_port():
    """Test config validation with invalid port"""
    trigger = WebhookTrigger(
        trigger_id="test_webhook",
        name="Test Webhook",
        description="A test webhook trigger",
        port=8080,
        path="/webhook",
    )

    config = {
        "port": "not_a_number",
        "path": "/webhook",
        "host": "localhost",
    }

    assert trigger.validate_config(config) is False


def test_validate_config_invalid_path():
    """Test config validation with invalid path"""
    trigger = WebhookTrigger(
        trigger_id="test_webhook",
        name="Test Webhook",
        description="A test webhook trigger",
        port=8080,
        path="/webhook",
    )

    config = {
        "port": 8080,
        "path": "invalid_path",
        "host": "localhost",
    }

    assert trigger.validate_config(config) is False


@pytest.mark.asyncio
async def test_initialize():
    """Test webhook trigger initialization creates server"""
    trigger = WebhookTrigger(
        trigger_id="test_webhook",
        name="Test Webhook",
        description="A test webhook trigger",
        port=8080,
        path="/webhook",
    )

    result = await trigger.initialize()

    assert result is True
    assert trigger.server is not None
    assert isinstance(trigger.server, web.Application)


@pytest.mark.asyncio
async def test_initialize_with_multiple_methods():
    """Test initialization adds routes for all allowed HTTP methods"""
    config = WebhookConfig(
        allowed_methods=[
            HttpMethod.GET,
            HttpMethod.POST,
            HttpMethod.PUT,
            HttpMethod.PATCH,
            HttpMethod.DELETE,
        ]
    )

    trigger = WebhookTrigger(
        trigger_id="test_webhook",
        name="Test Webhook",
        description="A test webhook trigger",
        port=8080,
        path="/webhook",
        webhook_config=config,
    )

    await trigger.initialize()

    assert trigger.server is not None
    # Verify routes were added (checking router resources)
    assert len(trigger.server.router.resources()) > 0


@pytest.mark.asyncio
async def test_activate():
    """Test activating webhook server"""
    trigger = WebhookTrigger(
        trigger_id="test_webhook",
        name="Test Webhook",
        description="A test webhook trigger",
        port=18080,
        path="/webhook",
    )

    try:
        result = await trigger.activate()

        assert result is True
        assert trigger.state == TriggerState.ACTIVE
        assert trigger.runner is not None
        assert trigger.site is not None
    finally:
        # Cleanup
        await trigger.deactivate()


@pytest.mark.asyncio
async def test_deactivate():
    """Test deactivating webhook server"""
    trigger = WebhookTrigger(
        trigger_id="test_webhook",
        name="Test Webhook",
        description="A test webhook trigger",
        port=18081,
        path="/webhook",
    )

    await trigger.activate()
    assert trigger.state == TriggerState.ACTIVE

    result = await trigger.deactivate()

    assert result is True
    assert trigger.state == TriggerState.INACTIVE


@pytest.mark.asyncio
async def test_test_connection():
    """Test connection test checks port availability"""
    trigger = WebhookTrigger(
        trigger_id="test_webhook",
        name="Test Webhook",
        description="A test webhook trigger",
        port=18082,
        path="/webhook",
    )

    result = await trigger.test_connection()

    assert result is True


@pytest.mark.asyncio
async def test_process_trigger_event():
    """Test processing webhook data into TriggerEvent"""
    trigger = WebhookTrigger(
        trigger_id="test_webhook",
        name="Test Webhook",
        description="A test webhook trigger",
        port=8080,
        path="/webhook",
    )

    event_data = {
        "payload": {"message": "test"},
        "headers": {"Content-Type": "application/json"},
        "method": "POST",
        "url": "http://localhost:8080/webhook",
        "raw_payload": {"message": "test"},
    }

    event = await trigger.process_trigger_event(event_data)

    assert event.trigger_id == "test_webhook"
    assert event.trigger_type == TriggerType.WEBHOOK
    assert event.payload == {"message": "test"}
    assert "headers" in event.metadata
    assert event.metadata["method"] == "POST"


def test_get_webhook_config():
    """Test getting webhook configuration"""
    config = WebhookConfig(
        allowed_methods=[HttpMethod.POST],
        max_payload_size=1024,
    )

    trigger = WebhookTrigger(
        trigger_id="test_webhook",
        name="Test Webhook",
        description="A test webhook trigger",
        port=8080,
        path="/webhook",
        webhook_config=config,
    )

    retrieved_config = trigger.get_webhook_config()

    assert retrieved_config == config
    assert retrieved_config.max_payload_size == 1024


def test_http_method_enum():
    """Test HttpMethod enum values"""
    assert HttpMethod.GET.value == "GET"
    assert HttpMethod.POST.value == "POST"
    assert HttpMethod.PUT.value == "PUT"
    assert HttpMethod.PATCH.value == "PATCH"
    assert HttpMethod.DELETE.value == "DELETE"


def test_webhook_config_defaults():
    """Test WebhookConfig default values"""
    config = WebhookConfig()

    assert config.allowed_methods == [HttpMethod.POST]
    assert config.max_payload_size == 1024 * 1024
    assert config.custom_headers is None


def test_webhook_config_validation():
    """Test WebhookConfig validates payload size"""
    with pytest.raises(ValueError):
        WebhookConfig(max_payload_size=0)


class WebhookTriggerTestCase(AioHTTPTestCase):
    """Test case for webhook request handling"""

    async def get_application(self):
        """Create test application"""
        self.trigger = WebhookTrigger(
            trigger_id="test_webhook",
            name="Test Webhook",
            description="A test webhook trigger",
            port=8080,
            path="/webhook",
        )
        await self.trigger.initialize()
        return self.trigger.server

    async def test_handle_webhook_json_payload(self):
        """Test handling webhook with JSON payload"""
        payload = {"message": "test data", "id": 123}

        callback_called = False
        received_event = None

        async def test_callback(event):
            nonlocal callback_called, received_event
            callback_called = True
            received_event = event

        self.trigger.add_callback(test_callback)

        resp = await self.client.request(
            "POST",
            "/webhook",
            json=payload,
        )

        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "success"

        # Give callbacks time to execute
        import asyncio

        await asyncio.sleep(0.1)

        assert callback_called is True
        assert received_event is not None
        assert received_event.payload["message"] == "test data"

    async def test_handle_webhook_form_data(self):
        """Test handling webhook with form-encoded data"""
        form_data = {"key1": "value1", "key2": "value2"}

        callback_called = False

        async def test_callback(event):
            nonlocal callback_called
            callback_called = True

        self.trigger.add_callback(test_callback)

        resp = await self.client.request(
            "POST",
            "/webhook",
            data=form_data,
        )

        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "success"

    async def test_handle_webhook_invalid_json(self):
        """Test handling webhook with invalid JSON"""
        resp = await self.client.request(
            "POST",
            "/webhook",
            data="invalid json{",
            headers={"Content-Type": "application/json"},
        )

        assert resp.status == 400
        data = await resp.json()
        assert "error" in data


class WebhookAuthTestCase(AioHTTPTestCase):
    """Test case for webhook authentication"""

    async def get_application(self):
        """Create test application with authentication"""
        self.auth_handler = MockWebhookAuth(should_pass=True)
        self.trigger = WebhookTrigger(
            trigger_id="test_webhook",
            name="Test Webhook",
            description="A test webhook trigger",
            port=8080,
            path="/webhook",
            auth_handler=self.auth_handler,
        )
        await self.trigger.initialize()
        return self.trigger.server

    async def test_handle_webhook_auth_success(self):
        """Test webhook request with successful authentication"""
        payload = {"message": "authenticated"}

        resp = await self.client.request(
            "POST",
            "/webhook",
            json=payload,
        )

        assert resp.status == 200
        assert self.auth_handler.verify_called is True

    async def test_handle_webhook_auth_failure(self):
        """Test webhook request with failed authentication"""
        self.auth_handler.should_pass = False
        payload = {"message": "unauthorized"}

        resp = await self.client.request(
            "POST",
            "/webhook",
            json=payload,
        )

        assert resp.status == 403
        data = await resp.json()
        assert "error" in data
        assert "Authentication failed" in data["error"]


@pytest.mark.asyncio
async def test_webhook_multiple_callbacks():
    """Test that multiple callbacks can be registered and invoked"""
    trigger = WebhookTrigger(
        trigger_id="test_webhook",
        name="Test Webhook",
        description="A test webhook trigger",
        port=8080,
        path="/webhook",
    )

    callback1_called = False
    callback2_called = False

    async def callback1(event):
        nonlocal callback1_called
        callback1_called = True

    async def callback2(event):
        nonlocal callback2_called
        callback2_called = True

    trigger.add_callback(callback1)
    trigger.add_callback(callback2)

    # Manually create and emit event
    event_data = {
        "payload": {"test": "data"},
        "headers": {},
        "method": "POST",
        "url": "http://localhost:8080/webhook",
        "raw_payload": {"test": "data"},
    }
    event = await trigger.process_trigger_event(event_data)
    await trigger._emit_trigger_event(event)

    # Give async operations time to complete
    import asyncio

    await asyncio.sleep(0.1)

    assert callback1_called is True
    assert callback2_called is True


@pytest.mark.asyncio
async def test_webhook_config_custom_headers():
    """Test webhook configuration with custom headers"""
    config = WebhookConfig(
        allowed_methods=[HttpMethod.POST],
        custom_headers={
            "X-Custom-Header": "custom-value",
            "X-Api-Version": "v1",
        },
    )

    trigger = WebhookTrigger(
        trigger_id="test_webhook",
        name="Test Webhook",
        description="A test webhook trigger",
        port=8080,
        path="/webhook",
        webhook_config=config,
    )

    assert trigger.webhook_config.custom_headers is not None
    assert "X-Custom-Header" in trigger.webhook_config.custom_headers


def test_webhook_auth_interface():
    """Test WebhookAuth interface implementation"""
    auth = MockWebhookAuth()

    # Mock request and body
    mock_request = MagicMock()
    raw_body = b"test body"

    # Test verify method
    result = auth.verify_webhook_request(mock_request, raw_body)
    assert result is True
    assert auth.verify_called is True

    # Test verification response
    response = auth.get_verification_response(mock_request, raw_body)
    assert response is None


@pytest.mark.asyncio
async def test_default_webhook_config_creation():
    """Test that default WebhookConfig is created when none provided"""
    trigger = WebhookTrigger(
        trigger_id="test_webhook",
        name="Test Webhook",
        description="A test webhook trigger",
        port=8080,
        path="/webhook",
    )

    assert trigger.webhook_config is not None
    assert isinstance(trigger.webhook_config, WebhookConfig)
    assert trigger.webhook_config.allowed_methods == [HttpMethod.POST]


@pytest.mark.asyncio
async def test_webhook_metadata_in_event():
    """Test that webhook metadata is properly included in event"""
    trigger = WebhookTrigger(
        trigger_id="test_webhook",
        name="Test Webhook",
        description="A test webhook trigger",
        port=8080,
        path="/webhook",
    )

    event_data = {
        "payload": {"data": "test"},
        "headers": {
            "Content-Type": "application/json",
            "User-Agent": "TestClient/1.0",
        },
        "method": "POST",
        "url": "http://localhost:8080/webhook?param=value",
        "raw_payload": {"data": "test"},
    }

    event = await trigger.process_trigger_event(event_data)

    assert event.metadata["headers"]["User-Agent"] == "TestClient/1.0"
    assert event.metadata["url"] == "http://localhost:8080/webhook?param=value"
    assert event.metadata["raw_payload"] == {"data": "test"}


class WebhookPayloadSizeTestCase(AioHTTPTestCase):
    """Test case for payload size validation"""

    async def get_application(self):
        """Create test application with custom payload size limit"""
        config = WebhookConfig(
            max_payload_size=1024,
        )
        self.trigger = WebhookTrigger(
            trigger_id="test_webhook",
            name="Test Webhook",
            description="A test webhook trigger",
            port=8080,
            path="/webhook",
            webhook_config=config,
        )
        await self.trigger.initialize()
        return self.trigger.server

    async def test_handle_webhook_payload_within_limit(self):
        """Test webhook accepts payload within size limit"""
        payload = {"message": "small payload"}

        resp = await self.client.request(
            "POST",
            "/webhook",
            json=payload,
        )

        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "success"

    async def test_handle_webhook_payload_exceeds_limit(self):
        """Test webhook rejects payload exceeding size limit"""
        large_payload = {"data": "x" * 2000}

        resp = await self.client.request(
            "POST",
            "/webhook",
            json=large_payload,
        )

        assert resp.status == 413
        data = await resp.json()
        assert "error" in data
        assert "Payload too large" in data["error"]

    async def test_handle_webhook_payload_at_limit(self):
        """Test webhook accepts payload exactly at size limit"""
        payload = {"data": "x" * 950}

        resp = await self.client.request(
            "POST",
            "/webhook",
            json=payload,
        )

        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "success"


class WebhookCustomHeadersTestCase(AioHTTPTestCase):
    """Test case for custom headers in responses"""

    async def get_application(self):
        """Create test application with custom headers"""
        config = WebhookConfig(
            custom_headers={
                "X-Custom-Header": "custom-value",
                "X-Api-Version": "v1.0",
                "X-Request-Id": "test-123",
            },
        )
        self.trigger = WebhookTrigger(
            trigger_id="test_webhook",
            name="Test Webhook",
            description="A test webhook trigger",
            port=8080,
            path="/webhook",
            webhook_config=config,
        )
        await self.trigger.initialize()
        return self.trigger.server

    async def test_handle_webhook_success_with_custom_headers(self):
        """Test custom headers are included in success response"""
        payload = {"message": "test"}

        resp = await self.client.request(
            "POST",
            "/webhook",
            json=payload,
        )

        assert resp.status == 200
        assert resp.headers.get("X-Custom-Header") == "custom-value"
        assert resp.headers.get("X-Api-Version") == "v1.0"
        assert resp.headers.get("X-Request-Id") == "test-123"

    async def test_handle_webhook_error_with_custom_headers(self):
        """Test custom headers are included in error response"""
        resp = await self.client.request(
            "POST",
            "/webhook",
            data="invalid json{",
            headers={"Content-Type": "application/json"},
        )

        assert resp.status == 400
        assert resp.headers.get("X-Custom-Header") == "custom-value"
        assert resp.headers.get("X-Api-Version") == "v1.0"
        assert resp.headers.get("X-Request-Id") == "test-123"


class WebhookCustomHeadersAuthTestCase(AioHTTPTestCase):
    """Test case for custom headers with authentication failures"""

    async def get_application(self):
        """Create test application with custom headers and auth"""
        config = WebhookConfig(
            custom_headers={
                "X-Auth-Provider": "custom",
                "X-Security-Level": "high",
            },
        )
        self.auth_handler = MockWebhookAuth(should_pass=False)
        self.trigger = WebhookTrigger(
            trigger_id="test_webhook",
            name="Test Webhook",
            description="A test webhook trigger",
            port=8080,
            path="/webhook",
            webhook_config=config,
            auth_handler=self.auth_handler,
        )
        await self.trigger.initialize()
        return self.trigger.server

    async def test_handle_webhook_auth_failure_with_custom_headers(self):
        """Test custom headers are included in auth failure response"""
        payload = {"message": "test"}

        resp = await self.client.request(
            "POST",
            "/webhook",
            json=payload,
        )

        assert resp.status == 403
        assert resp.headers.get("X-Auth-Provider") == "custom"
        assert resp.headers.get("X-Security-Level") == "high"
        data = await resp.json()
        assert "error" in data
        assert "Authentication failed" in data["error"]


@pytest.mark.asyncio
async def test_webhook_config_max_payload_size_bounds():
    """Test WebhookConfig enforces payload size boundaries"""
    config_valid = WebhookConfig(max_payload_size=1024)
    assert config_valid.max_payload_size == 1024

    config_max = WebhookConfig(max_payload_size=10 * 1024 * 1024)
    assert config_max.max_payload_size == 10 * 1024 * 1024

    with pytest.raises(ValueError):
        WebhookConfig(max_payload_size=0)

    with pytest.raises(ValueError):
        WebhookConfig(max_payload_size=11 * 1024 * 1024)
