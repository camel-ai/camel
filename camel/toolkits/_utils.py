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
# =========
import functools
import inspect

from camel.logger import get_logger
logger = get_logger(__name__)


def add_reason_field(func):
    """
    Decorator to enable reasoning for tool functions.
    1.It modifies the function's signature to add a 'reason' parameter.
    2.The 'reason' argument is a string describing why the tool is being called
      and it is added to the function docstring.
    3.It wraps the original function to ensure
      its return value includes a 'reason' key.

    Note: This decorator can only be applied to
          functions with a return type of Dict.

    """
    sig = inspect.signature(func)
    # Check return annotation
    if sig.return_annotation is inspect.Signature.empty or (
        getattr(sig.return_annotation, '__origin__', None) is not dict
        and sig.return_annotation is not dict
    ):
        logger.info(
            f"add_reason_field: Function '{func.__name__}' "
            "does not have return type Dict. "
            "Reasoning will not be applied."
        )
        return func

    # Patch signature
    params = list(sig.parameters.values())
    # Only add reason if not already present
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

    # Patch docstring
    doc = func.__doc__ or ""
    lines = doc.splitlines()
    # Add reason to Args section
    if "Args:" in doc:
        for i, line in enumerate(lines):
            if "Args:" in line:
                indent = line[: line.index("Args:")]
                reason_doc = (
                    f"{indent}    reason (str): The reason why this "
                    + "tool is called."
                )
                lines.insert(i + 1, reason_doc)
                break
    else:
        lines.extend(
            [
                "",
                "Args:",
                "    reason (str): The reason why this tool is called.",
            ]
        )

    # Add reason to Returns section
    returns_idx = None
    for i, line in enumerate(lines):
        if "Returns:" in line:
            returns_idx = i
            indent = line[: line.index("Returns:")]
            break

    if returns_idx is not None:
        # Find where Returns section ends by checking indentation
        end_idx = len(lines)
        for j in range(returns_idx + 1, len(lines)):
            line = lines[j]
            if line.strip() == "":
                continue
            if not line.startswith(indent + " "):
                end_idx = j
                break
        # Remove existing reason lines
        filtered = []
        for i, line in enumerate(lines):
            if '"reason"' not in line and "'reason'" not in line:
                filtered.append(line)
            elif i < returns_idx or i >= end_idx:
                filtered.append(line)

        lines = filtered

        # Recalculate end_idx after filtering
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

        # Append reason line at end of Returns section
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
        # No need to check type here, as enforced by decorator
        result["reason"] = reason
        return result
    wrapper.__signature__ = new_sig
    wrapper.__doc__ = doc
    return wrapper
