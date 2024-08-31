from pathlib import Path
from typing import Set, List, Any, Dict, Optional
import ast
import mimetypes
import fnmatch
import re


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

                traverse_mode = await get_user_input("Choose traverse mode:", choices=["entire file", "used code only"], default="entire file")

                starting_message = await self.get_starting_message()
                closing_message = await self.get_closing_message()

                if starting_message:
                    log_file.write(f"{wrap_text(starting_message)}\n\n")

                if traverse_mode == "entire file":
                    self.process_file(start_file, log_file)
                else:
                    self.process_file_used_code_only(start_file, log_file)

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

    def process_file_used_code_only(self, file_path: Path, log_file) -> None:
        if file_path in self.processed_files or self.should_ignore(file_path):
            return

        self.processed_files.add(file_path)

        with open(file_path, "r", encoding="utf-8") as source_file:
            content = source_file.read()

        log_file.write(f"--- Filename {file_path.relative_to(self.project_root)} ---\n\n")
        log_file.write(content)
        log_file.write("\n\n")

        imports = self.get_local_imports(file_path)
        for import_path, imported_names in imports.items():
            self.process_import_file(import_path, imported_names, file_path, log_file)

    def process_import_file(self, import_path: Path, imported_names: Set[str], importing_file: Path, log_file) -> None:
        if import_path in self.processed_files or self.should_ignore(import_path):
            return

        self.processed_files.add(import_path)

        with open(import_path, "r", encoding="utf-8") as source_file:
            content = source_file.read()

        log_file.write(f"--- Filename {import_path.relative_to(self.project_root)} ---\n\n")
        log_file.write(content)
        log_file.write("\n\n")

        unused_code = self.get_unused_code(content, imported_names, import_path)
        self.remove_unused_code_from_log(log_file, import_path, unused_code)

        new_imports = self.get_local_imports(import_path)
        for new_import_path, new_imported_names in new_imports.items():
            self.process_import_file(new_import_path, new_imported_names, import_path, log_file)

    def get_unused_code(self, content: str, imported_names: Set[str], file_path: Path) -> List[ast.AST]:
        tree = ast.parse(content)
        unused_nodes = []
        defined_names = set()

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                defined_names.add(node.name)

        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                continue  # Keep all imports
            elif isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                if node.name not in imported_names and not self.is_used_internally(node, defined_names, tree):
                    unused_nodes.append(node)
            elif isinstance(node, ast.Assign):
                all_targets_unused = True
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if target.id in imported_names or self.is_used_internally(node, defined_names, tree):
                            all_targets_unused = False
                            break
                if all_targets_unused:
                    unused_nodes.append(node)

        return unused_nodes

    def is_used_internally(self, node: ast.AST, defined_names: Set[str], tree: ast.AST) -> bool:
        for other_node in ast.walk(tree):
            if isinstance(other_node, ast.Name) and other_node.id in defined_names:
                return True
        return False

    def remove_unused_code_from_log(self, log_file, file_path: Path, unused_nodes: List[ast.AST]) -> None:
        log_file.seek(0)
        content = log_file.read()
        file_marker = f"--- Filename {file_path.relative_to(self.project_root)} ---"
        file_content_match = re.search(f"{re.escape(file_marker)}.*?(?=--- Filename|\Z)", content, re.DOTALL)

        if file_content_match:
            file_content = file_content_match.group(0)
            for node in unused_nodes:
                node_content = ast.get_source_segment(file_content, node)
                if node_content:
                    file_content = file_content.replace(node_content, "")

            updated_content = content.replace(file_content_match.group(0), file_content)
            log_file.seek(0)
            log_file.truncate()
            log_file.write(updated_content)

    def process_import_used_code(self, import_path: Path, imported_names: Set[str], log_file) -> None:
        if import_path in self.processed_files or self.should_ignore(import_path):
            return

        self.processed_files.add(import_path)

        with open(import_path, "r", encoding="utf-8") as source_file:
            content = source_file.read()

        tree = ast.parse(content)
        used_code = self.get_import_used_code(content, tree, imported_names)

        if used_code.strip():
            log_file.write(f"--- Filename {import_path.relative_to(self.project_root)} ---\n\n")
            log_file.write(used_code)
            log_file.write("\n\n")

        imports = self.get_local_imports(import_path)
        for new_import_path, new_imported_names in imports.items():
            self.process_import_used_code(new_import_path, new_imported_names, log_file)

    def get_import_used_code(self, content: str, tree: ast.AST, imported_names: Set[str]) -> str:
        used_code = []
        imports = []
        functions = {}
        classes = {}
        assignments = {}
        used_functions = set()

        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.append(ast.get_source_segment(content, node))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions[node.name] = ast.get_source_segment(content, node)
            elif isinstance(node, ast.ClassDef):
                classes[node.name] = ast.get_source_segment(content, node)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        assignments[target.id] = ast.get_source_segment(content, node)

        used_code.extend(imports)

        if imports:
            used_code.append("")

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    used_functions.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    used_functions.add(node.func.attr)

        for name in imported_names:
            if name in classes:
                used_code.append(classes[name])
            if name in functions:
                used_code.append(functions[name])
            if name in assignments:
                used_code.append(assignments[name])

        # Add functions used by imported classes/functions
        for func_name in used_functions:
            if func_name in functions and func_name not in imported_names:
                used_code.append(functions[func_name])

        return "\n\n".join(used_code)

    def process_import(self, import_path: Path, imported_names: Set[str], log_file) -> None:
        if import_path in self.processed_files or self.should_ignore(import_path):
            return

        self.processed_files.add(import_path)

        with open(import_path, "r", encoding="utf-8") as source_file:
            content = source_file.read()

        tree = ast.parse(content)
        used_code = self.get_used_code(content, tree, imported_names)

        if used_code.strip():
            log_file.write(f"--- Filename {import_path.relative_to(self.project_root)} ---\n\n")
            log_file.write(used_code)
            log_file.write("\n\n")

        imports = self.get_local_imports(import_path)
        for new_import_path, new_imported_names in imports.items():
            self.process_import(new_import_path, new_imported_names, log_file)

    def get_used_code(self, content: str, tree: ast.AST, imported_names: Set[str]) -> str:
        used_code = []
        imports = []
        functions = {}
        classes = {}
        assignments = {}

        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.append(ast.get_source_segment(content, node))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions[node.name] = ast.get_source_segment(content, node)
            elif isinstance(node, ast.ClassDef):
                classes[node.name] = ast.get_source_segment(content, node)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        assignments[target.id] = ast.get_source_segment(content, node)

        # Add imports
        used_code.extend(imports)

        # Add a blank line after imports if there are any
        if imports:
            used_code.append("")

        # Add used functions, classes, and assignments
        used_names = set(imported_names)
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                used_names.add(node.id)

        for name in used_names:
            if name in functions:
                used_code.append(functions[name])
            if name in classes:
                used_code.append(classes[name])
            if name in assignments:
                used_code.append(assignments[name])

        return "\n\n".join(used_code)

    def get_local_imports(self, file_path: Path) -> Dict[Path, Set[str]]:
        with open(file_path, "r", encoding="utf-8") as source_file:
            content = source_file.read()

        tree = ast.parse(content)
        imports = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(("src.", "apps.")):
                        module_path = self.resolve_import_path(alias.name)
                        if module_path:
                            imports.setdefault(module_path, set()).add(alias.asname or alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith(("src.", "apps.")):
                    module_path = self.resolve_import_path(node.module)
                    if module_path:
                        imported_names = set()
                        for alias in node.names:
                            if alias.name == "*":
                                imported_names.add("*")
                            else:
                                imported_names.add(alias.asname or alias.name)
                        imports.setdefault(module_path, set()).update(imported_names)

        return imports

    def resolve_import_path(self, module_name: str) -> Optional[Path]:
        module_path = self.project_root / Path(*module_name.split("."))
        if module_path.is_file():
            return module_path
        py_file = module_path.with_suffix(".py")
        if py_file.is_file():
            return py_file
        init_file = module_path / "__init__.py"
        if init_file.is_file():
            return init_file
        return None

    def log_ignored_patterns(self) -> None:
        if self.ignore_patterns:
            self.console.print("Ignoring the following patterns from .gitignore:", style="bold yellow")
            for pattern in self.ignore_patterns:
                self.console.print(f"  - {pattern}", style="yellow")
        else:
            self.console.print("No .gitignore patterns found.", style="bold yellow")

    def get_mode(self) -> str:
        return getattr(self, "_mode", "all")

    def set_mode(self, mode: str) -> None:
        self._mode = mode
