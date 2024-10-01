from pathlib import Path
from typing import Union, List, Optional
import shutil
import mimetypes
import fnmatch

import pyperclip


def delete_directory_recursive(directory_path: Union[str, Path]) -> bool:
    try:
        path: Path = Path(directory_path)
        if path.exists() and path.is_dir():
            shutil.rmtree(path)
            return True
        return False
    except Exception as e:
        print(f"An error occurred while trying to delete the directory: {e}")
        return False


def copy_to_clipboard(file_path: Path) -> dict[str, str]:
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
        pyperclip.copy(content)
        return {"message": "The file content was successfully copied to the clipboard", "success": True}
    except Exception:
        return {"message": "An error occurred while trying to copy the file content to the clipboard", "success": False}


def is_text_file_mimetype_or_allowed_file(file_path: Path, allowed_files: List[str]) -> bool:
    if is_text_file_mimetype(file_path) or file_path.name in allowed_files:
        return True

    return False


def is_text_file_mimetype(file_path: Path) -> bool:
    mime_type, _ = mimetypes.guess_type(file_path)

    if mime_type is None or not mime_type.startswith("text"):
        return False

    return True


def read_file_content(file_path: Path) -> Optional[str]:
    try:
        with open(file_path, "r", encoding="utf-8") as source_file:
            return source_file.read()
    except UnicodeDecodeError:
        return None
    except Exception as e:
        return f"Error reading file: {str(e)}"


def read_log_file(log_file) -> str:
    log_file.seek(0)
    return log_file.read()


def write_log_file(log_file, content: str) -> None:
    log_file.write(content)


def write_log_file_from_start(log_file, content: str) -> None:
    log_file.seek(0)
    log_file.truncate()
    write_log_file(log_file, content)


def is_path_directory(path: Path) -> bool:
    return path.is_dir()


def path_exists(path: Path) -> bool:
    return path.exists()


def get_files_match_pattern(directory: Path, pattern: str) -> List[Path]:
    return list(directory.rglob(pattern))


def get_gitignore_patters_list(project_root: Path) -> List[str]:
    gitignore_path = project_root / ".gitignore"

    if not gitignore_path.exists():
        return []

    with open(gitignore_path, "r") as f:
        patterns = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    return patterns


def should_ignore_file(file_path: Path, project_root: Path, ignore_patterns: List[str], allowed_files: List[str] = []) -> bool:
    if file_path.name in allowed_files:
        return False

    relative_path: Path = file_path.relative_to(project_root)

    for pattern in ignore_patterns:
        if fnmatch.fnmatch(str(relative_path), pattern) or fnmatch.fnmatch(relative_path.name, pattern):
            return True
        if pattern.endswith("/") and str(relative_path).startswith(pattern):
            return True
    return False
