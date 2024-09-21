from pathlib import Path

"""
    Generates a marker string to separate file contents in the prompt log.

    Args:
        file_path (Path): The path of the file.
        project_root (Path): The root of the project for relative path calculation.

    Returns:
        str: The formatted marker string.
"""


def create_dashed_filename_marker(file_path: Path, project_root: Path, blank_lines=True) -> str:
    relative_path = file_path.relative_to(project_root)

    if blank_lines:
        return f"--- Filename {relative_path} ---\n\n"

    return f"--- Filename {relative_path} ---"
