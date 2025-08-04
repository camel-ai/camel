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

from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
import shutil
import socket
import subprocess
import tempfile
import time
from typing import Any, Dict, List, Optional

from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit

logger = get_logger(__name__)


class WebDeployToolkit(BaseToolkit):
    r"""A simple toolkit for initializing React projects and deploying web.

    This toolkit provides core functionality to:
    - Initialize new React projects
    - Build React applications
    - Deploy HTML content to local server
    - Serve static websites locally
    """

    def __init__(
        self,
        timeout: Optional[float] = None,
        add_branding_tag: bool = True,
        logo_path: str = "../camel/misc/favicon.png",
        tag_text: str = "Created by CAMEL",
        tag_url: str = "https://github.com/camel-ai/camel",
        remote_server_ip: Optional[str] = None,
        remote_server_port: int = 8080,
    ):
        r"""Initialize the WebDeployToolkit.

        Args:
            timeout (Optional[float]): Command timeout in seconds.
                (default: :obj:`None`)
            add_branding_tag (bool): Whether to add brand tag to deployed
                pages. (default: :obj:`True`)
            logo_path (str): Path to custom logo file (SVG, PNG, JPG, ICO).
                (default: :obj:`../camel/misc/favicon.png`)
            tag_text (str): Text to display in the tag.
                (default: :obj:`Created by CAMEL`)
            tag_url (str): URL to open when tag is clicked.
                (default: :obj:`https://github.com/camel-ai/camel`)
            remote_server_ip (Optional[str]): Remote server IP for deployment.
                (default: :obj:`None` - use local deployment)
            remote_server_port (int): Remote server port.
                (default: :obj:`8080`)
        """
        super().__init__(timeout=timeout)
        self.timeout = timeout
        self.server_instances: Dict[int, Any] = {}  # Track running servers
        self.add_branding_tag = add_branding_tag
        self.logo_path = logo_path
        self.tag_text = self._sanitize_text(tag_text)
        self.tag_url = self._validate_url(tag_url)
        self.remote_server_ip = (
            self._validate_ip_or_domain(remote_server_ip)
            if remote_server_ip
            else None
        )
        self.remote_server_port = self._validate_port(remote_server_port)
        self.server_registry_file = os.path.join(
            tempfile.gettempdir(), "web_deploy_servers.json"
        )
        self._load_server_registry()

    def _validate_ip_or_domain(self, address: str) -> str:
        r"""Validate IP address or domain name format."""
        import ipaddress
        import re

        try:
            # Try to validate as IP address first
            ipaddress.ip_address(address)
            return address
        except ValueError:
            # If not a valid IP, check if it's a valid domain name
            domain_pattern = re.compile(
                r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?'
                r'(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
            )
            if domain_pattern.match(address) and len(address) <= 253:
                return address
            else:
                raise ValueError(
                    f"Invalid IP address or domain name: {address}"
                )

    def _validate_port(self, port: int) -> int:
        r"""Validate port number."""
        if not isinstance(port, int) or port < 1 or port > 65535:
            raise ValueError(f"Invalid port number: {port}")
        return port

    def _sanitize_text(self, text: str) -> str:
        r"""Sanitize text to prevent XSS."""
        if not isinstance(text, str):
            return ""
        # Remove any HTML/script tags
        text = re.sub(r'<[^>]+>', '', text)
        # Escape special characters
        text = (
            text.replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
        )
        text = text.replace('"', '&quot;').replace("'", '&#x27;')
        return text[:100]  # Limit length

    def _validate_url(self, url: str) -> str:
        r"""Validate URL format."""
        if not isinstance(url, str):
            raise ValueError("URL must be a string")
        # Basic URL validation
        url_pattern = re.compile(
            r'^https?://'
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
            r'localhost|'
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
            r'(?::\d+)?'
            r'(?:/?|[/?]\S+)$',
            re.IGNORECASE,
        )
        if not url_pattern.match(url):
            raise ValueError(f"Invalid URL format: {url}")
        return url

    def _validate_subdirectory(
        self, subdirectory: Optional[str]
    ) -> Optional[str]:
        r"""Validate subdirectory to prevent path traversal."""
        if subdirectory is None:
            return None

        # Remove any leading/trailing slashes
        subdirectory = subdirectory.strip('/')

        # Check for path traversal attempts
        if '..' in subdirectory or subdirectory.startswith('/'):
            raise ValueError(f"Invalid subdirectory: {subdirectory}")

        # Only allow alphanumeric, dash, underscore, and forward slashes
        if not re.match(r'^[a-zA-Z0-9_-]+(?:/[a-zA-Z0-9_-]+)*$', subdirectory):
            raise ValueError(f"Invalid subdirectory format: {subdirectory}")

        return subdirectory

    def _is_port_available(self, port: int) -> bool:
        r"""Check if a port is available for binding."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(('127.0.0.1', port))
                return True
            except OSError:
                return False

    def _load_server_registry(self):
        r"""Load server registry from persistent storage."""
        try:
            if os.path.exists(self.server_registry_file):
                with open(self.server_registry_file, 'r') as f:
                    data = json.load(f)
                    # Reconstruct server instances from registry
                    for port_str, server_info in data.items():
                        port = int(port_str)
                        pid = server_info.get('pid')
                        if pid and self._is_process_running(pid):
                            # Create a mock process object for tracking
                            self.server_instances[port] = {
                                'pid': pid,
                                'start_time': server_info.get('start_time'),
                                'directory': server_info.get('directory'),
                            }
        except Exception as e:
            logger.warning(f"Could not load server registry: {e}")

    def _save_server_registry(self):
        r"""Save server registry to persistent storage."""
        try:
            registry_data = {}
            for port, server_info in self.server_instances.items():
                if isinstance(server_info, dict):
                    registry_data[str(port)] = {
                        'pid': server_info.get('pid'),
                        'start_time': server_info.get('start_time'),
                        'directory': server_info.get('directory'),
                    }
                else:
                    # Handle subprocess.Popen objects
                    registry_data[str(port)] = {
                        'pid': server_info.pid,
                        'start_time': time.time(),
                        'directory': getattr(server_info, 'directory', None),
                    }

            with open(self.server_registry_file, 'w') as f:
                json.dump(registry_data, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save server registry: {e}")

    def _is_process_running(self, pid: int) -> bool:
        r"""Check if a process with given PID is still running."""
        try:
            # Send signal 0 to check if process exists
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

    def _build_custom_url(
        self, domain: str, subdirectory: Optional[str] = None
    ) -> str:
        r"""Build custom URL with optional subdirectory.

        Args:
            domain (str): Custom domain
            subdirectory (Optional[str]): Subdirectory path

        Returns:
            str: Complete custom URL
        """
        # Validate domain
        if not re.match(r'^[a-zA-Z0-9.-]+$', domain):
            raise ValueError(f"Invalid domain format: {domain}")
        custom_url = f"http://{domain}:8080"
        if subdirectory:
            subdirectory = self._validate_subdirectory(subdirectory)
            custom_url += f"/{subdirectory}"
        return custom_url

    def _load_logo_as_data_uri(self, logo_path: str) -> str:
        r"""Load a local logo file and convert it to data URI.

        Args:
            logo_path (str): Path to the logo file

        Returns:
            str: Data URI of the logo file
        """
        try:
            if not os.path.exists(logo_path):
                logger.warning(f"Logo file not found: {logo_path}")
                return self._get_default_logo()

            # Get MIME type
            mime_type, _ = mimetypes.guess_type(logo_path)
            if not mime_type:
                # Default MIME types for common formats
                ext = os.path.splitext(logo_path)[1].lower()
                mime_types_map = {
                    '.svg': 'image/svg+xml',
                    '.png': 'image/png',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.ico': 'image/x-icon',
                    '.gif': 'image/gif',
                }
                mime_type = mime_types_map.get(ext, 'image/png')

            # Read file and encode to base64
            with open(logo_path, 'rb') as f:
                file_data = f.read()

            base64_data = base64.b64encode(file_data).decode('utf-8')
            return f"data:{mime_type};base64,{base64_data}"

        except Exception as e:
            logger.error(f"Error loading logo file {logo_path}: {e}")
            return self._get_default_logo()

    def _get_default_logo(self) -> str:
        r"""Get the default logo as data URI.

        Returns:
            str: Default logo data URI
        """
        default_logo_data_uri = (
            "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
            "width='32' height='32' viewBox='0 0 32 32' fill='none'%3E%3Crect "
            "width='32' height='32' rx='8' fill='%23333333'/%3E%3Ctext x='16' "
            "y='22' font-family='system-ui, -apple-system, sans-serif' "
            "font-size='12' font-weight='700' text-anchor='middle' "
            "fill='white'%3EAI%3C/text%3E%3C/svg%3E"
        )
        return default_logo_data_uri

    def deploy_html_content(
        self,
        html_content: Optional[str] = None,
        html_file_path: Optional[str] = None,
        file_name: str = "index.html",
        port: int = 8000,
        domain: Optional[str] = None,
        subdirectory: Optional[str] = None,
    ) -> Dict[str, Any]:
        r"""Deploy HTML content to a local server or remote server.

        Args:
            html_content (Optional[str]): HTML content to deploy. Either this
                or html_file_path must be provided.
            html_file_path (Optional[str]): Path to HTML file to deploy. Either
                this or html_content must be provided.
            file_name (str): Name for the HTML file when using html_content.
                (default: :obj:`index.html`)
            port (int): Port to serve on. (default: :obj:`8000`)
            domain (Optional[str]): Custom domain to access the content.
                (e.g., :obj:`example.com`)
            subdirectory (Optional[str]): Subdirectory path for multi-user
                deployment. (e.g., :obj:`user123`)

        Returns:
            Dict[str, Any]: Deployment result with server URL and custom domain
                info.
        """
        try:
            # Validate inputs
            if html_content is None and html_file_path is None:
                return {
                    'success': False,
                    'error': (
                        'Either html_content or html_file_path must be '
                        'provided'
                    ),
                }

            if html_content is not None and html_file_path is not None:
                return {
                    'success': False,
                    'error': (
                        'Cannot provide both html_content and '
                        'html_file_path'
                    ),
                }

            # Read content from file if file path is provided
            if html_file_path:
                if not os.path.exists(html_file_path):
                    return {
                        'success': False,
                        'error': f'HTML file not found: {html_file_path}',
                    }

                try:
                    with open(html_file_path, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    # Use the original filename if deploying from file
                    file_name = os.path.basename(html_file_path)
                except Exception as e:
                    return {
                        'success': False,
                        'error': f'Error reading HTML file: {e}',
                    }

            # Check if remote deployment is configured
            if self.remote_server_ip:
                return self._deploy_to_remote_server(
                    html_content,  # type: ignore[arg-type]
                    subdirectory,
                    domain,
                )
            else:
                return self._deploy_to_local_server(
                    html_content,  # type: ignore[arg-type]
                    file_name,
                    port,
                    domain,
                    subdirectory,
                )

        except Exception as e:
            logger.error(f"Error deploying HTML content: {e}")
            return {'success': False, 'error': str(e)}

    def _deploy_to_remote_server(
        self,
        html_content: str,
        subdirectory: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> Dict[str, Any]:
        r"""Deploy HTML content to remote server via API.

        Args:
            html_content (str): HTML content to deploy
            subdirectory (Optional[str]): Subdirectory path for deployment
            domain (Optional[str]): Custom domain

        Returns:
            Dict[str, Any]: Deployment result
        """
        try:
            import requests

            # Validate subdirectory
            subdirectory = self._validate_subdirectory(subdirectory)

            # Prepare deployment data
            deploy_data = {
                "html_content": html_content,
                "subdirectory": subdirectory,
                "domain": domain,
                "timestamp": time.time(),
            }

            # Send to remote server API
            api_url = f"http://{self.remote_server_ip}:{self.remote_server_port}/api/deploy"

            response = requests.post(
                api_url,
                json=deploy_data,
                timeout=self.timeout,
                # Security: disable redirects to prevent SSRF
                allow_redirects=False,
                # Add headers for security
                headers={'Content-Type': 'application/json'},
            )

            if response.status_code == 200:
                response.json()

                # Build URLs
                base_url = (
                    f"http://{self.remote_server_ip}:{self.remote_server_port}"
                )
                deployed_url = (
                    f"{base_url}/{subdirectory}/" if subdirectory else base_url
                )

                return {
                    'success': True,
                    'remote_url': deployed_url,
                    'server_ip': self.remote_server_ip,
                    'subdirectory': subdirectory,
                    'domain': domain,
                    'message': f'Successfully deployed to remote server!\n  • '
                    f'Access URL: {deployed_url}\n  • Server: '
                    f'{self.remote_server_ip}:{self.remote_server_port}',
                    'branding_tag_added': self.add_branding_tag,
                }
            else:
                return {
                    'success': False,
                    'error': f'Remote deployment failed: HTTP '
                    f'{response.status_code}',
                }

        except ImportError:
            return {
                'success': False,
                'error': 'Remote deployment requires requests library. '
                'Install with: pip install requests',
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Remote deployment error: {e!s}',
            }

    def _deploy_to_local_server(
        self,
        html_content: str,
        file_name: str,
        port: int,
        domain: Optional[str],
        subdirectory: Optional[str],
    ) -> Dict[str, Any]:
        r"""Deploy HTML content to local server (original functionality).

        Args:
            html_content (str): HTML content to deploy
            file_name (str): Name for the HTML file
            port (int): Port to serve on (default: 8000)
            domain (Optional[str]): Custom domain
            subdirectory (Optional[str]): Subdirectory path

        Returns:
            Dict[str, Any]: Deployment result
        """
        temp_dir = None
        try:
            # Validate subdirectory
            subdirectory = self._validate_subdirectory(subdirectory)

            # Create temporary directory
            temp_dir = tempfile.mkdtemp(prefix="web_deploy_")

            # Handle subdirectory for multi-user deployment
            if subdirectory:
                deploy_dir = os.path.join(temp_dir, subdirectory)
                os.makedirs(deploy_dir, exist_ok=True)
                html_file_path = os.path.join(deploy_dir, file_name)
            else:
                html_file_path = os.path.join(temp_dir, file_name)

            # Write enhanced HTML content to file
            with open(html_file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            # Start server
            server_result = self._serve_static_files(temp_dir, port)

            if server_result['success']:
                # Build URLs with localhost fallback
                local_url = server_result["server_url"]
                if subdirectory:
                    local_url += f"/{subdirectory}"

                # Custom domain URL (if provided)
                custom_url = (
                    self._build_custom_url(domain, subdirectory)
                    if domain
                    else None
                )

                # Localhost fallback URL
                localhost_url = f"http://localhost:{port}"
                if subdirectory:
                    localhost_url += f"/{subdirectory}"

                # Build message with all access options
                message = 'HTML content deployed successfully!\n'
                message += f'  • Local access: {local_url}\n'
                message += f'  • Localhost fallback: {localhost_url}'

                if custom_url:
                    message += f'\n  • Custom domain: {custom_url}'

                if self.add_branding_tag:
                    message += f'\n  • Branding: "{self.tag_text}" tag added'

                server_result.update(
                    {
                        'html_file': html_file_path,
                        'temp_directory': temp_dir,
                        'local_url': local_url,
                        'localhost_url': localhost_url,
                        'custom_url': custom_url,
                        'domain': domain,
                        'subdirectory': subdirectory,
                        'message': message,
                        'branding_tag_added': self.add_branding_tag,
                    }
                )

            return server_result

        except Exception as e:
            # Clean up temp directory on error
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception:
                    pass
            return {'success': False, 'error': str(e)}

    def _serve_static_files(self, directory: str, port: int) -> Dict[str, Any]:
        r"""Serve static files from a directory using a local HTTP server
        (as a background process).

        Args:
            directory (str): Directory to serve files from
            port (int): Port to serve on (default: 8000)

        Returns:
            Dict[str, Any]: Server information
        """
        import subprocess

        try:
            if not os.path.exists(directory):
                return {
                    'success': False,
                    'error': f'Directory {directory} does not exist',
                }

            if not os.path.isdir(directory):
                return {
                    'success': False,
                    'error': f'{directory} is not a directory',
                }

            # Validate port
            port = self._validate_port(port)

            # Check if port is already in use
            if port in self.server_instances:
                return {
                    'success': False,
                    'error': f'Port {port} is already in use by this toolkit',
                }

            # Check if port is available
            if not self._is_port_available(port):
                return {
                    'success': False,
                    'error': (
                        f'Port {port} is already in use by another process'
                    ),
                }

            # Start http.server as a background process with security
            # improvements
            process = subprocess.Popen(
                [
                    "python3",
                    "-m",
                    "http.server",
                    str(port),
                    "--bind",
                    "127.0.0.1",
                ],
                cwd=directory,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=False,  # Prevent shell injection
                env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'},
            )

            # Store both process and metadata for persistence
            self.server_instances[port] = {
                'process': process,
                'pid': process.pid,
                'start_time': time.time(),
                'directory': directory,
            }
            self._save_server_registry()

            # Wait for server to start with timeout
            start_time = time.time()
            while time.time() - start_time < 5:
                if not self._is_port_available(port):
                    # Port is now in use, server started
                    break
                time.sleep(0.1)
            else:
                # Server didn't start in time
                process.terminate()
                del self.server_instances[port]
                return {
                    'success': False,
                    'error': f'Server failed to start on port {port}',
                }

            server_url = f"http://localhost:{port}"

            return {
                'success': True,
                'server_url': server_url,
                'port': port,
                'directory': directory,
                'message': f'Static files served from {directory} at '
                f'{server_url} (background process)',
            }

        except Exception as e:
            logger.error(f"Error serving static files: {e}")
            return {'success': False, 'error': str(e)}

    def deploy_folder(
        self,
        folder_path: str,
        port: int = 8000,
        domain: Optional[str] = None,
        subdirectory: Optional[str] = None,
    ) -> Dict[str, Any]:
        r"""Deploy a folder containing web files.

        Args:
            folder_path (str): Path to the folder to deploy.
            port (int): Port to serve on. (default: :obj:`8000`)
            domain (Optional[str]): Custom domain to access the content.
                (e.g., :obj:`example.com`)
            subdirectory (Optional[str]): Subdirectory path for multi-user
                deployment. (e.g., :obj:`user123`)

        Returns:
            Dict[str, Any]: Deployment result with custom domain info.
        """
        try:
            if not os.path.exists(folder_path):
                return {
                    'success': False,
                    'error': f'Folder {folder_path} does not exist',
                }

            if not os.path.isdir(folder_path):
                return {
                    'success': False,
                    'error': f'{folder_path} is not a directory',
                }

            # Validate subdirectory
            subdirectory = self._validate_subdirectory(subdirectory)

            # Check if remote deployment is configured
            if self.remote_server_ip:
                return self._deploy_folder_to_remote_server(
                    folder_path,
                    subdirectory,
                    domain,
                )
            else:
                return self._deploy_folder_to_local_server(
                    folder_path,
                    port,
                    domain,
                    subdirectory,
                )

        except Exception as e:
            logger.error(f"Error deploying folder: {e}")
            return {'success': False, 'error': str(e)}

    def _deploy_folder_to_local_server(
        self,
        folder_path: str,
        port: int,
        domain: Optional[str],
        subdirectory: Optional[str],
    ) -> Dict[str, Any]:
        r"""Deploy folder to local server (original functionality).

        Args:
            folder_path (str): Path to the folder to deploy
            port (int): Port to serve on
            domain (Optional[str]): Custom domain
            subdirectory (Optional[str]): Subdirectory path

        Returns:
            Dict[str, Any]: Deployment result
        """
        try:
            temp_dir = None
            if self.add_branding_tag:
                # Create temporary directory and copy all files
                temp_dir = tempfile.mkdtemp(prefix="web_deploy_enhanced_")

                # Handle subdirectory structure
                if subdirectory:
                    deploy_base = os.path.join(temp_dir, subdirectory)
                    os.makedirs(deploy_base, exist_ok=True)
                    shutil.copytree(
                        folder_path,
                        deploy_base,
                        dirs_exist_ok=True,
                    )
                    deploy_path = deploy_base
                else:
                    shutil.copytree(
                        folder_path,
                        os.path.join(temp_dir, "site"),
                        dirs_exist_ok=True,
                    )
                    deploy_path = os.path.join(temp_dir, "site")

                # Enhance HTML files with branding tag
                html_files_enhanced = []
                for root, _, files in os.walk(deploy_path):
                    for file in files:
                        if file.endswith('.html'):
                            html_file_path = os.path.join(root, file)
                            try:
                                with open(
                                    html_file_path, 'r', encoding='utf-8'
                                ) as f:
                                    original_content = f.read()

                                with open(
                                    html_file_path, 'w', encoding='utf-8'
                                ) as f:
                                    f.write(original_content)

                                html_files_enhanced.append(
                                    os.path.relpath(
                                        html_file_path, deploy_path
                                    )
                                )
                            except Exception as e:
                                logger.warning(
                                    f"Failed to enhance {html_file_path}: {e}"
                                )

                # Serve the enhanced folder
                server_result = self._serve_static_files(temp_dir, port)

                if server_result['success']:
                    # Build URLs with localhost fallback
                    local_url = server_result["server_url"]
                    if subdirectory:
                        local_url += f"/{subdirectory}"

                    # Custom domain URL (if provided)
                    custom_url = (
                        self._build_custom_url(domain, subdirectory)
                        if domain
                        else None
                    )

                    # Localhost fallback URL
                    localhost_url = f"http://localhost:{port}"
                    if subdirectory:
                        localhost_url += f"/{subdirectory}"

                    # Build message with all access options
                    message = 'Folder deployed successfully!\n'
                    message += f'  • Local access: {local_url}\n'
                    message += f'  • Localhost fallback: {localhost_url}'

                    if custom_url:
                        message += f'\n  • Custom domain: {custom_url}'

                    if self.add_branding_tag:
                        message += f'\n  • Branding: "{self.tag_text}" tag '
                        message += (
                            f'added to {len(html_files_enhanced)} HTML files'
                        )

                    server_result.update(
                        {
                            'original_folder': folder_path,
                            'enhanced_folder': deploy_path,
                            'html_files_enhanced': html_files_enhanced,
                            'local_url': local_url,
                            'localhost_url': localhost_url,
                            'custom_url': custom_url,
                            'domain': domain,
                            'subdirectory': subdirectory,
                            'branding_tag_added': True,
                            'message': message,
                        }
                    )

                return server_result
            else:
                # Check for index.html
                index_html = os.path.join(folder_path, 'index.html')
                if not os.path.exists(index_html):
                    logger.warning(f'No index.html found in {folder_path}')

                # Handle subdirectory for original folder deployment
                if subdirectory:
                    temp_dir = tempfile.mkdtemp(prefix="web_deploy_")
                    deploy_base = os.path.join(temp_dir, subdirectory)
                    shutil.copytree(
                        folder_path, deploy_base, dirs_exist_ok=True
                    )
                    deploy_path = temp_dir
                else:
                    deploy_path = folder_path

                # Serve the folder
                server_result = self._serve_static_files(deploy_path, port)

                if server_result['success']:
                    # Build URLs with localhost fallback
                    local_url = server_result["server_url"]
                    if subdirectory:
                        local_url += f"/{subdirectory}"

                    # Custom domain URL (if provided)
                    custom_url = (
                        self._build_custom_url(domain, subdirectory)
                        if domain
                        else None
                    )

                    # Localhost fallback URL
                    localhost_url = f"http://localhost:{port}"
                    if subdirectory:
                        localhost_url += f"/{subdirectory}"

                    # Build message with all access options
                    message = 'Folder deployed successfully!\n'
                    message += f'  • Local access: {local_url}\n'
                    message += f'  • Localhost fallback: {localhost_url}'

                    if custom_url:
                        message += f'\n  • Custom domain: {custom_url}'

                    server_result.update(
                        {
                            'local_url': local_url,
                            'localhost_url': localhost_url,
                            'custom_url': custom_url,
                            'domain': domain,
                            'subdirectory': subdirectory,
                            'message': message,
                            'branding_tag_added': False,
                        }
                    )

                return server_result

        except Exception as e:
            # Clean up temp directory on error
            if (
                'temp_dir' in locals()
                and temp_dir
                and os.path.exists(temp_dir)
            ):
                try:
                    shutil.rmtree(temp_dir)
                except Exception:
                    pass
            logger.error(f"Error deploying folder: {e}")
            return {'success': False, 'error': str(e)}

    def _deploy_folder_to_remote_server(
        self,
        folder_path: str,
        subdirectory: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> Dict[str, Any]:
        r"""Deploy folder to remote server via API.

        Args:
            folder_path (str): Path to the folder to deploy
            subdirectory (Optional[str]): Subdirectory path for deployment
            domain (Optional[str]): Custom domain

        Returns:
            Dict[str, Any]: Deployment result
        """
        try:
            import tempfile
            import zipfile

            import requests

            # Validate subdirectory
            subdirectory = self._validate_subdirectory(subdirectory)

            # Create a temporary zip file of the folder
            with tempfile.NamedTemporaryFile(
                suffix='.zip', delete=False
            ) as temp_zip:
                zip_path = temp_zip.name

            try:
                # Create zip archive
                with zipfile.ZipFile(
                    zip_path, 'w', zipfile.ZIP_DEFLATED
                ) as zipf:
                    for root, _, files in os.walk(folder_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            # Calculate relative path within the archive
                            arcname = os.path.relpath(file_path, folder_path)
                            zipf.write(file_path, arcname)

                # Read zip file as base64
                with open(zip_path, 'rb') as f:
                    zip_data = base64.b64encode(f.read()).decode('utf-8')

                # Prepare deployment data
                deploy_data = {
                    "deployment_type": "folder",
                    "folder_data": zip_data,
                    "subdirectory": subdirectory,
                    "domain": domain,
                    "timestamp": time.time(),
                }

                # Add logo data if custom logo is specified
                if self.logo_path and os.path.exists(self.logo_path):
                    try:
                        logo_ext = os.path.splitext(self.logo_path)[1]
                        logo_filename = f"custom_logo{logo_ext}"

                        with open(self.logo_path, 'rb') as logo_file:
                            logo_data = base64.b64encode(
                                logo_file.read()
                            ).decode('utf-8')

                        deploy_data.update(
                            {
                                "logo_data": logo_data,
                                "logo_ext": logo_ext,
                                "logo_filename": logo_filename,
                            }
                        )
                    except Exception as logo_error:
                        logger.warning(
                            f"Failed to process custom logo: {logo_error}"
                        )

                # Send to remote server API
                api_url = f"http://{self.remote_server_ip}:{self.remote_server_port}/api/deploy"

                response = requests.post(
                    api_url,
                    json=deploy_data,
                    timeout=self.timeout
                    or 60,  # Extended timeout for folder uploads
                    allow_redirects=False,
                    headers={'Content-Type': 'application/json'},
                )

                if response.status_code == 200:
                    result = response.json()

                    # Build URLs
                    base_url = f"http://{self.remote_server_ip}:{self.remote_server_port}"
                    deployed_url = (
                        f"{base_url}/{subdirectory}/"
                        if subdirectory
                        else base_url
                    )

                    return {
                        'success': True,
                        'remote_url': deployed_url,
                        'server_ip': self.remote_server_ip,
                        'subdirectory': subdirectory,
                        'domain': domain,
                        'message': (
                            f'Successfully deployed folder to remote server!\n'
                            f'  • Access URL: {deployed_url}\n'
                            f'  • Server: '
                            f'{self.remote_server_ip}:{self.remote_server_port}'
                        ),
                        'branding_tag_added': self.add_branding_tag,
                        'logo_processed': result.get('logo_processed', False),
                    }
                else:
                    return {
                        'success': False,
                        'error': (
                            f'Remote folder deployment failed: '
                            f'HTTP {response.status_code}'
                        ),
                    }

            finally:
                # Clean up temporary zip file
                if os.path.exists(zip_path):
                    os.unlink(zip_path)

        except ImportError:
            return {
                'success': False,
                'error': 'Remote deployment requires requests library. '
                'Install with: pip install requests',
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Remote folder deployment error: {e!s}',
            }

    def stop_server(self, port: int) -> Dict[str, Any]:
        r"""Stop a running server on the specified port.

        Args:
            port (int): Port of the server to stop.

        Returns:
            Dict[str, Any]: Result of stopping the server.
        """
        try:
            # Validate port
            port = self._validate_port(port)
            # First check persistent registry for servers
            self._load_server_registry()

            if port not in self.server_instances:
                # Check if there's a process running on this port by PID
                if os.path.exists(self.server_registry_file):
                    with open(self.server_registry_file, 'r') as f:
                        data = json.load(f)
                        port_str = str(port)
                        if port_str in data:
                            pid = data[port_str].get('pid')
                            if pid and self._is_process_running(pid):
                                try:
                                    os.kill(pid, 15)  # SIGTERM
                                    # Remove from registry
                                    del data[port_str]
                                    with open(
                                        self.server_registry_file, 'w'
                                    ) as f:
                                        json.dump(data, f, indent=2)
                                    return {
                                        'success': True,
                                        'port': port,
                                        'message': (
                                            f'Server on port {port} stopped '
                                            f'successfully (from registry)'
                                        ),
                                    }
                                except Exception as e:
                                    logger.error(
                                        f"Error stopping server by PID: {e}"
                                    )

                return {
                    'success': False,
                    'error': f'No server running on port {port}',
                }

            server_info = self.server_instances[port]
            if isinstance(server_info, dict):
                process = server_info.get('process')
                pid = server_info.get('pid')

                # Stop the main server process
                if process:
                    process.terminate()
                    process.wait(
                        timeout=5
                    )  # Wait for process to terminate gracefully
                elif pid and self._is_process_running(pid):
                    os.kill(pid, 15)  # SIGTERM

            else:
                # Handle old-style direct process objects
                server_info.terminate()
                server_info.wait(timeout=5)

            del self.server_instances[port]
            self._save_server_registry()

            return {
                'success': True,
                'port': port,
                'message': f'Server on port {port} stopped successfully',
            }

        except subprocess.TimeoutExpired:
            if isinstance(server_info, dict):
                process = server_info.get('process')

                if process:
                    process.kill()
                    process.wait(timeout=5)
            else:
                server_info.kill()
                server_info.wait(timeout=5)
            del self.server_instances[port]
            self._save_server_registry()
            return {
                'success': True,
                'port': port,
                'message': f'Server on port {port} stopped after timeout',
            }
        except Exception as e:
            logger.error(f"Error stopping server: {e}")
            return {'success': False, 'error': str(e)}

    def list_running_servers(self) -> Dict[str, Any]:
        r"""List all currently running servers.

        Returns:
            Dict[str, Any]: Information about running servers
        """
        try:
            self._load_server_registry()

            running_servers = []
            current_time = time.time()

            for port, server_info in self.server_instances.items():
                if isinstance(server_info, dict):
                    start_time = server_info.get('start_time', 0)
                    running_time = current_time - start_time

                    running_servers.append(
                        {
                            'port': port,
                            'pid': server_info.get('pid'),
                            'directory': server_info.get('directory'),
                            'start_time': start_time,
                            'running_time': running_time,
                            'url': f'http://localhost:{port}',
                        }
                    )

            return {
                'success': True,
                'servers': running_servers,
                'total_servers': len(running_servers),
            }

        except Exception as e:
            logger.error(f"Error listing servers: {e}")
            return {'success': False, 'error': str(e)}

    def get_tools(self) -> List[FunctionTool]:
        r"""Get all available tools from the WebDeployToolkit."""
        return [
            FunctionTool(self.deploy_html_content),
            FunctionTool(self.deploy_folder),
            FunctionTool(self.stop_server),
            FunctionTool(self.list_running_servers),
        ]
