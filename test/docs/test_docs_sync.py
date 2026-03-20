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
    REPO_ROOT / ".camel/skills/docs-incremental-update/scripts/"
    "auto_sync_docs_with_chatagent.py",
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
        "\ncamel/agents/chat_agent.py\n\ncamel/models/base_model.py\n",
        encoding="utf-8",
    )

    changed_files = doc_code_map._read_path_list(path_list)

    assert changed_files == [
        "camel/agents/chat_agent.py",
        "camel/models/base_model.py",
    ]


def test_filter_changed_python_files_keeps_all_python_paths():
    changed_files = [
        "camel/agents/chat_agent.py",
        "camel/models/base_model.py",
        "docs/mintlify/key_modules/agents.mdx",
        "services/doc_sync.py",
        "tests/test_docs.py",
        "camel/agents/README.md",
    ]

    filtered = auto_sync_docs._filter_changed_python_files(changed_files)

    assert filtered == [
        "camel/agents/chat_agent.py",
        "camel/models/base_model.py",
        "services/doc_sync.py",
        "tests/test_docs.py",
    ]


def test_build_user_message_includes_target_doc_and_changed_files():
    message = auto_sync_docs._build_user_message(
        Path("docs/mintlify/key_modules/runtimes.mdx"),
        [
            "camel/runtimes/base.py",
            "camel/runtimes/docker_runtime.py",
        ],
    )

    assert "## Target doc" in message
    assert "docs/mintlify/key_modules/runtimes.mdx" in message
    assert "## Changed Python files for this run (optional context)" in message
    assert "camel/runtimes/base.py" in message
    assert "camel/runtimes/docker_runtime.py" in message
    assert "any relevant code" in message


def test_write_agent_response_log_appends_entries(tmp_path):
    auto_sync_docs._write_agent_response_log(
        tmp_path,
        Path("docs/mintlify/mcp/example.mdx"),
        "UPDATED",
        "UPDATED",
    )

    log_path = tmp_path / "terminal_logs" / "agent_response.log"

    assert log_path.exists()
    content = log_path.read_text(encoding="utf-8")
    assert "UPDATED docs/mintlify/mcp/example.mdx" in content
    assert content.rstrip().endswith("UPDATED")
