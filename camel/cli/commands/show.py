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
from rich.table import Table

from camel.cli.utils import (
    get_models,
    get_service_laddr,
    get_service_pid,
    sizeof_fmt,
)
from camel.termui import ui


@click.command()
@click.argument(
    "property",
    type=click.Choice(
        ["pid", "address", "local-models"], case_sensitive=False
    ),
)
def show(property):
    """
    show service properties
    """
    property = property.lower()
    if property == "pid":
        pid = get_service_pid()
        ui.echo(pid)

    elif property == "address":
        laddr = get_service_laddr()
        ui.echo(f"[link=http://{laddr}]{laddr}[/link]")

    if property == "local-models":
        repo_dic = get_models()
        repo_dic = dict(sorted(repo_dic.items()))
        display_models_in_table(repo_dic)


def display_models_in_table(repo_dic):
    table = Table(title="Available local models")
    table.add_column("Model", justify="left", style="cyan", no_wrap=True)
    table.add_column("Size", justify="right", style="green")

    for repo in repo_dic.values():
        table.add_row(repo["repo_id"], sizeof_fmt(repo["size_on_disk"]))

    ui.echo(table)
