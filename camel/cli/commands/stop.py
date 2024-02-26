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

import click
import requests
from camel.cli.utils import get_service_laddr
from camel.termui import ui

@click.command()
@click.argument("alias")
def stop(alias):
    """
    Stop a running LLM
    """
    laddr = get_service_laddr()
    url = f"http://{laddr}/v1/delete"
    json_data = {
        "alias": alias,
    }
    resp = requests.delete(url, json=json_data)
    if resp.status_code == 200:
        # TODO: add highlight
        ui.info(f"Model {alias} removed")
    else:
        ui.error(f"Failed to remove model {alias}")
