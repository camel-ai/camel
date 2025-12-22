# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========

import functools
import inspect
from typing import Dict

from camel.logger import get_logger

logger = get_logger(__name__)


def add_reason_field(func):
    """
    Decorator to enable reasoning for tool functions.
    1. It modifies the function's signature to add a 'reason' parameter.
    2. The 'reason' argument is a string describing why the tool is
       being called and it is added to the function docstring.
    3. It wraps the original function to ensure its return value
       includes a 'reason' key.

    Note: This decorator can only be applied to
          functions with a return type of Dict.

    """
    sig = inspect.signature(func)

    def is_dict_type(annotation):
        if annotation is dict:
            return True
        if annotation is inspect.Signature.empty:
            return False
        origin = getattr(annotation, '__origin__', None)
        if origin is dict:
            return True
        if annotation is Dict or origin is Dict:
            return True
        return False

    if not is_dict_type(sig.return_annotation):
        logger.info(
            f"add_reason_field: Function '{func.__name__}' "
            "does not have return type Dict. "
            "Reasoning will not be applied."
        )
        return func

    params = list(sig.parameters.values())
    if "reason" not in sig.parameters:
        params.append(
            inspect.Parameter(
                "reason",
                inspect.Parameter.KEYWORD_ONLY,
                default="",
                annotation=str,
            )
        )
    new_sig = sig.replace(parameters=params)

    doc = func.__doc__ or ""
    lines = doc.splitlines()

    if "Args:" in doc:
        args_idx = None
        indent = None
        for i, line in enumerate(lines):
            if "Args:" in line:
                args_idx = i
                indent = line[: line.index("Args:")]
                break

        if args_idx is not None:
            insert_idx = args_idx + 1
            last_arg_idx = args_idx + 1
            for j in range(args_idx + 1, len(lines)):
                line = lines[j]
                if not line.startswith(indent + " "):
                    insert_idx = j
                    break
                if line.strip() != "":
                    last_arg_idx = j
                insert_idx = j + 1

            if last_arg_idx > args_idx:
                insert_idx = last_arg_idx + 1

            reason_doc = (
                f"{indent}    reason (str): The reason why this "
                + "tool is called."
            )
            lines.insert(insert_idx, reason_doc)
    else:
        lines.extend(
            [
                "",
                "Args:",
                "    reason (str): The reason why this tool is called.",
            ]
        )

    returns_idx = None
    for i, line in enumerate(lines):
        if "Returns:" in line:
            returns_idx = i
            indent = line[: line.index("Returns:")]
            break

    if returns_idx is not None:
        end_idx = len(lines)
        for j in range(returns_idx + 1, len(lines)):
            line = lines[j]
            if line.strip() == "":
                continue
            if not line.startswith(indent + " "):
                end_idx = j
                break

        filtered = []
        for i, line in enumerate(lines):
            if '"reason"' not in line and "'reason'" not in line:
                filtered.append(line)
            elif i < returns_idx or i >= end_idx:
                filtered.append(line)

        lines = filtered

        end_idx = len(lines)
        for j in range(returns_idx + 1, len(lines)):
            line = lines[j]
            if line.strip() == "":
                continue
            if not line.startswith(indent + " "):
                end_idx = j
                break

        while end_idx > returns_idx + 1 and lines[end_idx - 1].strip() == "":
            end_idx -= 1

        reason_line = f'{indent}        - "reason" (str): tool call reason.'
        lines.insert(end_idx, reason_line)
    elif "Returns:" not in doc:
        lines.extend(
            [
                "",
                "Returns:",
                "  dict: The result dictionary.",
                '        - "reason" (str): tool call reason.',
            ]
        )

    doc = "\n".join(lines)

    @functools.wraps(func)
    async def wrapper(*args, reason: str = "", **kwargs):
        result = await func(*args, **kwargs)
        result["reason"] = reason
        return result

    wrapper.__signature__ = new_sig
    wrapper.__doc__ = doc
    return wrapper
