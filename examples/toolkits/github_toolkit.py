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
import os
import sys
from typing import TYPE_CHECKING

import asyncio

from camel.toolkits import GithubToolkit
from camel.toolkits.mcp_toolkit import _MCPServer

if TYPE_CHECKING:
    from mcp import ClientSession


gt = GithubToolkit(repo_name="camel-ai/camel")

# Retrieve a list of all file paths within the camel GitHub repository
paths = gt.get_all_file_paths()
print(paths)
"""
===============================================================================
['.container/.env.example', '.container/Dockerfile', '.container/README.md', '.
container/docker-compose.yaml', '.container/minimal_build/Dockerfile', '.
github/ISSUE_TEMPLATE/bug_report.yml', '.github/ISSUE_TEMPLATE/discussions.
yml', '.github/ISSUE_TEMPLATE/feature_request.yml', '.github/ISSUE_TEMPLATE/
questions.yml', '.github/PULL_REQUEST_TEMPLATE.md', '.github/actions/
camel_install/action.yml', '.github/workflows/build_package.yml', '.github/
workflows/documentation.yml', '.github/workflows/pre_commit.yml', '.github/
workflows/publish_release.yml', '.github/workflows/pytest_apps.yml', '.github/
workflows/pytest_package.yml', '.gitignore', '.pre-commit-config.yaml', '.
style.yapf', 'CONTRIBUTING.md', 'LICENSE', 'Makefile', 'README.md', 'apps/
agents/README.md', 'apps/agents/agents.py', 'apps/agents/test/test_agents.py', 
'apps/agents/test/test_text_utils.py', 'apps/agents/text_utils.py', 'apps/
common/auto_zip.py', 'apps/common/test/test_archive_1.zip', 'apps/common/test/
test_auto_zip.py', 'apps/data_explorer/.gitignore', 'apps/data_explorer/README.
md', 'apps/data_explorer/data_explorer.py', 'apps/data_explorer/downloader.
py', 'apps/data_explorer/loader.py', 'apps/data_explorer/test/
test_data_explorer.py', 'apps/data_explorer/test/test_loader.py', 'apps/
dilemma/database_connection.py', 'apps/dilemma/dilemma.py', 'apps/dilemma/
requirements.txt', 'camel/__init__.py', 'camel/agents/__init__.py', 'camel/
agents/base.py', 'camel/agents/chat_agent.py', 'camel/agents/critic_agent.py', 
'camel/agents/deductive_reasoner_agent.py',...
===============================================================================
"""

# Retrieve the content of a specific file in the repository
content = gt.retrieve_file_content("camel/agents/chat_agent.py")
print(content[:1000])
"""
===============================================================================
from __future__ import annotations

import json
import logging
import re
import uuid
from collections import defaultdict
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    Union,
)

from openai.types.chat import ChatCompletionMessageToolCall
f
===============================================================================
"""


async def run_example():
    server = _MCPServer(
        command_or_url=sys.executable,
        args=[__file__, "--server"],
        env={"GITHUB_ACCESS_TOKEN": os.environ.get("GITHUB_ACCESS_TOKEN")}
    )
    await server.connect()

    session: "ClientSession" = server._session

    issue_list_result = await session.call_tool(
        name="get_issue_list",
        arguments={"state": "open"},
    )
    print("Open Issues (via MCP):")
    print(issue_list_result.content[0].text[:500])

    # 通过 MCP 调用工具包中的 retrieve_file_content 方法
    file_content_result = await session.call_tool(
        name="retrieve_file_content",
        arguments={"file_path": "README.md"},
    )
    print("\nContent of README.md (via MCP):")
    print(file_content_result.content[0].text[:500])

    await server.disconnect()


if __name__ == "__main__":
    if "--server" in sys.argv:
        gt.mcp.run("stdio")
    else:
        asyncio.run(run_example())
