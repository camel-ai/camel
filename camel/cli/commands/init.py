# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========

import os
import sys
import socket
import configparser
from pathlib import Path
import subprocess
import click
from camel.termui import ui
from camel.cli.utils import get_service_pid, service_is_alive


@click.command()
@click.option("--host", type=str, default=None, help='host address')
@click.option("--port", "-p", type=str, default=None, help='port number')
@click.option("--daemon", "-d", default=False, is_flag=True, help="run as systemd daemon in background")
def init(host, port, daemon):
    """
    start camel openai api-compatible server
    """
    # read local config file
    file_dir = Path(__file__)
    local_config = configparser.ConfigParser()
    config_dir = os.path.expanduser("~/.config/systemd/user/camel.conf")
    local_config.read(config_dir)

    # host priority: flag > camel.conf > Default 127.0.0.1
    if host is None:
        host = local_config["Service"].get("host", "127.0.0.1")

    if port is None:
        port = local_config["Service"].get("port", "8000")
    # check if port is in use
    if if_port_in_use(host, int(port)):
        ui.warn(f"Port {port} is in use, trying to find an available port...")
        port = find_available_port(host)

    if daemon:
        # check if camel.service unit file exists
        dot_config_dir = os.path.expanduser("~/.config/systemd/user/")
        if not any(os.path.exists(parent + "camel.service")
                for parent in (dot_config_dir,
                               "/etc/systemd/user/")
            ):
            raise FileNotFoundError(
                "Deamon mode enabled but systemd unit file `camel.service` file not found"
            )
        # check if log directory exists
        local_dir = os.path.expanduser("~/.local")
        log_dir = local_dir + "/camel/logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # check if service is running
        if service_is_alive():
            ui.warn("camel daemon already running")
            return

            # refresh systemd EnvironmentFile
        # TODO: check whether the service start successfully before move on
        subprocess.run(["systemctl", "--user", "start", "camel"])
        pid = get_service_pid()
        ui.info(f"camel service (pid {pid}) running on [link=http://{host}:{port}]{host}:{port}[/link]")

        with open(config_dir, "w") as f:  #be careful configparser convert all keys to lower case
            local_config["Service"]["host"] = host
            local_config["Service"]["port"] = str(port)
            local_config.write(f)
        f.close()
    else:
        subprocess.run([
            f"{sys.executable}", f"{file_dir.parents[2]}/serve/openai_api_server.py",
            "--host", host,
            "--port", str(port)
        ])

    # write to local config file
        
def if_port_in_use(host: str, port: int) -> bool:
    """
    Check if the port (in our project, usually the default 8000) is
    in use. If so, return a random available port number.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0

def find_available_port(host: str) -> int:
    """
    Find an available port number.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return s.getsockname()[1]