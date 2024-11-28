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
"""
Everything related to parsing the data JSONs into UI-compatible format.
"""

import glob
import os
import re
from typing import Any, Dict, Optional, Tuple, Union

from tqdm import tqdm

from apps.common.auto_zip import AutoZip

ChatHistory = Dict[str, Any]
ParsedChatHistory = Dict[str, Any]
AllChats = Dict[str, Any]
Datasets = Dict[str, AllChats]

REPO_ROOT = os.path.realpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "../..")
)


def parse(raw_chat: ChatHistory) -> Union[ParsedChatHistory, None]:
    """Gets the JSON raw chat data, validates it and transforms
        into an easy to work with form.

    Args:
        raw_chat (ChatHistory): In-memory loaded JSON data file.

    Returns:
        Union[ParsedChatHistory, None]: Parsed chat data or None
        if there were parsing errors.
    """

    if "role_1" not in raw_chat:
        return None

    role_1 = raw_chat["role_1"]
    if "_RoleType.ASSISTANT" not in role_1:
        return None
    assistant_role = role_1.split("_RoleType.ASSISTANT")
    if len(assistant_role) < 1:
        return None
    if len(assistant_role[0]) <= 0:
        return None
    assistant_role = assistant_role[0]

    role_2 = raw_chat["role_2"]
    if "_RoleType.USER" not in role_2:
        return None
    user_role = role_2.split("_RoleType.USER")
    if len(user_role) < 1:
        return None
    if len(user_role[0]) <= 0:
        return None
    user_role = user_role[0]

    original_task = raw_chat["original_task"]
    if len(original_task) <= 0:
        return None

    specified_task = raw_chat["specified_task"]
    if len(specified_task) <= 0:
        return None

    messages = dict()
    for key in raw_chat:
        match = re.search("message_(?P<number>[0-9]+)", key)
        if match:
            number = int(match.group("number"))
            messages[number] = raw_chat[key]

    return dict(
        assistant_role=assistant_role,
        user_role=user_role,
        original_task=original_task,
        specified_task=specified_task,
        messages=messages,
    )


def load_zip(zip_path: str) -> AllChats:
    """Load all JSONs from a zip file and parse them.

    Args:
        path (str): path to the ZIP file.

    Returns:
        AllChats: A dictionary with all possible assistant and
        user roles and the matrix of chats.
    """

    zip_inst = AutoZip(zip_path)
    parsed_list = []
    for raw_chat in tqdm(iter(zip_inst)):
        parsed = parse(raw_chat)
        if parsed is None:
            continue
        parsed_list.append(parsed)

    assistant_roles_set = set()
    user_roles_set = set()
    for parsed in parsed_list:
        assistant_roles_set.add(parsed['assistant_role'])
        user_roles_set.add(parsed['user_role'])
    assistant_roles = sorted(assistant_roles_set)
    user_roles = sorted(user_roles_set)
    matrix: Dict[Tuple[str, str], Dict[str, Dict]] = dict()
    for parsed in parsed_list:
        key = (parsed['assistant_role'], parsed['user_role'])
        original_task: str = parsed['original_task']
        new_item = {
            k: v
            for k, v in parsed.items()
            if k not in {'assistant_role', 'user_role', 'original_task'}
        }
        if key in matrix:
            matrix[key][original_task] = new_item
        else:
            matrix[key] = {original_task: new_item}

    return dict(
        assistant_roles=assistant_roles,
        user_roles=user_roles,
        matrix=matrix,
    )


def load_datasets(path: Optional[str] = None) -> Datasets:
    """Load all JSONs from a set of zip files and parse them.

    Args:
        path (str): path to the folder with ZIP datasets.

    Returns:
        Datasets: A dictionary of dataset name and dataset contents.
    """

    if path is None:
        path = os.path.join(REPO_ROOT, "datasets")

    filt = os.path.join(path, "*.zip")
    files = glob.glob(filt)
    datasets = {}
    for file_name in tqdm(files):
        name = os.path.splitext(os.path.basename(file_name))[0]
        datasets[name] = load_zip(file_name)
    return datasets
