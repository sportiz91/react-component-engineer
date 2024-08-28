from pathlib import Path
from typing import Set, List, Any
import ast

from src.apps.console.classes.commands.base import BaseCommand
from src.libs.helpers.console import get_user_input

# @TODO: delete when working
# from src.libs.services.logger.logger import log

NAME: str = "prompt constructor"

DESCRIPTION: str = "Construct a prompt log file from a given Python file and its local imports"

PROJECT_ROOT: Path = Path(__file__).resolve().parents[5]

PROCESSED_FILES: Set[Path] = set()


class PromptConstructorCommand(BaseCommand):
    name: str = NAME
    description: str = DESCRIPTION
    project_root: Path = PROJECT_ROOT
    processed_files: Set[Path] = PROCESSED_FILES

    async def execute(self, *args: Any, **kwargs: Any) -> None:
        filename = await get_user_input("Enter the filename (e.g., src/apps/console/main.py): ")
        start_file = self.project_root / filename

        if not start_file.exists():
            self.console.print(f"File {start_file} does not exist.", style="bold red")
            return

        prompt_log = self.project_root / "prompt.log"
        with open(prompt_log, "w") as log_file:
            self.process_file(start_file, log_file)

        self.console.print(f"prompt log has been written to {prompt_log}", style="bold green")

    def process_file(self, file_path: Path, log_file) -> None:
        if file_path in self.processed_files:
            return

        self.processed_files.add(file_path)

        with open(file_path, "r") as source_file:
            content = source_file.read()

        log_file.write(f"--- Filename {file_path.relative_to(self.project_root)} ---\n\n")
        log_file.write(content)
        log_file.write("\n")

        local_imports = self.get_local_imports(content)

        for import_path in local_imports:
            self.process_file(import_path, log_file)

    def get_local_imports(
        self,
        content: str,
    ) -> List[Path]:

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
