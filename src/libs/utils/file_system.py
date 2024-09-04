from pathlib import Path
import shutil
from typing import Union

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
