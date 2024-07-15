# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
import json
import random
import re
import string
from pathlib import Path
from typing import Any, Dict, List, Union

import markdown
from bs4 import BeautifulSoup


def load_jsonl(file_path: Union[Path, str]) -> List[Dict[Any, Any]]:
    """
    Load data from a JSONL (JSON Lines) file.

    This function reads a JSONL file and returns its contents as
    a list of dictionaries. Each line in the file is expected to be a
    valid JSON object.

    Args:
        file_path (Union[Path, str]): The path to the JSONL file to be loaded.

    Returns:
        List[Dict[Any, Any]]: A list of dictionaries, where each
        dictionary represents a JSON object from a line in the file.

    Raises:
        JSONDecodeError: If a line in the file is not a valid JSON object.
        IOError: If there's an issue reading the file.
    """
    with open(file_path) as fin:
        lines = fin.readlines()
        tasks = []
        for line in lines:
            data = json.loads(line)
            tasks.append(data)
        return tasks


def encode_prompt(prompt_instructions: List[str]) -> str:
    """
    Encode multiple prompt instructions into a single string.

    This function takes a list of instructions and formats them into
    a numbered list within a single string prompt.

    Args:
        prompt_instructions (List[str]): A list of instruction strings
        to be encoded.

    Returns:
        str: A formatted string containing all instructions as a numbered list.

    Example:
        >>> instructions = ["Do task A", "Perform action B",
        "Analyze result C"]
        >>> encode_prompt(instructions)
        'Come up with a series of tasks:
        1. Do task A
        2. Perform action B
        3. Analyze result C
        4.'
    """
    prompt = "Come up with a series of tasks:\n"
    for idx, instruction in enumerate(prompt_instructions):
        instruction = re.sub(r"\s+", " ", instruction).strip().rstrip(":")
        prompt += f"{idx+1}. {instruction}\n"
    prompt += f"{len(prompt_instructions) + 1}."
    return prompt


def sample_machine_instructions(
    machine_instructions: List[str], similarities: Any, n: int
) -> List[str]:
    """
    Sample n machine instructions from a list of machine instructions.

    This function randomly selects a specified number of instructions
    from the provided list.

    Args:
        machine_instructions (List[str]): A list of machine instructions
        to sample from.
        similarities (Any): This parameter is not used in the function
        and can be ignored.
        n (int): The number of instructions to sample.

    Returns:
        List[str]: A list containing the randomly sampled instructions.

    Note:
        If n is greater than the length of machine_instructions,
        all instructions will be returned.
    """
    return random.sample(
        machine_instructions, min(n, len(machine_instructions))
    )


def find_word_in_string(w: str, s: str) -> Union[re.Match, None]:
    """
    Search for a whole word within a string.

    This function looks for the exact word 'w' in the string 's',
    ignoring case.

    Args:
        w (str): The word to search for.
        s (str): The string to search in.

    Returns:
        Union[re.Match, None]: A match object if the word is found,
        None otherwise.

    Example:
        >>> find_word_in_string("apple", "I have an Apple.")
        <re.Match object; span=(10, 15), match='Apple'>
        >>> find_word_in_string("app", "I have an Apple.")
        None
    """
    return re.compile(r'\b({0})\b'.format(w), flags=re.IGNORECASE).search(s)


def post_process_agent_system_response(
    response: Union[str, None],
) -> List[str]:
    """
    Process and filter the response from an agent system.

    Source: https://github.com/yizhongw/self-instruct

    This function takes a string response, splits it into
    individual instructions,
    and applies various filters to clean and validate each instruction.

    Args:
        response (Union[str, None]): The raw response string from
        the agent system.

    Returns:
        List[str]: A list of processed and filtered instructions.

    Filters applied:
    - Remove empty instructions
    - Remove instructions that are too short
        (<=3 words) or too long (>150 words)
    - Remove instructions containing specific keywords
        (e.g., "image", "file", "draw")
    - Remove instructions starting with "Write a program"
    - Remove instructions starting with punctuation or non-ASCII characters

    Note:
        If the input response is None, an empty list is returned.
    """
    if response is None:
        return []
    raw_instructions = re.split(r"\n\d+\s?\. ", response)
    instructions = []
    for inst in raw_instructions:
        inst = re.sub(r"\s+", " ", inst).strip()
        inst = inst.strip().capitalize()
        if inst == "":
            continue
        # filter out too short or too long instructions
        if len(inst.split()) <= 3 or len(inst.split()) > 150:
            continue
        # filter based on keywords that are not suitable for language models.
        if any(
            find_word_in_string(word, inst)
            for word in [
                "image",
                "images",
                "graph",
                "graphs",
                "picture",
                "pictures",
                "file",
                "files",
                "map",
                "maps",
                "draw",
                "plot",
                "go to",
            ]
        ):
            continue
        # We found that the model tends to add "write a program"
        # to some existing instructions, which lead to a lot of such
        # instructions.
        # And it's a bit comfusing whether the model need to write
        # a program or directly output the result.
        # Here we filter them out.
        # Note this is not a comprehensive filtering for all
        # programming instructions.
        if inst.startswith("Write a program"):
            continue
        # filter those starting with punctuation
        if inst[0] in string.punctuation:
            continue
        # filter those starting with non-english character
        if not inst[0].isascii():
            continue
        instructions.append(inst)

    return instructions


def md_to_text(md, do_md_to_text=True):
    if not do_md_to_text:
        return md
    assert md is not None, "Markdown is None"
    html = markdown.markdown(md)
    soup = BeautifulSoup(html, features='html.parser')
    return soup.get_text()
