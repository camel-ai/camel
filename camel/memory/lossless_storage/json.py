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

import json
from pathlib import Path
from typing import Any, Dict, List

from camel.memory.lossless_storage.base import LosslessStorage


class JsonStorage(LosslessStorage):

    def __init__(self, path: Path = Path("chat_history.json")):
        self.json_path = path
        self.json_path.touch()

    def save(self, records: List[Dict[str, Any]]) -> None:
        with self.json_path.open("a") as f:
            f.writelines([json.dumps(r) for r in records])

    def load(self) -> List[Dict[str, Any]]:
        with self.json_path.open("r") as f:
            return [json.loads(r) for r in f.readlines()]

    def clear(self) -> None:
        with self.json_path.open("w"):
            pass
