import glob
import json
import os
from pathlib import Path
from typing import Any

import toml
import yaml


def expand_paths(paths: list[str], extension: str | None = None) -> list[str]:
    """Expand directories and glob patterns into a list of files.

    Args:
        paths: List of paths to directories or glob patterns
        extension: Optional file extension to filter for (e.g., '.json', '.txt')

    Returns:
        List of files
    """
    files = []
    for path in paths:
        path_obj = Path(path)

        if path_obj.is_file():
            files.append(str(path_obj))
        elif path_obj.is_dir():
            # Find all files in directory
            for file_path in path_obj.rglob("*"):
                if file_path.is_file():
                    files.append(str(file_path))
        else:
            # Try as glob pattern
            matched_files = glob.glob(path)
            if matched_files:
                files.extend(matched_files)
            else:
                print(f"Warning: No files found for pattern: {path}")

    # Remove duplicates and sort
    all_files = sorted(list(set(files)))

    # Filter by extension if specified
    if extension is not None:
        all_files = [f for f in all_files if Path(f).suffix == extension]

    return all_files


# NOTE: When using the results of load_file(), we need to pay attention to the case
# where the value is None when loading from json or yaml, the key will be missing in
# toml since there is no "null" in toml.


def load_file(path: str | Path, **kwargs: Any) -> dict[str, Any]:
    """Load the content of a file from a path based on the file extension.

    Args:
        path: The path to the file to load.
        **kwargs: Additional keyword arguments to pass to the file reader.

    Returns:
        The data dictionary loaded from the file.
    """
    path = Path(path)
    if path.suffix == ".json":
        with open(path, "r") as fp:
            data = json.load(fp, **kwargs)
    elif path.suffix == ".yaml" or path.suffix == ".yml":
        with open(path, "r") as fp:
            data = yaml.load(fp, Loader=yaml.SafeLoader, **kwargs)
    elif path.suffix == ".toml":
        with open(path, "r") as fp:
            data = toml.load(fp, **kwargs)
    elif path.suffix == ".txt" or path.suffix == ".md":
        encoding = kwargs.pop("encoding", None)
        if len(kwargs) > 0:
            raise ValueError(f"Unsupported keyword arguments: {kwargs}")
        with open(path, "r", encoding=encoding) as fp:
            data = fp.read()
    else:
        raise ValueError(f"Unsupported file extension: {path}")
    return data


def dump_file(path: str | Path, data: dict[str, Any], **kwargs: Any) -> None:
    """Dump data content to a file based on the file extension.

    Args:
        path: The path to the file to dump the data to.
        data: The data dictionary to dump to the file.
        **kwargs: Additional keyword arguments to pass to the file writer.
    """
    path = Path(path)
    os.makedirs(path.parent, exist_ok=True)  # make dir if not exists

    if path.suffix == ".json":
        with open(path, "w") as fp:
            json.dump(data, fp, **kwargs)
    elif path.suffix == ".yaml" or path.suffix == ".yml":
        with open(path, "w") as fp:
            yaml.dump(data, fp, **kwargs)
    elif path.suffix == ".toml":
        # toml cannot dump the Enum values, so we need to convert them to strings
        data_str = json.dumps(data)
        new_data = json.loads(data_str)
        with open(path, "w") as fp:
            toml.dump(new_data, fp, **kwargs)
    elif path.suffix == ".txt" or path.suffix == ".md":
        encoding = kwargs.pop("encoding", None)
        if len(kwargs) > 0:
            raise ValueError(f"Unsupported keyword arguments: {kwargs}")
        with open(path, "w", encoding=encoding) as fp:
            fp.write(data)
    else:
        raise ValueError(f"Unsupported file extension: {path}")
