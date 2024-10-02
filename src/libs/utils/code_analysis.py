from pathlib import Path
import ast
from typing import Optional, List, Set, Dict, Tuple

from src.libs.utils.file_system import should_ignore_file, is_path_directory, get_files_match_pattern
from src.libs.services.logger.logger import log


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


def get_imports_from_import_node(node: ast.Import, project_root: Path) -> Tuple[Dict[Path, Set[str]], Dict[str, str]]:
    imports: Dict[Path, Set[str]] = {}
    alias_mapping: Dict[str, str] = {}

    for alias in node.names:
        if is_local_module(alias.name, project_root):
            module_path: Path | None = resolve_import_path(alias.name, project_root)
            if module_path:
                imported_name: str = alias.name
                alias_name: str = alias.asname or alias.name
                imports.setdefault(module_path, set()).add(imported_name)
                if alias.asname:
                    alias_mapping[alias_name] = imported_name

    return imports, alias_mapping


def get_imports_from_import_from_node(node: ast.ImportFrom, project_root: Path) -> Tuple[Dict[Path, Set[str]], Dict[str, str]]:
    imports: Dict[Path, Set[str]] = {}
    alias_mapping: Dict[str, str] = {}

    if node.module and is_local_module(node.module, project_root):
        module_path: Path | None = resolve_import_path(node.module, project_root)
        if module_path:
            for alias in node.names:
                imported_name: str = alias.name
                alias_name: str = alias.asname or alias.name
                imports.setdefault(module_path, set()).add(imported_name)
                if alias.asname:
                    alias_mapping[alias_name] = imported_name

    return imports, alias_mapping


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


def get_local_imports(
    content: str, project_root: Path, ignore_patterns: List[str] = [], allowed_files: List[str] = []
) -> Tuple[Dict[Path, Set[str]], Dict[Path, Set[str]], Dict[str, str]]:
    tree = ast.parse(content)
    imports: Dict[Path, Set[str]] = {}
    programatically_imports: Dict[Path, Set[str]] = {}
    alias_mapping: Dict[str, str] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            import_dict, alias_m = get_imports_from_import_node(node, project_root)
            for module_path, names in import_dict.items():
                imports.setdefault(module_path, set()).update(names)
            alias_mapping.update(alias_m)
        elif isinstance(node, ast.ImportFrom):
            import_dict, alias_m = get_imports_from_import_from_node(node, project_root)
            for module_path, names in import_dict.items():
                imports.setdefault(module_path, set()).update(names)
            alias_mapping.update(alias_m)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            import_dict = get_imports_from_programmatic_imports(node, project_root, ignore_patterns, allowed_files)
            for module_path, names in import_dict.items():
                imports.setdefault(module_path, set()).update(names)
                programatically_imports.setdefault(module_path, set()).update(names)

    return imports, programatically_imports, alias_mapping


# @TODO: delete should_log logic
def collect_defined_and_used_names(
    tree: ast.AST, imported_names: Set[str], alias_mapping: Dict[str, str], should_log
) -> Tuple[Set[str], Set[str], Set[str], Dict[str, List[str]]]:

    class NameCollector(ast.NodeVisitor):
        def __init__(self):
            self.defined_names = set()
            self.used_names = set(imported_names)
            self.used_classes = set()
            self.class_methods = {}
            self.current_function_is_used_stack = [True]

        def visit_Name(self, node):
            name = node.id
            if name in alias_mapping:
                name = alias_mapping[name]
            if isinstance(node.ctx, ast.Store):
                self.defined_names.add(name)
            elif isinstance(node.ctx, ast.Load) and name not in __builtins__:
                if self.current_function_is_used_stack[-1]:
                    self.used_names.add(name)
                    if name in self.defined_names:
                        self.used_classes.add(name)
            self.generic_visit(node)

        def visit_ClassDef(self, node):
            self.defined_names.add(node.name)
            self.class_methods[node.name] = [m.name for m in node.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]
            if node.name in imported_names:
                self.used_classes.add(node.name)
                self.current_function_is_used_stack.append(True)
                self.generic_visit(node)
                self.current_function_is_used_stack.pop()
            else:
                pass

        def visit_FunctionDef(self, node):
            self.defined_names.add(node.name)
            if node.name in self.used_names:
                self.current_function_is_used_stack.append(True)
                self.generic_visit(node)
                self.current_function_is_used_stack.pop()
            else:
                pass

        def visit_AsyncFunctionDef(self, node):
            self.visit_FunctionDef(node)

        def visit_Call(self, node):
            if self.current_function_is_used_stack[-1]:
                func = node.func
                if isinstance(func, ast.Name):
                    name = func.id
                    if name in alias_mapping:
                        name = alias_mapping[name]
                    self.used_names.add(name)
                elif isinstance(func, ast.Attribute):
                    name = func.attr
                    if name in alias_mapping:
                        name = alias_mapping[name]
                    self.used_names.add(name)
            self.generic_visit(node)

    collector = NameCollector()
    collector.visit(tree)

    # Include methods of used classes
    for class_name in collector.used_classes:
        if class_name in collector.class_methods:
            collector.used_names.update(collector.class_methods[class_name])

    # Log for debugging if needed
    if should_log:
        log("defined_names")
        log(collector.defined_names)
        log("used_names")
        log(collector.used_names)
        log("used_classes")
        log(collector.used_classes)
        log("class_methods")
        log(collector.class_methods)

    return (
        collector.defined_names,
        collector.used_names,
        collector.used_classes,
        collector.class_methods,
    )


def extract_assigned_names(node):
    assigned_names = set()

    if isinstance(node, ast.Name):
        assigned_names.add(node.id)
    elif isinstance(node, ast.Attribute):
        # For attributes like self.x = value
        # You may decide to use node.attr or node.value.id
        # Here, we'll use node.attr (e.g., 'x' in 'self.x')
        assigned_names.add(node.attr)
    elif isinstance(node, (ast.Tuple, ast.List)):
        for elt in node.elts:
            assigned_names.update(extract_assigned_names(elt))
    elif isinstance(node, ast.Subscript):
        # Subscript assignments like a[0] = value
        # You might choose to handle this differently
        pass  # Ignoring subscripts for now
    elif isinstance(node, ast.Starred):
        assigned_names.update(extract_assigned_names(node.value))
    # Add more cases if needed
    return assigned_names


# @TODO: delete should_log logic
def find_unused_code_nodes(
    tree: ast.AST, used_names: Set[str], used_classes: Set[str], class_methods: Dict[str, List[str]], file_path: Path, programatically_imports: Dict[Path, Set[str]], should_log
) -> Tuple[List[ast.AST], List[ast.AST]]:
    unused_nodes: List[ast.AST] = []
    used_nodes: List[ast.AST] = []

    is_file_path_in_programatically_imports: bool = file_path in programatically_imports

    for node in tree.body:

        # @TODO: delete should_log logic
        if should_log:
            log("node")
            log(ast.dump(node))

        if is_file_path_in_programatically_imports:
            used_nodes.append(node)
            continue
        if isinstance(node, ast.ClassDef):
            if node.name not in used_names and node.name not in used_classes:
                unused_nodes.append(node)
            else:
                used_nodes.append(node)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.decorator_list:
                used_nodes.append(node)
                continue
            is_method_of_used_class = any((node.name in methods for cls, methods in class_methods.items() if cls in used_classes))
            if node.name not in used_names and node.name != "__init__" and (not is_method_of_used_class):
                unused_nodes.append(node)
            else:
                used_nodes.append(node)
        elif isinstance(node, ast.Assign):
            assigned_names = set()
            for target in node.targets:
                assigned_names.update(extract_assigned_names(target))
            if not assigned_names or all((name not in used_names and name not in used_classes for name in assigned_names)):
                unused_nodes.append(node)
            else:
                used_nodes.append(node)
        elif isinstance(node, ast.AnnAssign):
            assigned_names = extract_assigned_names(node.target)
            if not assigned_names or all((name not in used_names and name not in used_classes for name in assigned_names)):
                unused_nodes.append(node)
            else:
                used_nodes.append(node)
        else:
            used_nodes.append(node)
    return (unused_nodes, used_nodes)


def get_unused_code_nodes(
    content: str, imported_names: Set[str], file_path: Path, programatically_imports: Dict[Path, Set[str]], alias_mapping: Dict[str, str], tree: Optional[ast.AST] = None
) -> Tuple[List[ast.AST], List[ast.AST]]:
    if tree is None:
        tree = ast.parse(content)

    # @TODO: delete should_log logic
    should_log: bool = False
    if file_path == Path("/home/lasantoneta/react-component-engineer/src/libs/utils/code_analysis.py"):
        should_log = True

    # @TODO: delete should_log logic
    _, used_names, used_classes, class_methods = collect_defined_and_used_names(tree, imported_names, alias_mapping, should_log)
    unused_nodes, used_nodes = find_unused_code_nodes(tree, used_names, used_classes, class_methods, file_path, programatically_imports, should_log)

    return (unused_nodes, used_nodes)


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


def get_node_source_code_with_decorators(source: str, node: ast.AST) -> Optional[str]:
    if not hasattr(node, "lineno") or not hasattr(node, "end_lineno"):
        return None

    lines = source.splitlines()

    if hasattr(node, "decorator_list") and node.decorator_list:
        first_decorator = node.decorator_list[0]
        start_lineno = first_decorator.lineno
        decorator_col_offset = first_decorator.col_offset

        start_line = lines[start_lineno - 1]

        at_pos = start_line.rfind("@", 0, decorator_col_offset)

        if at_pos != -1:
            start_col_offset = at_pos
        else:
            start_col_offset = 0
    else:
        start_lineno = node.lineno
        start_col_offset = node.col_offset

    end_lineno = node.end_lineno
    end_col_offset = node.end_col_offset

    start_lineno -= 1
    end_lineno -= 1

    if start_lineno == end_lineno:
        return lines[start_lineno][start_col_offset:end_col_offset]

    texts: list = [lines[start_lineno][start_col_offset:]]
    if end_lineno - start_lineno > 1:
        texts.extend(lines[start_lineno + 1 : end_lineno])
    texts.append(lines[end_lineno][:end_col_offset])

    return "\n".join(texts)
