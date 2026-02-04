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

from camel.runtimes import BaseRuntime
from camel.toolkits import FunctionTool


class _ConcreteRuntime(BaseRuntime):
    r"""Minimal concrete runtime for testing base cleanup/stop/context manager."""

    def __init__(self):
        super().__init__()
        self.cleanup_called = False

    def add(
        self,
        funcs: FunctionTool | list[FunctionTool],
        *args: object,
        **kwargs: object,
    ) -> "_ConcreteRuntime":
        if not isinstance(funcs, list):
            funcs = [funcs]
        for f in funcs:
            self.tools_map[f.get_function_name()] = f
        return self

    def reset(self, *args: object, **kwargs: object) -> "_ConcreteRuntime":
        return self

    def cleanup(self) -> None:
        self.cleanup_called = True


def test_base_runtime_cleanup_contract():
    r"""Test that a concrete runtime implements cleanup and it is callable."""
    runtime = _ConcreteRuntime()
    assert not runtime.cleanup_called
    runtime.cleanup()
    assert runtime.cleanup_called


def test_base_runtime_stop_calls_cleanup():
    r"""Test that stop() calls cleanup() and returns self."""
    runtime = _ConcreteRuntime()
    assert not runtime.cleanup_called
    result = runtime.stop()
    assert runtime.cleanup_called
    assert result is runtime


def test_base_runtime_context_manager_calls_cleanup():
    r"""Test that using the runtime as a context manager calls cleanup on exit."""
    runtime = _ConcreteRuntime()
    assert not runtime.cleanup_called
    with runtime:
        pass
    assert runtime.cleanup_called


def test_base_runtime_context_manager_returns_self():
    r"""Test that context manager __enter__ returns self."""
    runtime = _ConcreteRuntime()
    with runtime as r:
        assert r is runtime
