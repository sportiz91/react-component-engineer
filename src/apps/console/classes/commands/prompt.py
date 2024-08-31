from pathlib import Path
from typing import Set, List, Any
import ast
import mimetypes
import fnmatch


from src.apps.console.classes.commands.base import BaseCommand
from src.libs.helpers.console import get_user_input
from src.libs.utils.string import wrap_text
from src.libs.utils.constants import CODE_CHANGES, ENTIRE_FILE

NAME: str = "prompt"
DESCRIPTION: str = "Construct a prompt log file from given Python files or all files in specified folders"
PROJECT_ROOT: Path = Path(__file__).resolve().parents[5]
PROCESSED_FILES: Set[Path] = set()
ALLOWED_FILES: List[str] = [".gitignore", ".env.example", "pyproject.toml", ".flake8"]


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

        entire_file_vs_code_differences = (
            await get_user_input(
                "Do you want to output the entire file(s) with the change(s) or only the code differences?: ", choices=["entire", "differences"], default="differences"
            )
            or "differences"
        )

        prompt_log = self.project_root / "prompt.log"

        with open(prompt_log, "w+") as log_file:
            if mode == "traverse":
                filename = await get_user_input("Enter the filename (e.g., src/apps/console/main.py): ")

                start_file = self.project_root / filename

                if not start_file.exists():
                    self.console.print(f"File {start_file} does not exist.", style="bold red")
                    return

                starting_message = await self.get_starting_message()
                closing_message = await self.get_closing_message()

                if starting_message:
                    log_file.write(f"{wrap_text(starting_message)}\n\n")

                self.process_file(start_file, log_file)

                if closing_message:
                    log_file.write(f"\n{wrap_text(closing_message)}")

                if entire_file_vs_code_differences == "differences":
                    log_file.write(f"\n{wrap_text(CODE_CHANGES)}")

                elif entire_file_vs_code_differences == "entire":
                    log_file.write(f"\n{wrap_text(ENTIRE_FILE)}")

            elif mode == "all":
                folder_paths = await get_user_input("Enter the folder paths (space-separated, e.g., src/apps/console src/libs): ")
                folders = [self.project_root / folder.strip() for folder in folder_paths.split()]

                starting_message = await self.get_starting_message()
                closing_message = await self.get_closing_message()

                if starting_message:
                    log_file.write(f"{wrap_text(starting_message)}\n\n")

                self.process_multiple_folders(folders, log_file)

                if closing_message:
                    log_file.write(f"\n{wrap_text(closing_message)}")

                if entire_file_vs_code_differences == "differences":
                    log_file.write(f"\n{wrap_text(CODE_CHANGES)}")

                elif entire_file_vs_code_differences == "entire":
                    log_file.write(f"\n{wrap_text(ENTIRE_FILE)}")

            else:
                self.console.print(f"Invalid mode: {mode}", style="bold red")
                return

        self.console.print(f"prompt log has been written to {prompt_log}", style="bold green")

    async def get_starting_message(self) -> str:
        return await get_user_input("Enter a message to be written at the beginning of the prompt.log file", multiline=True)

    async def get_closing_message(self) -> str:
        return await get_user_input("Enter a message to be written at the end of the prompt.log file", multiline=True)

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
        mime_type, _ = mimetypes.guess_type(file_path)

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
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "import_module":
                if len(node.args) > 0 and isinstance(node.args[0], ast.Str):
                    module_name = node.args[0].s
                    if module_name.startswith(("src.", "apps.")):
                        module_path = self.project_root / Path(*module_name.split("."))
                        if module_path.is_dir():
                            for file in module_path.rglob("*.py"):
                                if file.is_file():
                                    imports.append(file)
                        else:
                            py_file = module_path.with_suffix(".py")
                            if py_file.exists():
                                imports.append(py_file)

        return imports

    def get_mode(self) -> str:
        return getattr(self, "_mode", "all")

    def set_mode(self, mode: str) -> None:
        self._mode = mode
