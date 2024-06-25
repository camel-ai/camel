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

import click
import requests

from camel.cli.utils import get_service_laddr
from camel.termui import ui


@click.command()
@click.option("--alias", type=str, help="custom model name")
@click.option(
    "--vllm",
    is_flag=True,
    default=False,
    help="launch model using VLLM framework",
)
@click.argument("model")
def launch(model, alias, vllm):
    """
    Launch a local model
    """

    laddr = get_service_laddr()
    url = f"http://{laddr}/v1/register"
    json_data = {
        "model": model,
        "vllm": vllm,
        "alias": alias,
    }
    resp = requests.post(url, json=json_data)
    if resp.status_code == 201:
        basename = os.path.basename(model)
        # TODO: add highlight
        ui.info(
            f"Model {basename} {f'(renamed as {alias})' if alias else ''}"
            "launched successfully"
        )
    else:
        ui.error(f"Failed to launch model {model}")
