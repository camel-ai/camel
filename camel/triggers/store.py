# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
r"""Persistence backends for trigger specs.

The :class:`BaseTriggerStore` interface is deliberately tiny so alternative
backends (a database, Redis, ...) can be dropped in. Two backends ship by
default: an in-memory store (tests / ephemeral) and an atomic JSON-file store
(survives process restarts).
"""

import json
import os
import tempfile
import threading
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from camel.logger import get_logger

from .models import TriggerSpec

logger = get_logger(__name__)


class BaseTriggerStore(ABC):
    r"""Abstract CRUD store for :class:`TriggerSpec` objects."""

    @abstractmethod
    def add(self, spec: TriggerSpec) -> None:
        r"""Persist a new trigger spec."""

    @abstractmethod
    def get(self, trigger_id: str) -> Optional[TriggerSpec]:
        r"""Fetch a spec by id, or ``None`` if absent."""

    @abstractmethod
    def list(self) -> List[TriggerSpec]:
        r"""Return all stored specs."""

    @abstractmethod
    def update(self, spec: TriggerSpec) -> None:
        r"""Persist changes to an existing spec."""

    @abstractmethod
    def delete(self, trigger_id: str) -> bool:
        r"""Remove a spec by id; return ``True`` if it existed."""


class InMemoryTriggerStore(BaseTriggerStore):
    r"""Non-persistent store backed by a dict. Suitable for tests."""

    def __init__(self) -> None:
        self._data: Dict[str, TriggerSpec] = {}
        self._lock = threading.Lock()

    def add(self, spec: TriggerSpec) -> None:
        with self._lock:
            self._data[spec.id] = spec.model_copy(deep=True)

    def get(self, trigger_id: str) -> Optional[TriggerSpec]:
        with self._lock:
            spec = self._data.get(trigger_id)
            return spec.model_copy(deep=True) if spec else None

    def list(self) -> List[TriggerSpec]:
        with self._lock:
            return [s.model_copy(deep=True) for s in self._data.values()]

    def update(self, spec: TriggerSpec) -> None:
        with self._lock:
            if spec.id not in self._data:
                raise KeyError(f"Trigger {spec.id} not found.")
            self._data[spec.id] = spec.model_copy(deep=True)

    def delete(self, trigger_id: str) -> bool:
        with self._lock:
            return self._data.pop(trigger_id, None) is not None


class JsonFileTriggerStore(BaseTriggerStore):
    r"""Store backed by a single JSON file, written atomically.

    Args:
        path (str): Path to the JSON file. Created on first write. Its parent
            directory is created if missing.
    """

    def __init__(self, path: str) -> None:
        self.path = path
        self._lock = threading.Lock()
        parent = os.path.dirname(os.path.abspath(path))
        if parent:
            os.makedirs(parent, exist_ok=True)

    def _load_unlocked(self) -> Dict[str, TriggerSpec]:
        if not os.path.exists(self.path):
            return {}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to read trigger store {self.path}: {e}")
            return {}
        out: Dict[str, TriggerSpec] = {}
        for item in raw:
            try:
                spec = TriggerSpec.model_validate(item)
                out[spec.id] = spec
            except Exception as e:
                logger.warning(f"Skipping invalid trigger record: {e}")
        return out

    def _save_unlocked(self, data: Dict[str, TriggerSpec]) -> None:
        payload = [s.model_dump(mode="json") for s in data.values()]
        # Atomic write: tmp file in same dir, then os.replace.
        dir_name = os.path.dirname(os.path.abspath(self.path))
        fd, tmp = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            os.replace(tmp, self.path)
        except Exception:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    def add(self, spec: TriggerSpec) -> None:
        with self._lock:
            data = self._load_unlocked()
            data[spec.id] = spec
            self._save_unlocked(data)

    def get(self, trigger_id: str) -> Optional[TriggerSpec]:
        with self._lock:
            return self._load_unlocked().get(trigger_id)

    def list(self) -> List[TriggerSpec]:
        with self._lock:
            return list(self._load_unlocked().values())

    def update(self, spec: TriggerSpec) -> None:
        with self._lock:
            data = self._load_unlocked()
            if spec.id not in data:
                raise KeyError(f"Trigger {spec.id} not found.")
            data[spec.id] = spec
            self._save_unlocked(data)

    def delete(self, trigger_id: str) -> bool:
        with self._lock:
            data = self._load_unlocked()
            existed = data.pop(trigger_id, None) is not None
            if existed:
                self._save_unlocked(data)
            return existed
