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
import shutil
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
            timeout (Optional[float]): Command timeout in seconds
            add_branding_tag (bool): Whether to add brand tag to deployed pages
            logo_path (str): Path to custom logo file (SVG, PNG, JPG, ICO).
                (default: .../misc/favicon.png)
            tag_text (str): Text to display in the tag
                (default: "Created by CAMEL")
            tag_url (str): URL to open when tag is clicked
                (default: "https://github.com/camel-ai/camel")
            remote_server_ip (Optional[str]): Remote server IP for deployment
                (default: None - use local deployment)
            remote_server_port (int): Remote server port
                (default: 8080)
        """
        super().__init__()
        self.timeout = timeout
        self.server_instances: Dict[int, Any] = {}  # Track running servers
        self.add_branding_tag = add_branding_tag
        self.logo_path = logo_path
        self.tag_text = tag_text
        self.tag_url = tag_url
        self.remote_server_ip = remote_server_ip
        self.remote_server_port = remote_server_port
        self.server_registry_file = os.path.join(
            tempfile.gettempdir(), "web_deploy_servers.json"
        )
        self._load_server_registry()

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
        custom_url = f"http://{domain}:8080"
        if subdirectory:
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
        r"""Get the default Eigent logo as data URI.

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

    def _generate_eigent_tag(self) -> str:
        r"""Generate the HTML/CSS/JS for the branded floating tag.

        Returns:
            str: Complete HTML code for the branded tag
        """
        # Load the logo from the specified path
        logo_data_uri = self._load_logo_as_data_uri(self.logo_path)

        return f"""
<style>
#eigent-floating-ball {{
  position: fixed;
  bottom: 20px;
  right: 20px;
  padding: 10px 12px;
  background: #333333;
  border-radius: 12px;
  display: flex;
  align-items: center;
  color: #F8F8F8;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
  z-index: 9999;
  transition: all 0.3s ease;
  overflow: hidden;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}}

#eigent-floating-ball:hover {{
  transform: translateY(-2px);
  background: #444444;
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
}}

.eigent-ball-content {{
  display: flex;
  align-items: center;
  gap: 8px;
}}

  .eigent-logo {{
   width: 24px;
   height: 24px;
   background-image: url("{logo_data_uri}");
   background-repeat: no-repeat;
   background-position: center;
   background-size: cover;
 }}

.eigent-ball-text {{
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
}}

.eigent-close-icon {{
  margin-left: 8px;
  font-size: 16px;
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  cursor: pointer;
  opacity: 0.7;
  transition: opacity 0.2s ease;
}}

.eigent-close-icon:hover {{
  opacity: 1;
  background: rgba(255, 255, 255, 0.1);
}}
</style>
 <div id="eigent-floating-ball">
   <div class="eigent-ball-content">
     <div class="eigent-logo"></div>
     <span class="eigent-ball-text">{self.tag_text}</span>
   </div>
   <div class="eigent-close-icon">x</div>
 </div>
<script>
// Initialize Eigent floating ball functionality
function initEigentFloatingBall() {{
  const ball = document.getElementById('eigent-floating-ball');
  if (!ball) return;

  // Initial animation
  ball.style.opacity = '0';
  ball.style.transform = 'translateY(20px)';

  setTimeout(() => {{
    ball.style.opacity = '1';
    ball.style.transform = 'translateY(0)';
  }}, 500);

     // Handle logo click
   const ballContent = ball.querySelector('.eigent-ball-content');
   ballContent.addEventListener('click', function (e) {{
     e.stopPropagation();
     window.open('{self.tag_url}', '_blank');
     ball.style.transform = 'scale(0.95)';
     setTimeout(() => {{
       ball.style.transform = 'scale(1)';
     }}, 100);
   }});

  // Handle close button click
  const closeIcon = ball.querySelector('.eigent-close-icon');
  closeIcon.addEventListener('click', function (e) {{
    e.stopPropagation();
    ball.style.opacity = '0';
    ball.style.transform = 'translateY(20px)';

    setTimeout(() => {{
      ball.style.display = 'none';
    }}, 300);
  }});
}}

// Initialize when DOM is ready
if (document.readyState === 'loading') {{
  document.addEventListener('DOMContentLoaded', initEigentFloatingBall);
}} else {{
  initEigentFloatingBall();
}}
</script>"""  # noqa: E501

    def _inject_eigent_tag(self, html_content: str) -> str:
        r"""Inject branded tag into HTML content.

        Args:
            html_content (str): Original HTML content

        Returns:
            str: HTML content with branded tag injected
        """
        if not self.add_branding_tag:
            return html_content

        branded_tag = self._generate_eigent_tag()

        # Try to inject before closing body tag
        if '</body>' in html_content:
            return html_content.replace('</body>', f'{branded_tag}\n</body>')

        # If no body tag, append to end
        return html_content + branded_tag

    def init_react_project(
        self,
        project_name: str,
        template: str = "typescript",
        directory: Optional[str] = None,
    ) -> Dict[str, Any]:
        r"""Initialize a new React project using create-react-app.

        Args:
            project_name (str): Name of the React project
            template (str): Template to use ('typescript', 'javascript')
            directory (Optional[str]): Directory to create project in
                (default: current directory)

        Returns:
            Dict[str, Any]: Result with project path and status
        """
        try:
            work_dir = directory or os.getcwd()
            project_path = os.path.join(work_dir, project_name)

            # Check if project already exists
            if os.path.exists(project_path):
                return {
                    'success': False,
                    'error': f'Project directory {project_name} already '
                    f'exists',
                }

            # Prepare create-react-app command
            cmd = ["npx", "create-react-app", project_name]
            if template == "typescript":
                cmd.extend(["--template", "typescript"])

            logger.info(f"Creating React project: {' '.join(cmd)}")

            # Execute command
            result = subprocess.run(
                cmd,
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            if result.returncode != 0:
                return {
                    'success': False,
                    'error': f'Failed to create React project: '
                    f'{result.stderr}',
                }

            return {
                'success': True,
                'project_path': project_path,
                'project_name': project_name,
                'template': template,
                'message': f'React project {project_name} created '
                f'successfully at {project_path}',
            }

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': f'Project creation timed out after '
                f'{self.timeout} seconds',
            }
        except Exception as e:
            logger.error(f"Error initializing React project: {e}")
            return {'success': False, 'error': str(e)}

    def build_react_project(self, project_path: str) -> Dict[str, Any]:
        r"""Build a React project.

        Args:
            project_path (str): Path to the React project directory

        Returns:
            Dict[str, Any]: Build result with output directory path
        """
        try:
            if not os.path.exists(project_path):
                return {
                    'success': False,
                    'error': f'Project path {project_path} does not exist',
                }

            package_json_path = os.path.join(project_path, 'package.json')
            if not os.path.exists(package_json_path):
                return {
                    'success': False,
                    'error': 'package.json not found. '
                    'Is this a valid React project?',
                }

            # Install dependencies if node_modules doesn't exist
            node_modules_path = os.path.join(project_path, 'node_modules')
            if not os.path.exists(node_modules_path):
                logger.info("Installing dependencies...")
                install_result = subprocess.run(
                    ["npm", "install"],
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                )

                if install_result.returncode != 0:
                    return {
                        'success': False,
                        'error': f'Failed to install dependencies: '
                        f'{install_result.stderr}',
                    }

            # Build the project
            logger.info("Building React project...")
            build_result = subprocess.run(
                ["npm", "run", "build"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            if build_result.returncode != 0:
                return {
                    'success': False,
                    'error': f'Build failed: {build_result.stderr}',
                }

            # Find build output directory
            build_dir = os.path.join(project_path, 'build')
            if not os.path.exists(build_dir):
                build_dir = os.path.join(project_path, 'dist')
                if not os.path.exists(build_dir):
                    return {
                        'success': False,
                        'error': 'Build output directory not found',
                    }

            return {
                'success': True,
                'build_path': build_dir,
                'project_path': project_path,
                'message': f'React project built successfully. '
                f'Output: {build_dir}',
            }

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': f'Build process timed out after '
                f'{self.timeout} seconds',
            }
        except Exception as e:
            logger.error(f"Error building React project: {e}")
            return {'success': False, 'error': str(e)}

    def deploy_html_content(
        self,
        html_content: str,
        file_name: str = "index.html",
        port: int = 8000,
        domain: Optional[str] = None,
        subdirectory: Optional[str] = None,
    ) -> Dict[str, Any]:
        r"""Deploy HTML content to a local server or remote server.

        Args:
            html_content (str): HTML content to deploy
            file_name (str): Name for the HTML file (default: 'index.html')
            port (int): Port to serve on (default: 8000)
            domain (Optional[str]): Custom domain to access the content
                (e.g., 'example.com')
            subdirectory (Optional[str]): Subdirectory path for multi-user
                deployment (e.g., 'user123')

        Returns:
            Dict[str, Any]: Deployment result with server URL and custom domain
                info
        """
        try:
            # Check if remote deployment is configured
            if self.remote_server_ip:
                return self._deploy_to_remote_server(
                    html_content, subdirectory, domain
                )
            else:
                return self._deploy_to_local_server(
                    html_content, file_name, port, domain, subdirectory
                )

        except Exception as e:
            print(f"Error deploying HTML content: {e}")
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
            import time

            import requests

            # Inject branding tag
            enhanced_html = self._inject_eigent_tag(html_content)

            # Prepare deployment data
            deploy_data = {
                "html_content": enhanced_html,
                "subdirectory": subdirectory,
                "domain": domain,
                "timestamp": time.time(),
            }

            # Send to remote server API
            api_url = f"http://{self.remote_server_ip}:{self.remote_server_port}/api/deploy"

            response = requests.post(api_url, json=deploy_data, timeout=30)

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
        # Inject Eigent tag into HTML content
        enhanced_html = self._inject_eigent_tag(html_content)
        try:
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
                f.write(enhanced_html)

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

            # Check if port is already in use
            if port in self.server_instances:
                return {
                    'success': False,
                    'error': f'Port {port} is already in use by this toolkit',
                }

            # Start http.server as a background process
            process = subprocess.Popen(
                ["python3", "-m", "http.server", str(port)],
                cwd=directory,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            
            # Store both process and metadata for persistence
            self.server_instances[port] = {
                'process': process,
                'pid': process.pid,
                'start_time': time.time(),
                'directory': directory,
            }
            self._save_server_registry()

            import time

            time.sleep(1)  # Wait a moment for server to start

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
            folder_path (str): Path to the folder to deploy
            port (int): Port to serve on (default: 8000)
            domain (Optional[str]): Custom domain to access the content
                (e.g., 'example.com')
            subdirectory (Optional[str]): Subdirectory path for multi-user
                deployment (e.g., 'user123')

        Returns:
            Dict[str, Any]: Deployment result with custom domain info
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

                                enhanced_content = self._inject_eigent_tag(
                                    original_content
                                )

                                with open(
                                    html_file_path, 'w', encoding='utf-8'
                                ) as f:
                                    f.write(enhanced_content)

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
            logger.error(f"Error deploying folder: {e}")
            return {'success': False, 'error': str(e)}

    def stop_server(self, port: int) -> Dict[str, Any]:
        r"""Stop a running server on the specified port.

        Args:
            port (int): Port of the server to stop

        Returns:
            Dict[str, Any]: Result of stopping the server
        """
        try:
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
                                    with open(self.server_registry_file, 'w') as f:
                                        json.dump(data, f, indent=2)
                                    return {
                                        'success': True,
                                        'port': port,
                                        'message': f'Server on port {port} stopped successfully (from registry)',
                                    }
                                except Exception as e:
                                    logger.error(f"Error stopping server by PID: {e}")
                
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
                    process.wait(timeout=5)  # Wait for process to terminate gracefully
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
                    
                    running_servers.append({
                        'port': port,
                        'pid': server_info.get('pid'),
                        'directory': server_info.get('directory'),
                        'start_time': start_time,
                        'running_time': running_time,
                        'url': f'http://localhost:{port}',
                    })
            
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
            FunctionTool(self.init_react_project),
            FunctionTool(self.build_react_project),
            FunctionTool(self.deploy_html_content),
            FunctionTool(self.deploy_folder),
            FunctionTool(self.stop_server),
            FunctionTool(self.list_running_servers),
        ]
