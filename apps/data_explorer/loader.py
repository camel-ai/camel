"""
Everything related to parsing the data JSONs into UI-compatible format.
"""

import glob
import json
import os
import re
from typing import Any, Dict, List, Tuple, Union

from tqdm import tqdm

ChatHistory = Dict[str, Any]
ParsedChatHistory = Dict[str, Any]
AllChats = Dict[str, Any]


def parse(raw_chat: ChatHistory) -> Union[ParsedChatHistory, None]:
    """ Gets the JSON raw chat data, validates it and transforms
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


def load_data(path: str) -> AllChats:
    """ Load all JSONs from a folder and parse them.

    Args:
        path (str): path to the folder with JSONs.

    Returns:
        AllChats: A dictionary with all possible assistant and
        user roles and the matrix of chats.
    """

    filt = os.path.join(path, "*.json")
    files = glob.glob(filt)
    parsed_list = []
    for file_name in tqdm(files):
        with open(file_name, "rb") as f:
            try:
                raw_chat = json.load(f)
            except Exception as ex:
                print(str(ex))
                continue
            parsed = parse(raw_chat)
            if parsed is None:
                continue
            parsed_list.append(parsed)

    assistant_roles = set()
    user_roles = set()
    for parsed in parsed_list:
        assistant_roles.add(parsed['assistant_role'])
        user_roles.add(parsed['user_role'])
    assistant_roles = list(sorted(assistant_roles))
    user_roles = list(sorted(user_roles))
    matrix: Dict[Tuple[str, str], List[Dict]] = dict()
    for parsed in parsed_list:
        key = (parsed['assistant_role'], parsed['user_role'])
        original_task = parsed['original_task']
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


if __name__ == "__main__":
    data = load_data("DATA/")
