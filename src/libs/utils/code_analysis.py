from pathlib import Path
import ast
from typing import Optional, List, Set, Dict, Tuple

from src.libs.utils.file_system import should_ignore_file, is_path_directory, get_files_match_pattern


def remove_blank_lines_from_code_lines(lines: List[str]) -> str:
    formatted_lines = []
    blank_line_count = 0

    for line in lines:
        if line.strip():
            if blank_line_count > 0:
                formatted_lines.extend([""] * min(blank_line_count, 2))
            formatted_lines.append(line)
            blank_line_count = 0
        else:
            blank_line_count += 1

    while formatted_lines and not formatted_lines[-1].strip():
        formatted_lines.pop()

    return "\n".join(formatted_lines)


def is_local_module(module_name: str, project_root: Path) -> bool:
    module_path: Path = project_root / Path(*module_name.split("."))

    return module_path.exists() or module_path.with_suffix(".py").exists() or (module_path / "__init__.py").exists()


def resolve_import_path(module_name: str, project_root: Path) -> Optional[Path]:
    module_path = project_root / Path(*module_name.split("."))

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


def get_imports_from_import_node(node: ast.Import, project_root: Path) -> Dict[Path, Set[str]]:
    imports: Dict[Path, Set[str]] = {}

    for alias in node.names:
        if is_local_module(alias.name, project_root):
            module_path = resolve_import_path(alias.name, project_root)
            if module_path:
                imports.setdefault(module_path, set()).add(alias.asname or alias.name)

    return imports


def get_imports_from_import_from_node(node: ast.ImportFrom, project_root: Path) -> Dict[Path, Set[str]]:
    imports: Dict[Path, Set[str]] = {}

    if node.module and is_local_module(node.module, project_root):
        module_path = resolve_import_path(node.module, project_root)
        if module_path:
            imported_names = {alias.asname or alias.name for alias in node.names}
            imports.setdefault(module_path, set()).update(imported_names)

    return imports


def get_imports_from_programmatic_imports(node: ast.Call, project_root: Path, ignore_patterns: List[str], allowed_files: List[str]) -> Dict[Path, Set[str]]:
    imports: Dict[Path, Set[str]] = {}

    if node.func.attr == "import_module" and isinstance(node.func.value, ast.Name) and node.func.value.id == "importlib":
        if node.args and isinstance(node.args[0], ast.Constant):
            module_name = node.args[0].s
            if is_local_module(module_name, project_root):
                module_path = resolve_import_path(module_name, project_root)
                if module_path and is_path_directory(module_path):
                    for py_file in get_files_match_pattern(module_path, "*.py"):
                        if not should_ignore_file(py_file, project_root, ignore_patterns, allowed_files):
                            relative_module_name = str(py_file.relative_to(project_root)).replace("/", ".").replace("\\", ".")[:-3]
                            imports.setdefault(py_file, set()).add(relative_module_name)

    return imports


def get_local_imports(content: str, project_root: Path, ignore_patterns: List[str] = [], allowed_files: List[str] = []) -> Tuple[Dict[Path, Set[str]], Dict[Path, Set[str]]]:
    tree = ast.parse(content)
    imports: Dict[Path, Set[str]] = {}
    programatically_imports: Dict[Path, Set[str]] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            import_dict = get_imports_from_import_node(node, project_root)
            for module_path, names in import_dict.items():
                imports.setdefault(module_path, set()).update(names)
        elif isinstance(node, ast.ImportFrom):
            import_dict = get_imports_from_import_from_node(node, project_root)
            for module_path, names in import_dict.items():
                imports.setdefault(module_path, set()).update(names)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            import_dict = get_imports_from_programmatic_imports(node, project_root, ignore_patterns, allowed_files)
            for module_path, names in import_dict.items():
                imports.setdefault(module_path, set()).update(names)
                programatically_imports.setdefault(module_path, set()).update(names)

    return imports, programatically_imports


def collect_defined_and_used_names(tree: ast.AST, imported_names: Set[str]) -> Tuple[Set[str], Set[str], Set[str], Dict[str, List[str]]]:
    class NameCollector(ast.NodeVisitor):
        def visit_Name(self, node):
            if isinstance(node.ctx, ast.Store):
                defined_names.add(node.id)
            elif isinstance(node.ctx, ast.Load) and node.id not in __builtins__:
                used_names.add(node.id)
                if node.id in defined_names:
                    used_classes.add(node.id)
            self.generic_visit(node)

        def visit_ClassDef(self, node):
            defined_names.add(node.name)
            class_methods[node.name] = [m.name for m in node.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]
            if node.name in imported_names:
                used_classes.add(node.name)
            self.generic_visit(node)

    defined_names: Set[str] = set()
    used_names: Set[str] = set(imported_names)
    used_classes: Set[str] = set()
    class_methods: Dict[str, List[str]] = {}

    NameCollector().visit(tree)

    for class_name in used_classes:
        if class_name in class_methods:
            used_names.update(class_methods[class_name])

    return defined_names, used_names, used_classes, class_methods


def find_unused_code_ranges(tree: ast.AST, used_names: Set[str], used_classes: Set[str], class_methods: Dict[str, List[str]]) -> List[Tuple[int, int]]:
    unused_ranges: List[Tuple[int, int]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if node.name not in used_names and node.name not in used_classes:
                unused_ranges.append((node.lineno, node.end_lineno))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.decorator_list:
                continue
            is_method_of_used_class = any(node.name in methods for cls, methods in class_methods.items() if cls in used_classes)
            if node.name not in used_names and node.name != "__init__" and not is_method_of_used_class:
                unused_ranges.append((node.lineno, node.end_lineno))
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if target.id not in used_names and target.id not in used_classes:
                            unused_ranges.append((node.lineno, node.end_lineno))
            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name):
                    if node.target.id not in used_names and node.target.id not in used_classes:
                        unused_ranges.append((node.lineno, node.end_lineno))

    return unused_ranges


def get_unused_code_ranges(content: str, imported_names: Set[str], file_path: Path, programatically_imports: Dict[Path, Set[str]]) -> List[Tuple[int, int]]:
    if file_path in programatically_imports:
        return []

    tree = ast.parse(content)

    _, used_names, used_classes, class_methods = collect_defined_and_used_names(tree, imported_names)

    unused_ranges = find_unused_code_ranges(tree, used_names, used_classes, class_methods)

    return unused_ranges


def filter_lines(lines: List[str], lines_to_remove: Set[int]) -> List[str]:
    return [line for i, line in enumerate(lines) if i not in lines_to_remove]


def process_lines(lines: List[str]) -> List[str]:
    new_lines = []
    blank_line_count = 0

    for line in lines:
        if line.strip():
            blank_line_count = 0
            new_lines.append(line)

        else:
            blank_line_count += 1
            if blank_line_count <= 2:
                new_lines.append(line)

    return new_lines
