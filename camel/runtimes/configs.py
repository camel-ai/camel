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
from typing import Dict, List, Optional, Union

from pydantic import BaseModel


class TaskConfig(BaseModel):
    r"""A configuration for a task to run a command inside the container.

    Arttributes:
        cmd (str or list): Command to be executed
        stdout (bool): Attach to stdout. (default: :obj: `True`)
        stderr (bool): Attach to stderr. (default: :obj: `True`)
        stdin (bool): Attach to stdin. (default: :obj: `False`)
        tty (bool): Allocate a pseudo-TTY. (default: :obj: `False`)
        privileged (bool): Run as privileged. (default: :obj: `False`)
        user (str): User to execute command as. (default: :obj: `""`)
        detach (bool): If true, detach from the exec command.
            (default: :obj: `False`)
        stream (bool): Stream response data. (default: :obj: `False`)
        socket (bool): Return the connection socket to allow custom
            read/write operations. (default: :obj: `False`)
        environment (dict or list): A dictionary or a list of strings in
            the following format ``["PASSWORD=xxx"]`` or
            ``{"PASSWORD": "xxx"}``. (default: :obj: `None`)
        workdir (str): Path to working directory for this exec session.
            (default: :obj: `None`)
        demux (bool): Return stdout and stderr separately. (default: :obj:
            `False`)
    """

    cmd: Union[str, List[str]]
    stdout: bool = True
    stderr: bool = True
    stdin: bool = False
    tty: bool = False
    privileged: bool = False
    user: str = ""
    detach: bool = False
    stream: bool = False
    socket: bool = False
    environment: Optional[Union[Dict[str, str], List[str]]] = None
    workdir: Optional[str] = None
    demux: bool = False
