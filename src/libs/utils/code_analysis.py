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
def collect_defined_and_used_names(tree: ast.AST, imported_names: Set[str], alias_mapping: Dict[str, str], should_log: bool) -> Tuple[Set[str], Set[str]]:

    class DefinitionCollector(ast.NodeVisitor):
        def __init__(self):
            self.defined_names = set()

        def visit_FunctionDef(self, node):
            self.defined_names.add(node.name)
            self.generic_visit(node)

        def visit_ClassDef(self, node):
            self.defined_names.add(node.name)
            self.generic_visit(node)

        def visit_Assign(self, node):
            for target in node.targets:
                self.defined_names.update(extract_assigned_names(target))
            self.generic_visit(node)

        def visit_AnnAssign(self, node):
            self.defined_names.update(extract_assigned_names(node.target))
            self.generic_visit(node)

    class UsageCollector(ast.NodeVisitor):
        def __init__(self):
            self.used_names = set()
            self.alias_mapping = {}

        def visit_Name(self, node):
            if isinstance(node.ctx, ast.Load):
                name = node.id
                if name in self.alias_mapping:
                    name = self.alias_mapping[name]
                self.used_names.add(name)
            self.generic_visit(node)

        def visit_Call(self, node):
            func = node.func
            if isinstance(func, ast.Name):
                name = func.id
                if name in self.alias_mapping:
                    name = self.alias_mapping[name]
                self.used_names.add(name)
            elif isinstance(func, ast.Attribute):
                name = func.attr
                if name in self.alias_mapping:
                    name = self.alias_mapping[name]
                self.used_names.add(name)
            self.generic_visit(node)

        def visit_Import(self, node):
            for alias in node.names:
                imported_name = alias.name.split(".")[0]
                asname = alias.asname or imported_name
                self.alias_mapping[asname] = imported_name
            self.generic_visit(node)

        def visit_ImportFrom(self, node):
            module = node.module
            for alias in node.names:
                imported_name = alias.name
                asname = alias.asname or imported_name
                full_name = f"{module}.{imported_name}" if module else imported_name
                self.alias_mapping[asname] = full_name
            self.generic_visit(node)

    def_collector = DefinitionCollector()
    def_collector.visit(tree)
    defined_names = def_collector.defined_names

    usage_collector = UsageCollector()
    usage_collector.alias_mapping = alias_mapping
    usage_collector.used_names.update(imported_names)
    usage_collector.visit(tree)
    used_names = usage_collector.used_names

    return defined_names, used_names


def extract_assigned_names(node: ast.AST) -> Set[str]:
    assigned_names: Set[str] = set()

    if isinstance(node, list):
        for n in node:
            assigned_names.update(extract_assigned_names(n))
    elif isinstance(node, ast.Name):
        assigned_names.add(node.id)
    elif isinstance(node, (ast.Tuple, ast.List)):
        for elt in node.elts:
            assigned_names.update(extract_assigned_names(elt))
    elif isinstance(node, ast.Attribute):
        assigned_names.add(node.attr)
    elif isinstance(node, ast.Subscript):
        pass
    elif isinstance(node, ast.Starred):
        assigned_names.update(extract_assigned_names(node.value))

    return assigned_names


# @TODO: delete should_log logic
def find_unused_code_nodes(
    tree: ast.AST, used_names: Set[str], defined_names: Set[str], file_path: Path, programatically_imports: Dict[Path, Set[str]], should_log: bool
) -> Tuple[List[ast.AST], List[ast.AST]]:
    unused_nodes: List[ast.AST] = []
    used_nodes: List[ast.AST] = []

    is_file_path_in_programatically_imports: bool = file_path in programatically_imports

    for node in tree.body:
        if should_log:
            log("node")
            log(ast.dump(node))

        if is_file_path_in_programatically_imports:
            used_nodes.append(node)
            continue

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name in used_names:
                used_nodes.append(node)
            else:
                unused_nodes.append(node)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            assigned_names = set()
            for target in targets:
                assigned_names.update(extract_assigned_names(target))
            if assigned_names & used_names:
                used_nodes.append(node)
            else:
                unused_nodes.append(node)
        else:
            used_nodes.append(node)
    return unused_nodes, used_nodes


def get_unused_code_nodes(
    content: str, imported_names: Set[str], file_path: Path, programatically_imports: Dict[Path, Set[str]], alias_mapping: Dict[str, str], tree: Optional[ast.AST] = None
) -> Tuple[List[ast.AST], List[ast.AST]]:
    if tree is None:
        tree = ast.parse(content)

    # Determine whether to log based on the file path or other criteria
    should_log: bool = False
    if file_path == Path("/path/to/specific/file.py"):
        should_log = True

    # Collect definitions and usages
    defined_names, used_names = collect_defined_and_used_names(tree, imported_names, alias_mapping, should_log)

    # Determine unused and used nodes
    unused_nodes, used_nodes = find_unused_code_nodes(tree, used_names, defined_names, file_path, programatically_imports, should_log)

    return unused_nodes, used_nodes


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
