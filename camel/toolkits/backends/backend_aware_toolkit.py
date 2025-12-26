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
from __future__ import annotations

from typing import Optional

from camel.toolkits.base import BaseToolkit

from .base import BaseBackend
from .filesystem_backend import FilesystemBackend


class BackendAwareToolkit(BaseToolkit):
    r"""Base class for toolkits that operate with a storage backend.

    This class provides a standard mechanism for toolkits that need access
    to a persistent or stateful storage backend. A backend can be explicitly
    provided, or a default filesystem-backed implementation will be created
    and rooted at the resolved working directory.

    The working directory is resolved in the following order:
    1. The provided ``working_directory`` argument.
    2. The ``CAMEL_WORKDIR`` environment variable.
    3. A local ``./camel_working_dir`` directory.
    """

    def __init__(
        self,
        *,
        backend: Optional[BaseBackend] = None,
        working_directory: Optional[str] = None,
        default_encoding: str = "utf-8",
        backup_enabled: bool = True,
        timeout: Optional[float] = None,
    ) -> None:
        r"""Initialize the backend-aware toolkit.

        Args:
            backend (BaseBackend, optional): The storage backend used by the
                toolkit. If not provided, a ``FilesystemBackend`` is created
                and rooted at the resolved working directory.
                (default: :obj:`None`)
            working_directory (str, optional): Path to the working directory
                used for filesystem-backed storage. If not provided, the
                directory is resolved from environment variables or defaults.
                (default: :obj:`None`)
            default_encoding (str): Default text encoding used when reading
                or writing files through the backend.
                (default: :obj:`"utf-8"`)
            backup_enabled (bool): Whether to enable backup behavior when
                overwriting files in filesystem-backed storage.
                (default: :obj:`True`)
            timeout (float, optional): Timeout in seconds applied to toolkit
                operations.
                (default: :obj:`None`)
        """
        super().__init__(timeout=timeout)

        import os
        from pathlib import Path

        # Standard working_directory resolution (same logic as FileToolkit)
        if working_directory:
            self.working_directory = Path(working_directory).resolve()
        else:
            camel_workdir = os.environ.get("CAMEL_WORKDIR")
            if camel_workdir:
                self.working_directory = Path(camel_workdir).resolve()
            else:
                self.working_directory = Path("./camel_working_dir").resolve()

        self.working_directory.mkdir(parents=True, exist_ok=True)
        self.default_encoding = default_encoding
        self.backup_enabled = backup_enabled

        # Backend setup
        if backend is None:
            self.backend: BaseBackend = FilesystemBackend(
                root_dir=self.working_directory,
                default_encoding=self.default_encoding,
                backup_enabled=self.backup_enabled,
            )
        else:
            self.backend = backend
