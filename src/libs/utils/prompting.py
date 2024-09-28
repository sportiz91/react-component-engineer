from pathlib import Path


def find_next_dashed_marker_position_in_content(content: str, file_marker: str) -> int:
    start_index: int = content.index(file_marker)
    next_marker_index: int = content.find("--- Filename", start_index + len(file_marker))

    if next_marker_index == -1:
        next_marker_index: int = len(content)

    return next_marker_index


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


def add_content_end_dashed_file_marker(content: str, next_marker_position: str, new_content: str) -> str:
    return content[:next_marker_position].rstrip() + "\n\n" + new_content + "\n\n" + content[next_marker_position:]


def add_content_to_end(content: str, file_marker: str, new_content: str) -> str:
    return content.rstrip() + f"\n\n{file_marker}\n\n{new_content}\n\n"


def update_content_dashed_marker(content: str, file_marker: str, new_content: str) -> str:
    if file_marker in content:
        # Find the existing content under the file marker
        start_index: int = content.index(file_marker) + len(file_marker) + 2  # +2 to account for the two newline characters after the marker
        end_index: int = find_next_dashed_marker_position_in_content(content, file_marker)
        existing_content: str = content[start_index:end_index].rstrip()
        # Append the new content to the existing content
        combined_content: str = existing_content + "\n" + new_content
        # Reconstruct the content with the combined content under the file marker
        return content[:start_index] + combined_content + "\n\n" + content[end_index:]

    return add_content_to_end(content, file_marker, new_content)
