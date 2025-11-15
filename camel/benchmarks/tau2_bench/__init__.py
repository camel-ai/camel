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
"""Tau2-Bench benchmark integration for CAMEL."""

import sys as _sys

# Register alias before importing submodules so vendored tau2 loads first.
from .benchmark import Tau2BenchBenchmark

__all__ = ["Tau2BenchBenchmark"]

_PACKAGE_NAME = __name__
_SYS_MODULES = _sys.modules
_SYS_MODULES.setdefault("tau2_bench", _SYS_MODULES[_PACKAGE_NAME])

try:
    from . import tau2 as _vendored_tau2
except Exception:  # pragma: no cover - defensive
    pass
else:
    _SYS_MODULES["tau2"] = _vendored_tau2
