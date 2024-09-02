from pathlib import Path
from typing import Set, List, Any, Dict, Optional, Tuple
import ast
import mimetypes
import fnmatch
import re


from src.apps.console.classes.commands.base import BaseCommand
from src.libs.helpers.console import get_user_input
from src.libs.utils.string import wrap_text
from src.libs.utils.constants import CODE_CHANGES, ENTIRE_FILE
from src.libs.services.logger.logger import log

NAME: str = "prompt"
DESCRIPTION: str = "Construct a prompt log file from given Python files or all files in specified folders"
PROJECT_ROOT: Path = Path(__file__).resolve().parents[5]
PROCESSED_FILES: Set[Path] = set()
ALLOWED_FILES: List[str] = [".gitignore", ".env.example", "pyproject.toml", ".flake8"]
PROCESSED_CONTENT: Dict[Path, Set[str]] = {}


class PromptConstructorCommand(BaseCommand):
    name: str = NAME
    description: str = DESCRIPTION
    project_root: Path = PROJECT_ROOT
    processed_files: Set[Path] = PROCESSED_FILES
    processed_content: Dict[Path, Set[str]] = PROCESSED_CONTENT

    async def execute(self, *args: Any, **kwargs: Any) -> None:
        self.ignore_patterns = self.parse_gitignore()

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
            local_imports, _ = self.get_local_imports(file_path)
            for import_path, _ in local_imports.items():
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

        imports, programatically_imports = self.get_local_imports(file_path)
        for import_path, imported_names in imports.items():
            self.process_import_file(import_path, imported_names, file_path, log_file, programatically_imports)

    def process_import_file(self, import_path: Path, imported_names: Set[str], importing_file: Path, log_file, programatically_imports) -> None:
        log(f"Starting process_import_file for {import_path}")
        log(f"Imported names: {imported_names}")
        log(f"Self processed content: {self.processed_content}")

        if import_path not in self.processed_content:
            self.processed_content[import_path] = ""

        if self.should_ignore(import_path):
            log(f"Ignoring file: {import_path}")
            return

        with open(import_path, "r", encoding="utf-8") as source_file:
            content = source_file.read()

        unused_ranges = self.get_unused_code(content, imported_names, import_path, programatically_imports)
        log(f"Unused ranges: {unused_ranges}")

        lines = content.splitlines(keepends=True)
        log(f"The lines: {lines}")

        lines_to_remove = set()
        for start, end in unused_ranges:
            lines_to_remove.update(range(start - 1, end))  # Convert to 0-indexed

        new_lines = []
        prev_line_kept = False
        for i, line in enumerate(lines):
            if i not in lines_to_remove:
                # Preserve blank lines between functions/classes
                if line.strip() == "" and prev_line_kept:
                    new_lines.append(line)
                    if line not in self.processed_content[import_path]:
                        self.processed_content[import_path] += line
                elif line.strip() != "":
                    new_lines.append(line)
                    prev_line_kept = True
                    if line not in self.processed_content[import_path]:
                        self.processed_content[import_path] += line

            else:
                prev_line_kept = False

        # new_content = "".join(new_lines)

        # Ensure there are no more than two consecutive blank lines
        # final_lines = []
        # blank_line_count = 0
        # for line in new_lines:
        #     if line.strip():
        #         if blank_line_count > 0:
        #             final_lines.extend(["\n"] * min(blank_line_count, 2))
        #         final_lines.append(line)
        #         blank_line_count = 0
        #     else:
        #         blank_line_count += 1

        # # Ensure there's always a newline at the end of the file
        # if final_lines and not final_lines[-1].endswith("\n"):
        #     final_lines.append("\n")

        final_content = "".join(new_lines)

        if final_content.strip():
            if import_path not in self.processed_files:
                log_file.write(f"\n\n--- Filename {import_path.relative_to(self.project_root)} ---\n\n")
            log_file.write(final_content)

        self.processed_files.add(import_path)

        log(f"Added {len(new_lines)} lines from {import_path}")

        new_imports, programatically_imports = self.get_local_imports(import_path)
        for new_import_path, new_imported_names in new_imports.items():
            self.process_import_file(new_import_path, new_imported_names, import_path, log_file, programatically_imports)

        log(f"Finished processing {import_path}")

    def get_unused_code(self, content: str, imported_names: Set[str], file_path: Path, programatically_imports: Dict[Path, Set[str]]) -> List[Tuple[int, int]]:
        log(f"programatically_imports: {programatically_imports}")

        if file_path in programatically_imports:
            return []

        tree = ast.parse(content)
        used_names = set(imported_names)
        defined_names = set()
        unused_ranges = []
        used_classes = set()
        class_methods = {}

        log(f"Analyzing file: {file_path}")
        log(f"Imported names: {imported_names}")

        class NameCollector(ast.NodeVisitor):
            def visit_Name(self, node):
                if isinstance(node.ctx, ast.Store):
                    defined_names.add(node.id)
                    log(f"Defined name: {node.id}")
                elif isinstance(node.ctx, ast.Load) and node.id not in __builtins__:
                    used_names.add(node.id)
                    if node.id in defined_names:
                        used_classes.add(node.id)
                    log(f"Used name: {node.id}")
                self.generic_visit(node)

            def visit_ClassDef(self, node):
                defined_names.add(node.name)
                class_methods[node.name] = [m.name for m in node.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]
                log(f"Defined class: {node.name} with methods: {class_methods[node.name]}")
                if node.name in imported_names:
                    used_classes.add(node.name)
                self.generic_visit(node)

        NameCollector().visit(tree)

        log(f"Defined names: {defined_names}")
        log(f"Used names: {used_names}")
        log(f"Used classes: {used_classes}")
        log(f"Class methods: {class_methods}")

        # Consider all methods of used classes as used
        for class_name in used_classes:
            if class_name in class_methods:
                used_names.update(class_methods[class_name])

        for node in ast.walk(tree):
            log(f"Processing node: {type(node).__name__}")
            if isinstance(node, ast.ClassDef):
                if node.name not in used_names and node.name not in used_classes:
                    unused_ranges.append((node.lineno, node.end_lineno))
                    log(f"Marking class as unused: {node.name}")
                else:
                    log(f"Class is used: {node.name}")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.decorator_list:
                    log(f"Skipping decorated function: {node.name}")
                    continue
                is_method_of_used_class = any(node.name in methods for cls, methods in class_methods.items() if cls in used_classes)
                if node.name not in used_names and node.name != "__init__" and not is_method_of_used_class:
                    unused_ranges.append((node.lineno, node.end_lineno))
                    log(f"Marking function as unused: {node.name}")
                else:
                    log(f"Function is used: {node.name}")
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            if target.id not in used_names and target.id not in used_classes:
                                unused_ranges.append((node.lineno, node.end_lineno))
                                log(f"Marking assignment as unused: {target.id}")
                            else:
                                log(f"Assignment is used: {target.id}")
                elif isinstance(node, ast.AnnAssign):
                    if isinstance(node.target, ast.Name):
                        if node.target.id not in used_names and node.target.id not in used_classes:
                            unused_ranges.append((node.lineno, node.end_lineno))
                            log(f"Marking annotated assignment as unused: {node.target.id}")
                        else:
                            log(f"Annotated assignment is used: {node.target.id}")

        log(f"Unused ranges for {file_path}: {unused_ranges}")
        return unused_ranges

    def is_used_internally(self, node: ast.AST, defined_names: Set[str], tree: ast.AST) -> bool:
        for other_node in ast.walk(tree):
            if isinstance(other_node, ast.Name) and other_node.id in defined_names:
                return True
        return False

    def remove_unused_code_from_log(self, log_file, file_path: Path, unused_ranges: List[Tuple[int, int]]) -> None:
        log_file.seek(0)
        content = log_file.read()
        file_marker = f"--- Filename {file_path.relative_to(self.project_root)} ---"
        pattern = re.compile(rf"{re.escape(file_marker)}.*?(?=--- Filename|\Z)", re.DOTALL)
        match = pattern.search(content)

        if match:
            file_content = match.group(0)
            lines = file_content.split("\n")

            # Create a set of line numbers to remove
            lines_to_remove = set()
            for start, end in unused_ranges:
                lines_to_remove.update(range(start - 1, end))  # Convert to 0-indexed

            # Keep only the lines that are not in lines_to_remove
            new_lines = [line for i, line in enumerate(lines) if i not in lines_to_remove]

            # Remove excessive blank lines
            compressed_lines = []
            blank_line_count = 0
            for line in new_lines:
                if line.strip():
                    if blank_line_count > 0:
                        compressed_lines.extend([""] * min(blank_line_count, 2))
                    compressed_lines.append(line)
                    blank_line_count = 0
                else:
                    blank_line_count += 1

            # Remove trailing blank lines
            while compressed_lines and not compressed_lines[-1].strip():
                compressed_lines.pop()

            new_file_content = "\n".join([file_marker] + compressed_lines)
            updated_content = pattern.sub(new_file_content, content)

            log_file.seek(0)
            log_file.truncate()
            log_file.write(updated_content)

            # Debug print
            print(f"Removed {len(lines) - len(compressed_lines)} lines from {file_path}")
        else:
            print(f"File content not found for {file_path}")

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

        imports, programatically_imports = self.get_local_imports(import_path)
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

        imports, programatically_imports = self.get_local_imports(import_path)
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

    def get_local_imports(self, file_path: Path) -> Tuple[Dict[Path, Set[str]], Dict[Path, Set[str]]]:
        with open(file_path, "r", encoding="utf-8") as source_file:
            content = source_file.read()

        tree = ast.parse(content)
        imports = {}
        programatically_imports = {}

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
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "import_module" and isinstance(node.func.value, ast.Name) and node.func.value.id == "importlib":
                    if node.args and isinstance(node.args[0], ast.Constant):
                        module_name = node.args[0].s
                        if module_name.startswith(("src.", "apps.")):
                            module_path = self.resolve_import_path(module_name)
                            if module_path and module_path.is_dir():
                                for py_file in module_path.rglob("*.py"):
                                    if not self.should_ignore(py_file):
                                        relative_module_name = str(py_file.relative_to(self.project_root)).replace("/", ".").replace("\\", ".")[:-3]
                                        imports.setdefault(py_file, set()).add(relative_module_name)
                                        programatically_imports.setdefault(py_file, set()).add(relative_module_name)

        return imports, programatically_imports

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
        if module_path.is_dir():
            return module_path
        return None

    def get_mode(self) -> str:
        return getattr(self, "_mode", "all")

    def set_mode(self, mode: str) -> None:
        self._mode = mode
