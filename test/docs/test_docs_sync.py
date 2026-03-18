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

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


doc_code_map = _load_module(
    "test_doc_code_map_module",
    REPO_ROOT / "docs/scripts/docs_sync/doc_code_map.py",
)
auto_sync_docs = _load_module(
    "test_auto_sync_docs_module",
    REPO_ROOT
    / ".camel/skills/docs-incremental-update/scripts/auto_sync_docs_with_chatagent.py",
)


def test_impacted_docs_detect_matching_source_changes(tmp_path):
    docs_root = tmp_path / "docs" / "mintlify" / "key_modules"
    source_root = tmp_path / "camel" / "runtimes"
    docs_root.mkdir(parents=True)
    source_root.mkdir(parents=True)

    doc_path = docs_root / "runtimes.mdx"
    doc_path.write_text(
        "---\n"
        'doc_code_map:\n'
        '  - "camel/runtimes/**/*.py"\n'
        "---\n"
        "body\n",
        encoding="utf-8",
    )
    (source_root / "remote.py").write_text(
        "print('hello')\n", encoding="utf-8"
    )

    doc_maps = doc_code_map._collect_doc_maps([docs_root])
    impacted = doc_code_map._impacted_docs(
        doc_maps=doc_maps,
        changed_files=["camel/runtimes/remote.py"],
        repo_root=tmp_path,
    )

    assert impacted == [doc_path]


def test_read_path_list_file(tmp_path):
    path_list = tmp_path / "changed_files.txt"
    path_list.write_text(
        "\ncamel/agents/chat_agent.py\n\nservices/doc_sync.py\n",
        encoding="utf-8",
    )

    changed_files = doc_code_map._read_path_list(path_list)

    assert changed_files == [
        "camel/agents/chat_agent.py",
        "services/doc_sync.py",
    ]


def test_resolve_code_respects_budget_after_truncation(tmp_path, monkeypatch):
    docs_root = tmp_path / "docs"
    source_root = tmp_path / "camel" / "runtimes"
    docs_root.mkdir(parents=True)
    source_root.mkdir(parents=True)

    doc_path = docs_root / "runtimes.mdx"
    doc_path.write_text(
        "---\n"
        'doc_code_map:\n'
        '  - "camel/runtimes/*.py"\n'
        "---\n"
        "body\n",
        encoding="utf-8",
    )
    (source_root / "large.py").write_text("a" * 400, encoding="utf-8")
    (source_root / "second.py").write_text("b" * 40, encoding="utf-8")

    monkeypatch.setattr(auto_sync_docs, "MAX_CODE_CHARS", 260)

    resolved = auto_sync_docs._resolve_code(doc_path, tmp_path)

    assert len(resolved) <= auto_sync_docs.MAX_CODE_CHARS
    assert "... (truncated)" in resolved
    assert "# --- camel/runtimes/second.py ---" not in resolved


def test_filter_changed_python_files_keeps_only_supported_roots():
    changed_files = [
        "camel/agents/chat_agent.py",
        "services/doc_sync.py",
        "docs/mintlify/key_modules/agents.mdx",
        "tests/test_docs.py",
        "camel/agents/README.md",
    ]

    filtered = auto_sync_docs._filter_changed_python_files(changed_files)

    assert filtered == [
        "camel/agents/chat_agent.py",
        "services/doc_sync.py",
    ]


def test_relevant_changed_python_files_match_doc_code_map(tmp_path):
    docs_root = tmp_path / "docs"
    source_root = tmp_path / "camel" / "runtimes"
    docs_root.mkdir(parents=True)
    source_root.mkdir(parents=True)

    doc_path = docs_root / "runtimes.mdx"
    doc_path.write_text(
        "---\n"
        'doc_code_map:\n'
        '  - "camel/runtimes/*.py"\n'
        "---\n"
        "body\n",
        encoding="utf-8",
    )
    (source_root / "remote.py").write_text(
        "print('hello')\n", encoding="utf-8"
    )
    (source_root / "local.py").write_text("print('world')\n", encoding="utf-8")

    relevant = auto_sync_docs._relevant_changed_python_files(
        doc_path,
        tmp_path,
        [
            "camel/runtimes/remote.py",
            "camel/agents/chat_agent.py",
        ],
    )

    assert relevant == ["camel/runtimes/remote.py"]


def test_should_skip_update_recognizes_sentinel():
    assert auto_sync_docs._should_skip_update("__NO_CHANGES__")
    assert auto_sync_docs._should_skip_update("  __NO_CHANGES__\n")
    assert not auto_sync_docs._should_skip_update("updated body")


def test_doc_was_updated_in_place_detects_direct_edit():
    original = "---\ntitle: Demo\n---\nbody\n"
    current = "---\ntitle: Demo\n---\nupdated body\n"
    frontmatter = "---\ntitle: Demo\n---\n"

    assert auto_sync_docs._doc_was_updated_in_place(
        original, current, frontmatter
    )


def test_doc_was_updated_in_place_rejects_frontmatter_change():
    original = "---\ntitle: Demo\n---\nbody\n"
    current = "---\ntitle: Changed\n---\nupdated body\n"
    frontmatter = "---\ntitle: Demo\n---\n"

    with pytest.raises(RuntimeError):
        auto_sync_docs._doc_was_updated_in_place(
            original, current, frontmatter
        )
