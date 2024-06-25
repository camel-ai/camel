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
import configparser
import os
import subprocess
import sys
from typing import Union

from huggingface_hub import scan_cache_dir

from camel.termui import ui

SERVICE_INACTIVE_ERROR_MSG = (
    "The camel daemon is inactive. "
    "Please initiate the service by running 'camel init --daemon'"
)


def sizeof_fmt(num, suffix="B"):
    for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
        if abs(num) < 1024.0:
            return f"{num:3.1f} {unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"


def service_is_alive() -> bool:
    service_status = (
        subprocess.run(
            ["systemctl", "--user", "is-active", "camel"], capture_output=True
        )
        .stdout.decode("utf-8")
        .strip()
    )

    return service_status == "active"


def get_service_pid() -> Union[int, None]:
    if service_is_alive():
        pid = (
            subprocess.check_output(
                [
                    "systemctl",
                    "--user",
                    "show",
                    "--property",
                    "MainPID",
                    "--value",
                    "camel",
                ]
            )
            .decode("utf-8")
            .strip()
        )

        return int(pid)
    else:
        ui.error(SERVICE_INACTIVE_ERROR_MSG)
        # TODO: or raise an OSError here?
        sys.exit(1)


def get_models():
    """
    return all availble cached models located in $HF_HUB_CACHE
    ref: https://huggingface.co/docs/huggingface_hub/package_reference/environment_variables
    """
    res = {
        repo.repo_id: {
            "repo_id": repo.repo_id,
            "repo_path": repo.repo_path,
            "size_on_disk": repo.size_on_disk,
        }
        for repo in scan_cache_dir().repos
        if repo.repo_type == "model"
    }
    return res


def get_service_laddr() -> Union[str, None]:
    if service_is_alive():
        local_config = configparser.ConfigParser()
        config_dir = os.path.expanduser("~/.config/systemd/user/camel.conf")
        local_config.read(config_dir)
        host = local_config["Service"].get("HOST")
        port = local_config["Service"].get("PORT")
        return f"{host}:{port}"
    else:
        ui.error(SERVICE_INACTIVE_ERROR_MSG)
        sys.exit(1)
