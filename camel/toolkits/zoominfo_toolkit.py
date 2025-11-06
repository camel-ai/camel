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

import os
import time
import json
import requests
import logging
from typing import Any, Dict, List, Optional, Literal
from camel.toolkits.base import BaseToolkit
try:
    from camel.toolkits.base import BaseToolkit
    from camel.toolkits import FunctionTool
    from camel.utils import MCPServer, api_keys_required, retry_on_error
except ImportError:
    # Fallback for testing without full CAMEL installation
    class BaseToolkit:
        def __init__(self, timeout=None):
            self.timeout = timeout
    
    class FunctionTool:
        def __init__(self, func):
            self.func = func
    
    def MCPServer():
        def decorator(cls):
            return cls
        return decorator
    
    def api_keys_required(keys):
        def decorator(func):
            return func
        return decorator
    
    def retry_on_error():
        def decorator(func):
            return func
        return decorator


# Global variables for token management
_zoominfo_access_token = None
_zoominfo_token_expires_at = 0

# Setup logger
logger = logging.getLogger(__name__)


def _get_zoominfo_token() -> str:
    r"""Get or refresh ZoomInfo JWT token."""
    global _zoominfo_access_token, _zoominfo_token_expires_at
    
    # Check if current token is still valid
    if _zoominfo_access_token and time.time() < _zoominfo_token_expires_at:
        return _zoominfo_access_token
    
    # Get credentials from environment
    username = os.getenv("ZOOMINFO_USERNAME")
    password = os.getenv("ZOOMINFO_PASSWORD")
    client_id = os.getenv("ZOOMINFO_CLIENT_ID")
    private_key = os.getenv("ZOOMINFO_PRIVATE_KEY")
    
    if not username:
        raise ValueError("ZoomInfo credentials missing. Please set ZOOMINFO_USERNAME environment variable.")
    
    # Try PKI authentication first if available
    if client_id and private_key:
        try:
            import jwt
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import padding
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives.serialization import load_pem_private_key
            
            # Load private key
            private_key_obj = load_pem_private_key(
                private_key.encode(),
                password=None,
                backend=default_backend()
            )
            
            # Create JWT token
            current_time = int(time.time())
            payload = {
                "iss": client_id,
                "exp": current_time + 3600,  # 1 hour expiration
                "iat": current_time,
                "sub": username
            }
            
            token = jwt.encode(
                payload,
                private_key_obj,
                algorithm="RS256",
                headers={"kid": client_id}
            )
            
            _zoominfo_access_token = token
            _zoominfo_token_expires_at = current_time + 3500  # Refresh 5 minutes before expiry
            return token
            
        except ImportError:
            logger.warning("PKI authentication requires 'pyjwt' and 'cryptography' packages. Falling back to username/password.")
        except Exception as e:
            logger.warning(f"PKI authentication failed: {e}. Falling back to username/password.")
    
    # Fallback to username/password authentication
    if not password:
        raise ValueError("ZoomInfo credentials missing. Please set ZOOMINFO_PASSWORD environment variable.")
    
    try:
        import zi_api_auth_client
        token = zi_api_auth_client.user_name_pwd_authentication(username, password)
        _zoominfo_access_token = token
        _zoominfo_token_expires_at = time.time() + 3500  # Refresh 5 minutes before expiry
        return token
    except ImportError:
        raise ValueError("ZoomInfo authentication requires 'zi_api_auth_client' package. Please install it with: pip install zi_api_auth_client")


def _make_zoominfo_request(
    method: str,
    endpoint: str,
    headers: Optional[Dict[str, str]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    r"""Make a request to ZoomInfo API with proper error handling."""
    base_url = "https://api.zoominfo.com"
    url = f"{base_url}{endpoint}"
    
    # Get authentication token
    token = _get_zoominfo_token()
    
    # Prepare headers
    request_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    if headers:
        request_headers.update(headers)
    
    try:
        response = requests.request(
            method=method,
            url=url,
            headers=request_headers,
            json=json_data,
            params=params,
            timeout=30,
        )
        
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"ZoomInfo API request failed: {e}")


@MCPServer()
class ZoomInfoToolkit(BaseToolkit):
    r"""ZoomInfo API toolkit for B2B data intelligence and contact/company search."""
    
    def __init__(self, timeout: Optional[float] = None):
        super().__init__(timeout=timeout)
        # Validate credentials on initialization
        _get_zoominfo_token()
    
    @api_keys_required([
        (None, "ZOOMINFO_USERNAME"),
        (None, "ZOOMINFO_PASSWORD"),
    ])
    # Search for companies by various criteria
    def zoominfo_search_companies(
        self,
        company_name: str = "",
        company_website: str = "",
        industry: str = "",
        rpp: int = 10,
        page: int = 1,
        sort_by: Literal["name", "employeeCount", "revenue"] = "name",
        sort_order: Literal["asc", "desc"] = "asc",
        **kwargs
    ) -> Dict[str, Any]:
        r"""Search for companies using ZoomInfo API.
        
        Args:
            company_name (str): Company name to search for
            company_website (str): Company website to search for
            industry (str): Industry to filter by
            rpp (int): Results per page (default: 10)
            page (int): Page number (default: 1)
            sort_by (str): Sort field - "name", "employeeCount", or "revenue"
            sort_order (str): Sort order - "asc" or "desc"
            **kwargs: Additional search parameters
            
        Returns:
            Dict[str, Any]: Search results with company information
        """
        params = {
            "rpp": rpp,
            "page": page,
            "sortBy": sort_by,
            "sortOrder": sort_order,
        }
        
        # Add optional parameters
        if company_name:
            params["companyName"] = company_name
        if company_website:
            params["companyWebsite"] = company_website
        if industry:
            params["companyDescription"] = industry
        
        # Add any additional parameters
        params.update(kwargs)
        
        return _make_zoominfo_request(
            method="POST",
            endpoint="/search/company",
            json_data=params,
        )
    
    @api_keys_required([
        (None, "ZOOMINFO_USERNAME"),
        (None, "ZOOMINFO_PASSWORD"),
    ])
    # Search for contacts by company, title, and other criteria
    def zoominfo_search_contacts(
        self,
        company_name: str = "",
        job_title: str = "",
        management_level: str = "",
        email_address: str = "",
        rpp: int = 10,
        page: int = 1,
        sort_by: Literal[
            "contactAccuracyScore", "lastName", "companyName", 
            "hierarchy", "sourceCount", "lastMentioned", "relevance"
        ] = "contactAccuracyScore",
        sort_order: Literal["asc", "desc"] = "desc",
        **kwargs
    ) -> Dict[str, Any]:
        r"""Search for contacts using ZoomInfo API.
        
        Args:
            company_name (str): Company name to search in
            job_title (str): Job title to search for
            management_level (str): Management level to filter by
            email_address (str): Email address to search for
            rpp (int): Results per page (default: 10)
            page (int): Page number (default: 1)
            sort_by (str): Sort field for contacts
            sort_order (str): Sort order - "asc" or "desc"
            **kwargs: Additional search parameters
            
        Returns:
            Dict[str, Any]: Search results with contact information
        """
        params = {
            "rpp": rpp,
            "page": page,
            "sortBy": sort_by,
            "sortOrder": sort_order,
        }
        
        # Add optional parameters
        if company_name:
            params["companyName"] = company_name
        if job_title:
            params["jobTitle"] = job_title
        if management_level:
            params["managementLevel"] = management_level
        if email_address:
            params["emailAddress"] = email_address
        
        # Add any additional parameters
        params.update(kwargs)
        
        return _make_zoominfo_request(
            method="POST",
            endpoint="/search/contact",
            json_data=params,
        )
    
    @api_keys_required([
        (None, "ZOOMINFO_USERNAME"),
        (None, "ZOOMINFO_PASSWORD"),
    ])
    # Enrich contact information with additional data
    def zoominfo_enrich_contact(
        self,
        match_person_input: List[Dict[str, Any]],
        output_fields: List[str],
        **kwargs
    ) -> Dict[str, Any]:
        r"""Enrich contact information using ZoomInfo API.
        
        Args:
            match_person_input (List[Dict]): List of contact inputs to match
            output_fields (List[str]): List of fields to return in output
            **kwargs: Additional enrichment parameters
            
        Returns:
            Dict[str, Any]: Enriched contact information
        """
        params = {
            "matchPersonInput": match_person_input,
            "outputFields": output_fields,
        }
        
        # Add any additional parameters
        params.update(kwargs)
        
        return _make_zoominfo_request(
            method="POST",
            endpoint="/enrich/contact",
            json_data=params,
        )
    
    def get_tools(self) -> List[FunctionTool]:
        r"""Returns toolkit functions as tools."""
        return [
            FunctionTool(self.zoominfo_search_companies),
            FunctionTool(self.zoominfo_search_contacts),
            FunctionTool(self.zoominfo_enrich_contact),
        ]
