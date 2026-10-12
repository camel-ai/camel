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

import pytest


def test_all_exports_from_camel():
    # Simulate `from camel import *` and capture the resulting namespace
    ns = {}
    exec("from camel import *", ns)

    assert 'set_log_level' in ns
    assert 'enable_logging' in ns
    assert 'disable_logging' in ns
    assert 'camel' not in ns


def test_all_exports_type():
    import camel

    assert isinstance(camel.__all__, list)

    for item in camel.__all__:
        assert isinstance(item, str)


def _star_import(module_name):
    ns = {}
    exec(f"from {module_name} import *", ns)
    return ns


def test_datagen_evol_instruct_all_exports_resolve():
    # tqdm is imported unconditionally by camel.datagen.evol_instruct but is
    # not a base dependency; on a bare install the module cannot be imported
    # at all, so the __all__ invariant below is not reachable.
    pytest.importorskip("tqdm")

    import camel.datagen.evol_instruct as module

    ns = _star_import(module.__name__)
    missing = [name for name in module.__all__ if name not in ns]
    assert not missing, (
        f"{module.__name__}.__all__ advertises names that a star import "
        f"cannot resolve: {missing}"
    )


def test_utils_all_exports_resolve():
    import camel.utils as module

    ns = _star_import(module.__name__)
    missing = [name for name in module.__all__ if name not in ns]
    assert not missing, (
        f"{module.__name__}.__all__ advertises names that a star import "
        f"cannot resolve: {missing}"
    )
