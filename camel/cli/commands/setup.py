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

import subprocess
from pathlib import Path

import click

from camel.termui import ui


@click.command()
def setup():
    """
    quick camel cli tool
    """
    file_dir = Path(__file__)
    ui.info("Configuring CAMEL CLI...")
    systemd_setup_script_dir = (
        f"{file_dir.parents[2]}/.script/setup_systemd_service.sh"
    )

    try:
        subprocess.run(["bash", f"{systemd_setup_script_dir}"])
    except Exception:
        ui.error("Failed to configure CAMEL CLI")
    else:
        ui.info("CAMEL CLI configured successfully")
