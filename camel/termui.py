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
import enum
from typing import Any

from rich.console import Console
from rich.theme import Theme

DEFAULT_THEME = {
    "primary": "cyan",
    "success": "green",
    "warning": "yellow",
    "error": "red",
    "info": "blue",
    "req": "bold green",
}

_console = Console(highlight=False, theme=Theme(DEFAULT_THEME))
_err_console = Console(stderr=True, theme=Theme(DEFAULT_THEME))


class Verbosity(enum.IntEnum):
    QUIET = -1
    NORMAL = 0
    DETAIL = 1
    DEBUG = 2


class UI:
    """
    Rich text terminal UI object.
    """

    def __init__(self, verbosity: Verbosity = Verbosity.NORMAL) -> None:
        self.verbosity = verbosity
        self.console = _console
        self.err_console = _err_console

    def echo(
        self,
        message: Any = "",
        err: bool = False,
        verbosity: Verbosity = Verbosity.QUIET,
        **kwargs: Any,
    ) -> None:
        """
        print message via rich console.
        Args:
            message (str): message to print with rich markup,
                defaults to ""
            err (bool): if true print to stderr,
                defaults to False
            verbosity (Verbosity): verbosity level to print message,
                default to QUIET
        """
        if self.verbosity >= verbosity:
            console = _err_console if err else _console
            if not console.is_interactive:
                kwargs.setdefault("crop", False)
                kwargs.setdefault("overflow", "ignore")
            console.print(message, **kwargs)

    # TODO: add a logging method

    def info(
        self, message: str, verbosity: Verbosity = Verbosity.QUIET
    ) -> None:
        """Print a message as info to stdout."""
        self.echo(
            f"[info]INFO:[/] [dim]{message}[/]", err=True, verbosity=verbosity
        )

    def warn(
        self, message: str, verbosity: Verbosity = Verbosity.QUIET
    ) -> None:
        """Print a message as warning to stdout."""
        self.echo(
            f"[error]WARNING:[/] {message}", err=True, verbosity=verbosity
        )

    def error(
        self, message: str, verbosity: Verbosity = Verbosity.QUIET
    ) -> None:
        """Print a message as error to stdout."""
        self.echo(
            f"[error]WARNING:[/] {message}", err=True, verbosity=verbosity
        )


ui = UI()
