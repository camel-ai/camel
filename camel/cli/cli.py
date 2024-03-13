# =========== Copyright 2023 @ camel_cli-AI.org. All Rights Reserved. ===========
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
# =========== Copyright 2023 @ camel_cli-AI.org. All Rights Reserved. ===========

import click
from .commands.add import add
from .commands.chat import chat
from .commands.exit import exit
from .commands.init import init
from .commands.launch import launch
from .commands.list import list
from .commands.setup import setup
from .commands.show import show
from .commands.status import status
from .commands.stop import stop

@click.group()
def camel_cli():
    pass

camel_cli.add_command(add)
camel_cli.add_command(launch)
camel_cli.add_command(chat)
camel_cli.add_command(exit)
camel_cli.add_command(init)
camel_cli.add_command(list)
camel_cli.add_command(show)
camel_cli.add_command(setup)
camel_cli.add_command(status)
camel_cli.add_command(stop)
