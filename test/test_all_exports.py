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
import importlib

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


def test_core_classes_importable_from_root():
    """Verify that core public API classes are importable from the
    root camel package for agent discoverability."""
    import camel

    core_names = [
        'ChatAgent',
        'ModelFactory',
        'BaseMessage',
        'ModelType',
        'ModelPlatformType',
        'FunctionTool',
        'BaseToolkit',
        'RolePlaying',
        'Workforce',
        'ChatAgentResponse',
    ]
    for name in core_names:
        assert hasattr(
            camel, name
        ), f"camel.{name} should be importable from root package"


# Submodules whose __all__ entries should all resolve to real attributes.
_SUBMODULES_TO_CHECK = [
    'camel',
    'camel.agents',
    'camel.configs',
    'camel.loaders',
    'camel.memories',
    'camel.messages',
    'camel.models',
    'camel.prompts',
    'camel.responses',
    'camel.societies',
    'camel.storages',
    'camel.toolkits',
    'camel.types',
]


@pytest.mark.parametrize("module_name", _SUBMODULES_TO_CHECK)
def test_all_exports_are_resolvable(module_name):
    """Every name listed in a submodule's __all__ must be an attribute of
    that module. A mismatch means users (or agents) will hit an ImportError
    when they try ``from <module> import <name>``."""
    mod = importlib.import_module(module_name)
    all_names = getattr(mod, '__all__', None)
    if all_names is None:
        pytest.skip(f"{module_name} does not define __all__")
    missing = [n for n in all_names if not hasattr(mod, n)]
    assert not missing, (
        f"{module_name}.__all__ contains names that are not defined: "
        f"{missing}"
    )
