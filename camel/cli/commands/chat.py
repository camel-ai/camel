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
@click.option("--model", help="model name", type=str, required=True)
@click.argument("messages")
def chat(model, messages):
    """
    Chat with a specific model
    """
    laddr = get_service_laddr()
    url = f"http://{laddr}/v1/chat/completions"
    json_data = {
        "model": model,
        "messages": [{
            "role": "user",
            "content": messages
        }]
    }
    resp = requests.post(url, json=json_data)
    # TODO: output format need to be unified, this one is not compatible with vllm output
    ui.echo(resp.json()[0])
