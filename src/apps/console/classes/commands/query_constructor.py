from pathlib import Path
from typing import Set, List, Any
import ast
import mimetypes
import fnmatch


from src.apps.console.classes.commands.base import BaseCommand
from src.libs.helpers.console import get_user_input
from src.libs.services.logger.logger import log

NAME: str = "prompt constructor"
DESCRIPTION: str = "Construct a prompt log file from given Python files or all files in specified folders"
PROJECT_ROOT: Path = Path(__file__).resolve().parents[5]
PROCESSED_FILES: Set[Path] = set()
ALLOWED_FILES: List[str] = [".gitignore", ".env.example"]


class PromptConstructorCommand(BaseCommand):
    name: str = NAME
    description: str = DESCRIPTION
    project_root: Path = PROJECT_ROOT
    processed_files: Set[Path] = PROCESSED_FILES

    async def execute(self, *args: Any, **kwargs: Any) -> None:
        self.ignore_patterns = self.parse_gitignore()
        self.log_ignored_patterns()

        mode = await get_user_input("Enter mode: ", choices=["all", "traverse"], default="all") or "all"
        self.set_mode(mode)

        prompt_log = self.project_root / "prompt.log"
        with open(prompt_log, "w") as log_file:
            if mode == "traverse":
                filename = await get_user_input("Enter the filename (e.g., src/apps/console/main.py): ")
                start_file = self.project_root / filename
                if not start_file.exists():
                    self.console.print(f"File {start_file} does not exist.", style="bold red")
                    return
                self.process_file(start_file, log_file)
            elif mode == "all":
                folder_paths = await get_user_input("Enter the folder paths (space-separated, e.g., src/apps/console src/libs): ")
                folders = [self.project_root / folder.strip() for folder in folder_paths.split()]
                self.process_multiple_folders(folders, log_file)
            else:
                self.console.print(f"Invalid mode: {mode}", style="bold red")
                return

        self.console.print(f"prompt log has been written to {prompt_log}", style="bold green")

    def parse_gitignore(self) -> List[str]:
        gitignore_path = self.project_root / ".gitignore"
        if not gitignore_path.exists():
            return []

        with open(gitignore_path, "r") as f:
            patterns = [line.strip() for line in f if line.strip() and not line.startswith("#")]

        return patterns

    def should_ignore(self, file_path: Path) -> bool:
        if file_path.name in ALLOWED_FILES:
            return False

        relative_path = file_path.relative_to(self.project_root)

        for pattern in self.ignore_patterns:
            if fnmatch.fnmatch(str(relative_path), pattern) or fnmatch.fnmatch(relative_path.name, pattern):
                return True
            if pattern.endswith("/") and str(relative_path).startswith(pattern):
                return True
        return False

    def process_multiple_folders(self, folders: List[Path], log_file) -> None:
        for folder in folders:
            if not folder.exists() or not folder.is_dir():
                self.console.print(f"Folder {folder} does not exist or is not a directory. Skipping.", style="bold yellow")
                continue
            self.process_folder(folder, log_file)
            log_file.write("\n")

    def process_folder(self, folder_path: Path, log_file) -> None:
        for file_path in folder_path.rglob("*"):
            if file_path.is_file() and not self.should_ignore(file_path):
                self.write_file_content(file_path, log_file)

    def write_file_content(self, file_path: Path, log_file) -> None:

        log("file_path.name")
        log(file_path.name)

        mime_type, _ = mimetypes.guess_type(file_path)

        log("mime_type")
        log(mime_type)

        if mime_type is None or not mime_type.startswith("text"):
            if file_path.name not in ALLOWED_FILES:
                return

        try:
            with open(file_path, "r", encoding="utf-8") as source_file:
                content = source_file.read()

            log_file.write(f"--- Filename {file_path.relative_to(self.project_root)} ---\n\n")
            log_file.write(content)
            log_file.write("\n\n")
        except UnicodeDecodeError:
            return
        except Exception as e:
            log_file.write(f"--- Filename {file_path.relative_to(self.project_root)} ---\n\n")
            log_file.write(f"Error reading file: {str(e)}\n\n")

    def process_file(self, file_path: Path, log_file) -> None:
        if file_path in self.processed_files or self.should_ignore(file_path):
            return

        self.processed_files.add(file_path)

        self.write_file_content(file_path, log_file)

        if self.get_mode() == "traverse":
            local_imports = self.get_local_imports(file_path)
            for import_path in local_imports:
                self.process_file(import_path, log_file)

    def log_ignored_patterns(self) -> None:
        if self.ignore_patterns:
            self.console.print("Ignoring the following patterns from .gitignore:", style="bold yellow")
            for pattern in self.ignore_patterns:
                self.console.print(f"  - {pattern}", style="yellow")
        else:
            self.console.print("No .gitignore patterns found.", style="bold yellow")

    def get_local_imports(self, file_path: Path) -> List[Path]:
        with open(file_path, "r", encoding="utf-8") as source_file:
            content = source_file.read()

        tree = ast.parse(content)
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module = node.names[0].name if isinstance(node, ast.Import) else node.module
                if module.startswith(("src.", "apps.")):
                    module_path = self.project_root / Path(*module.split("."))
                    if not module_path.exists():
                        module_path = module_path.with_name(module_path.stem + ".py")
                    if module_path.exists():
                        imports.append(module_path)

        return imports

    def get_mode(self) -> str:
        return getattr(self, "_mode", "all")

    def set_mode(self, mode: str) -> None:
        self._mode = mode
