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

from unittest.mock import MagicMock, patch

import pytest
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from camel.toolkits.zoominfo_toolkit import (
    ZoomInfoToolkit,
    _get_zoominfo_token,
    _make_zoominfo_request,
)


@pytest.fixture(autouse=True)
def set_env_vars(monkeypatch):
    """Set up environment variables for testing."""
    monkeypatch.setenv("ZOOMINFO_USERNAME", "test_user")
    monkeypatch.setenv("ZOOMINFO_PASSWORD", "test_pass")
    monkeypatch.setenv("ZOOMINFO_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("ZOOMINFO_PRIVATE_KEY", "-----BEGIN PRIVATE KEY-----\ntest_key\n-----END PRIVATE KEY-----")


def test_toolkit_init():
    """Test toolkit initialization."""
    with patch('camel.toolkits.zoominfo_toolkit._get_zoominfo_token') as mock_token:
        mock_token.return_value = "test_token"
        toolkit = ZoomInfoToolkit()
        assert toolkit is not None


def test_get_tools():
    """Test getting available tools."""
    with patch('camel.toolkits.zoominfo_toolkit._get_zoominfo_token') as mock_token:
        mock_token.return_value = "test_token"
        toolkit = ZoomInfoToolkit()
        tools = toolkit.get_tools()
        assert len(tools) == 3
        tool_names = [tool.func.__name__ for tool in tools]
        assert "zoominfo_search_companies" in tool_names
        assert "zoominfo_search_contacts" in tool_names
        assert "zoominfo_enrich_contact" in tool_names


@patch('camel.toolkits.zoominfo_toolkit.requests.request')
def test_search_companies(mock_request):
    """Test company search functionality."""
    # Mock successful API response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "maxResults": 10,
        "totalResults": 150,
        "currentPage": 1,
        "data": [
            {"id": 12345, "name": "Test Company"},
            {"id": 67890, "name": "Another Company"}
        ]
    }
    mock_response.raise_for_status.return_value = None
    mock_request.return_value = mock_response
    
    with patch('camel.toolkits.zoominfo_toolkit._get_zoominfo_token') as mock_token:
        mock_token.return_value = "test_token"
        toolkit = ZoomInfoToolkit()
        
        result = toolkit.zoominfo_search_companies(
            company_name="Test Company",
            rpp=10,
            page=1
        )
        
        assert "data" in result
        assert len(result["data"]) == 2
        assert result["data"][0]["name"] == "Test Company"


@patch('camel.toolkits.zoominfo_toolkit.requests.request')
def test_search_contacts(mock_request):
    """Test contact search functionality."""
    # Mock successful API response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "maxResults": 10,
        "totalResults": 50,
        "currentPage": 1,
        "data": [
            {
                "id": 12345,
                "firstName": "John",
                "lastName": "Doe",
                "jobTitle": "Software Engineer",
                "contactAccuracyScore": 95,
                "company": {"id": 67890, "name": "Test Company"}
            }
        ]
    }
    mock_response.raise_for_status.return_value = None
    mock_request.return_value = mock_response
    
    with patch('camel.toolkits.zoominfo_toolkit._get_zoominfo_token') as mock_token:
        mock_token.return_value = "test_token"
        toolkit = ZoomInfoToolkit()
        
        result = toolkit.zoominfo_search_contacts(
            company_name="Test Company",
            job_title="Software Engineer",
            rpp=10,
            page=1
        )
        
        assert "data" in result
        assert len(result["data"]) == 1
        assert result["data"][0]["firstName"] == "John"
        assert result["data"][0]["contactAccuracyScore"] == 95


@patch('camel.toolkits.zoominfo_toolkit.requests.request')
def test_enrich_contact(mock_request):
    """Test contact enrichment functionality."""
    # Mock successful API response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "success": True,
        "data": {
            "outputFields": ["id", "firstName", "lastName", "email"],
            "result": [
                {
                    "input": {"emailAddress": "john@example.com"},
                    "data": [
                        {
                            "id": 12345,
                            "firstName": "John",
                            "lastName": "Doe",
                            "email": "john.doe@company.com"
                        }
                    ],
                    "matchStatus": "matched"
                }
            ]
        }
    }
    mock_response.raise_for_status.return_value = None
    mock_request.return_value = mock_response
    
    with patch('camel.toolkits.zoominfo_toolkit._get_zoominfo_token') as mock_token:
        mock_token.return_value = "test_token"
        toolkit = ZoomInfoToolkit()
        
        result = toolkit.zoominfo_enrich_contact(
            match_person_input=[{"emailAddress": "john@example.com"}],
            output_fields=["id", "firstName", "lastName", "email"]
        )
        
        assert result["success"] is True
        assert len(result["data"]["result"]) == 1
        assert result["data"]["result"][0]["matchStatus"] == "matched"


def test_get_access_token_password():
    """Test access token retrieval with username/password."""
    # Mock the zi_api_auth_client module to avoid import errors
    mock_auth = MagicMock()
    mock_auth.user_name_pwd_authentication.return_value = "test_jwt_token"
    
    # Clear global variables
    import camel.toolkits.zoominfo_toolkit
    camel.toolkits.zoominfo_toolkit._zoominfo_access_token = None
    camel.toolkits.zoominfo_toolkit._zoominfo_token_expires_at = 0
    
    # Mock the import to avoid ModuleNotFoundError
    with patch.dict('sys.modules', {'zi_api_auth_client': mock_auth}):
        token = _get_zoominfo_token()
        assert token == "test_jwt_token"
        mock_auth.user_name_pwd_authentication.assert_called_once_with("test_user", "test_pass")


def test_missing_credentials(monkeypatch):
    """Test initialization with missing credentials."""
    monkeypatch.delenv("ZOOMINFO_USERNAME", raising=False)
    
    with pytest.raises(ValueError, match="ZoomInfo credentials missing"):
        # Clear the cached token first
        import camel.toolkits.zoominfo_toolkit
        camel.toolkits.zoominfo_toolkit._zoominfo_access_token = None
        camel.toolkits.zoominfo_toolkit._zoominfo_token_expires_at = 0
        ZoomInfoToolkit()


@patch('camel.toolkits.zoominfo_toolkit.requests.request')
def test_api_request_error(mock_request):
    """Test API request error handling."""
    mock_request.side_effect = Exception("ZoomInfo API request failed: Connection error")
    
    with patch('camel.toolkits.zoominfo_toolkit._get_zoominfo_token') as mock_token:
        mock_token.return_value = "test_token"
        
        with pytest.raises(Exception, match="ZoomInfo API request failed"):
            _make_zoominfo_request("POST", "/search/company", {"test": "data"})


@patch('camel.toolkits.zoominfo_toolkit.requests.request')
def test_search_companies_with_filters(mock_request):
    """Test company search with various filters."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": []}
    mock_response.raise_for_status.return_value = None
    mock_request.return_value = mock_response
    
    with patch('camel.toolkits.zoominfo_toolkit._get_zoominfo_token') as mock_token:
        mock_token.return_value = "test_token"
        toolkit = ZoomInfoToolkit()
        
        # Test with all parameters
        toolkit.zoominfo_search_companies(
            company_name="Test Corp",
            company_website="testcorp.com",
            industry="Technology",
            rpp=20,
            page=2,
            sort_by="employeeCount",
            sort_order="desc"
        )
        
        # Verify the request was made with correct parameters
        call_args = mock_request.call_args
        assert call_args[1]["json"]["companyName"] == "Test Corp"
        assert call_args[1]["json"]["companyWebsite"] == "testcorp.com"
        assert call_args[1]["json"]["companyDescription"] == "Technology"
        assert call_args[1]["json"]["rpp"] == 20
        assert call_args[1]["json"]["page"] == 2
        assert call_args[1]["json"]["sortBy"] == "employeeCount"
        assert call_args[1]["json"]["sortOrder"] == "desc"
