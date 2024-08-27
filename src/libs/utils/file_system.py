from pathlib import Path
import shutil
from typing import Union


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
