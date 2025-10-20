from pathlib import Path
from typing import List


def parse_path_arguments(argv: List[str], repo_root: Path) -> List[str]:
    """
    Parse and validate path arguments from command line.

    Returns a list of normalized relative paths from repo root.
    Filters out paths that are outside the repository or cannot be resolved.

    Args:
        argv: List of path arguments from command line
        repo_root: Root path of the repository

    Returns:
        List of normalized relative paths from repo root
    """
    filter_paths = []
    for arg in argv:
        path = Path(arg)

        # Convert to absolute path
        if not path.is_absolute():
            path = Path.cwd() / path

        # Normalize the path
        try:
            path = path.resolve()
        except (OSError, RuntimeError):
            print(f"Warning: Cannot resolve path '{arg}', skipping")
            continue

        # Check if path is within repo
        try:
            rel_path = path.relative_to(repo_root)
            filter_paths.append(str(rel_path))
        except ValueError:
            print(f"Warning: Path '{arg}' is not within the repository, skipping")
            continue

    return filter_paths


def filter_dict_by_paths(
    data_dict: dict, filter_paths: List[str], path_filter_func
) -> dict:
    """
    Filter a dictionary by paths using a custom filter function.

    Args:
        data_dict: Dictionary to filter
        filter_paths: List of paths to match against
        path_filter_func: Function that takes (path, filter_paths) and returns bool

    Returns:
        Filtered dictionary
    """
    if not filter_paths:
        return data_dict

    filtered = {}
    for path, value in data_dict.items():
        if path_filter_func(path, filter_paths):
            filtered[path] = value
    return filtered


def path_matches_filter(file_path: str, filter_paths: List[str]) -> bool:
    """
    Check if a file path should be included based on filter paths.
    Returns True if the file_path matches any of the filter_paths.
    """
    file_path_parts = Path(file_path).parts

    for filter_path in filter_paths:
        filter_path_parts = Path(filter_path).parts

        # Exact match
        if file_path == filter_path:
            return True

        # Check if file is under a directory filter
        if len(file_path_parts) >= len(filter_path_parts):
            if file_path_parts[: len(filter_path_parts)] == filter_path_parts:
                return True

    return False
