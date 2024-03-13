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
from rich.table import Table
from camel.cli.utils import get_service_laddr
from camel.termui import ui


@click.command()
def list():
    """
    List all running LLMs
    """

    laddr = get_service_laddr()
    url = f"http://{laddr}/v1/models"
    resp = requests.get(url)
    if resp.status_code == 200:
        running_model_list = resp.json()
        # TODO: add highlight
        display_models_in_table(running_model_list)
    else:
        ui.error("Failed to fetch running model list")

def display_models_in_table(model_list):
    table = Table(title="Running models")
    table.add_column("Model", justify="left", style="cyan", no_wrap=True)
    table.add_column("Basename", justify="left", style="magenta")
    table.add_column("Serving engine", justify="right", style="green")

    for model in model_list.values():
        table.add_row(
            model["alias"],
            model["basename"],
            model["serving_engine"]
        )

    ui.echo(table)