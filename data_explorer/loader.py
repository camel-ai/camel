import os
import re
import glob
import json


def parse(data):
    if "role_1" not in data:
        return None

    role_1 = data["role_1"]
    if "_RoleType.ASSISTANT" not in role_1:
        return None
    assistant_role = role_1.split("_RoleType.ASSISTANT")
    if len(assistant_role) < 1:
        return None
    if len(assistant_role[0]) <= 0:
        return None
    assistant_role = assistant_role[0]

    role_2 = data["role_2"]
    if "_RoleType.USER" not in role_2:
        return None
    user_role = role_2.split("_RoleType.USER")
    if len(user_role) < 1:
        return None
    if len(user_role[0]) <= 0:
        return None
    user_role = user_role[0]

    original_task = data["original_task"]
    if len(original_task) <= 0:
        return None

    specified_task = data["specified_task"]
    if len(specified_task) <= 0:
        return None

    messages = dict()
    for key in data:
        match = re.search("message_(?P<number>[0-9]+)", key)
        if match:
            number = int(match.group("number"))
            messages[number] = data[key]

    return dict(
        assistant_role=assistant_role,
        user_role=user_role,
        original_task=original_task,
        specified_task=specified_task,
        messages=messages,
    )


def load_data(path="DATA"):
    filt = os.path.join(path, "*.json")
    files = glob.glob(filt)
    parsed_list = []
    for file_name in files:
        with open(file_name, "rb") as f:
            try:
                data = json.load(f)
            except Exception as ex:
                print(str(ex))
                continue
            parsed = parse(data)
            parsed_list.append(parsed)

    assistant_roles = set()
    user_roles = set()
    for parsed in parsed_list:
        assistant_roles.add(parsed['assistant_role'])
        user_roles.add(parsed['user_role'])
    assistant_roles = list(assistant_roles)
    user_roles = list(user_roles)
    matrix: dict[tuple[str, str], dict] = dict()
    for parsed in parsed_list:
        matrix[(parsed['assistant_role'], parsed['user_role'])] = \
            {k: v for k, v in parsed.items()
             if k not in {'assistant_role', 'user_role'}}
    return dict(
        assistant_roles=assistant_roles,
        user_roles=user_roles,
        matrix=matrix,
    )


if __name__ == "__main__":
    data = load_data()
    print("")
