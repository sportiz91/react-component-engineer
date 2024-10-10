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


def resolve_relative_import(
    node: ast.ImportFrom,
    current_file: Path,
) -> Optional[Path]:
    current_package: Path = current_file.parent

    for _ in range(node.level - 1):
        current_package: Path = current_package.parent

    module_parts: list[str] = node.module.split(".") if node.module else []
    module_path: Path = current_package.joinpath(*module_parts)

    possible_files: list[Path] = [
        module_path / "__init__.py",
        module_path.with_suffix(".py"),
        module_path,
    ]

    for path in possible_files:
        if path.is_file():
            return path.resolve()

    return None


def resolve_absolute_import(
    node: ast.ImportFrom,
    project_root: Path,
) -> Optional[Path]:
    if node.module and is_local_module(node.module, project_root):
        return resolve_import_path(node.module, project_root)
    return None


def add_imported_names(
    node: ast.ImportFrom,
    module_file: Path,
    imports: Dict[Path, Set[str]],
    alias_mapping: Dict[str, str],
):
    for alias in node.names:
        imported_name = alias.name
        alias_name = alias.asname or alias.name
        imports.setdefault(module_file, set()).add(imported_name)
        if alias.asname:
            alias_mapping[alias_name] = imported_name


def process_import_aliases(
    module_path: Path,
    aliases: List[ast.alias],
    imports: Dict[Path, Set[str]],
    alias_mapping: Dict[str, str],
):
    for alias in aliases:
        imported_name = alias.name
        alias_name = alias.asname or alias.name
        imports.setdefault(module_path, set()).add(imported_name)
        if alias.asname:
            alias_mapping[alias_name] = imported_name


def get_imports_from_import_node(node: ast.Import, project_root: Path) -> Tuple[Dict[Path, Set[str]], Dict[str, str]]:
    imports: Dict[Path, Set[str]] = {}
    alias_mapping: Dict[str, str] = {}

    for alias in node.names:
        if is_local_module(alias.name, project_root):
            module_path: Path | None = resolve_import_path(alias.name, project_root)
            if module_path:
                process_import_aliases(module_path, [alias], imports, alias_mapping)

    return imports, alias_mapping


def get_imports_from_import_from_node(
    node: ast.ImportFrom,
    current_file: Path,
    project_root: Path,
) -> Tuple[Dict[Path, Set[str]], Dict[str, str]]:
    imports: Dict[Path, Set[str]] = {}
    alias_mapping: Dict[str, str] = {}

    if node.level == 0:
        module_file = resolve_absolute_import(node, project_root)
    else:
        module_file = resolve_relative_import(node, current_file)

    if module_file:
        add_imported_names(node, module_file, imports, alias_mapping)

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
    content: str,
    file_path: Path,
    project_root: Path,
    ignore_patterns: List[str] = [],
    allowed_files: List[str] = [],
) -> Tuple[Dict[Path, Set[str]], Dict[Path, Set[str]], Dict[str, str]]:
    tree = ast.parse(content)
    imports: Dict[Path, Set[str]] = {}
    programmatic_imports: Dict[Path, Set[str]] = {}
    alias_mapping: Dict[str, str] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            import_dict, alias_m = get_imports_from_import_node(node, project_root)
            for module_path, names in import_dict.items():
                imports.setdefault(module_path, set()).update(names)
            alias_mapping.update(alias_m)
        elif isinstance(node, ast.ImportFrom):
            import_dict, alias_m = get_imports_from_import_from_node(node, file_path, project_root)
            for module_path, names in import_dict.items():
                imports.setdefault(module_path, set()).update(names)
            alias_mapping.update(alias_m)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            import_dict = get_imports_from_programmatic_imports(node, project_root, ignore_patterns, allowed_files)
            for module_path, names in import_dict.items():
                imports.setdefault(module_path, set()).update(names)
                programmatic_imports.setdefault(module_path, set()).update(names)

    return imports, programmatic_imports, alias_mapping


def collect_defined_names(tree: ast.AST) -> Set[str]:
    defined_names: Set[str] = set()

    class DefinitionCollector(ast.NodeVisitor):
        def __init__(self):
            self.current_class = None

        def visit_ClassDef(self, node: ast.ClassDef):
            defined_names.add(node.name)
            self.current_class = node.name
            self.generic_visit(node)
            self.current_class = None

        def visit_FunctionDef(self, node: ast.FunctionDef):
            if self.current_class:
                function_name = f"{self.current_class}.{node.name}"
            else:
                function_name = node.name
            defined_names.add(function_name)
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
            self.visit_FunctionDef(node)

        def visit_Assign(self, node: ast.Assign):
            for target in node.targets:
                defined_names.update(extract_assigned_names(target))
            self.generic_visit(node)

        def visit_AnnAssign(self, node: ast.AnnAssign):
            defined_names.update(extract_assigned_names(node.target))
            self.generic_visit(node)

    collector = DefinitionCollector()
    collector.visit(tree)
    return defined_names


def collect_used_names(tree: ast.AST, reachable_functions: Set[str], alias_mapping: Dict[str, str], imported_names: Set[str]) -> Set[str]:
    used_names: Set[str] = set()

    class UsageCollector(ast.NodeVisitor):
        def __init__(self):
            self.current_function = None
            self.current_class = None

        def visit_ClassDef(self, node: ast.ClassDef):
            if node.name in reachable_functions:
                self.current_class = node.name
                self.generic_visit(node)
                self.current_class = None

        def visit_FunctionDef(self, node: ast.FunctionDef):
            if self.current_class:
                function_name = f"{self.current_class}.{node.name}"
            else:
                function_name = node.name

            if function_name in reachable_functions:
                self.current_function = function_name
                used_names.add(function_name)
                self.generic_visit(node)
                self.current_function = None

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
            self.visit_FunctionDef(node)

        def visit_Call(self, node: ast.Call):
            if self.current_function:
                func = node.func
                if isinstance(func, ast.Name):
                    name = func.id
                elif isinstance(func, ast.Attribute):
                    if isinstance(func.value, ast.Name):
                        name = f"{func.value.id}.{func.attr}"
                    else:
                        name = func.attr
                else:
                    name = None

                if name and name in alias_mapping:
                    name = alias_mapping[name]

                if name:
                    used_names.add(name)
            self.generic_visit(node)

        def visit_Name(self, node: ast.Name):
            if self.current_function and isinstance(node.ctx, ast.Load):
                name = node.id
                if name in alias_mapping:
                    name = alias_mapping[name]
                used_names.add(name)
            self.generic_visit(node)

    class ModuleLevelUsageCollector(ast.NodeVisitor):
        def __init__(self):
            self.used_names = set()

        def visit_Module(self, node):
            for stmt in node.body:
                self.visit(stmt)

        def visit_Call(self, node):
            func = node.func
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            else:
                name = None

            if name and name in alias_mapping:
                name = alias_mapping[name]

            if name:
                self.used_names.add(name)

        def visit_Name(self, node):
            if isinstance(node.ctx, ast.Load):
                name = node.id
                if name in alias_mapping:
                    name = alias_mapping[name]
                self.used_names.add(name)

        def visit_FunctionDef(self, node):
            if node.name.startswith("_") and node.decorator_list:
                self.used_names.add(node.name)

        def visit_ClassDef(self, node):
            pass

        def visit_AsyncFunctionDef(self, node):
            if node.name.startswith("_") and node.decorator_list:
                self.used_names.add(node.name)

        def visit_With(self, node):
            for item in node.items:
                context_expr = item.context_expr
                if isinstance(context_expr, ast.Call):
                    func = context_expr.func
                    if isinstance(func, ast.Name):
                        name = func.id
                    elif isinstance(func, ast.Attribute):
                        name = func.attr
                    else:
                        name = None

                    if name and name in alias_mapping:
                        name = alias_mapping[name]

                    if name:
                        self.used_names.add(name)

        def generic_visit(self, node):
            pass

    usage_collector = UsageCollector()
    usage_collector.visit(tree)

    module_level_usage_collector = ModuleLevelUsageCollector()
    module_level_usage_collector.visit(tree)

    used_names.update(module_level_usage_collector.used_names)
    used_names.update(imported_names)
    used_names.update(reachable_functions)

    return used_names


def find_reachable_functions(call_graph: Dict[str, Set[str]], entry_points: Set[str], defined_names: Set[str]) -> Set[str]:
    reachable_functions: Set[str] = set()
    stack = list(entry_points)

    while stack:
        function_name = stack.pop()
        if function_name in defined_names and function_name not in reachable_functions:
            reachable_functions.add(function_name)
            called_functions = call_graph.get(function_name, set()) & defined_names
            stack.extend(called_functions)

            for name in defined_names:
                if name.startswith(f"{function_name}."):
                    method_name = name
                    if method_name not in reachable_functions:
                        reachable_functions.add(method_name)
                        stack.append(method_name)
    return reachable_functions


def build_imported_names_graph(call_graph: Dict[str, Set[str]], imported_names: Set[str], defined_names: Set[str]) -> Dict[str, Set[str]]:
    imported_names_graph = {}

    def depth_first_seach(func: str, visited: Set[str]) -> Set[str]:
        if func not in call_graph or func in visited:
            return set()
        visited.add(func)
        called_funcs = call_graph[func] & defined_names
        result = set(called_funcs)
        for called_func in called_funcs:
            result.update(depth_first_seach(called_func, visited))
        return result

    for func in imported_names:
        visited = set()
        imported_names_graph[func] = depth_first_seach(func, visited)

    return imported_names_graph


def collect_defined_and_used_names(tree: ast.AST, imported_names: Set[str], alias_mapping: Dict[str, str], should_log: bool) -> Tuple[Set[str], Set[str]]:
    class CallGraphBuilder(ast.NodeVisitor):
        def __init__(self):
            self.call_graph: Dict[str, Set[str]] = {}
            self.function_stack: List[str] = []
            self.current_class = None

        def visit_ClassDef(self, node: ast.ClassDef):
            self.current_class = node.name
            self.generic_visit(node)
            self.current_class = None

        def visit_FunctionDef(self, node: ast.FunctionDef):
            if self.current_class:
                function_name = f"{self.current_class}.{node.name}"
            else:
                function_name = node.name
            self.function_stack.append(function_name)
            self.call_graph.setdefault(function_name, set())
            self.generic_visit(node)
            self.function_stack.pop()

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
            self.visit_FunctionDef(node)

        def visit_Call(self, node: ast.Call):
            if self.function_stack:
                current_function = self.function_stack[-1]
                func = node.func
                if isinstance(func, ast.Name):
                    called_function = func.id
                elif isinstance(func, ast.Attribute):
                    if isinstance(func.value, ast.Name):
                        called_function = f"{func.value.id}.{func.attr}"
                    else:
                        called_function = func.attr
                else:
                    called_function = None

                if called_function:
                    self.call_graph[current_function].add(called_function)
            self.generic_visit(node)

    class ModuleLevelCallCollector(ast.NodeVisitor):
        def __init__(self):
            self.module_level_calls = set()

        def visit_Module(self, node):
            for stmt in node.body:
                self.visit(stmt)

        def visit_Expr(self, node):
            if isinstance(node.value, ast.Call):
                func = node.value.func
                if isinstance(func, ast.Name):
                    func_name = func.id
                elif isinstance(func, ast.Attribute):
                    func_name = func.attr
                else:
                    func_name = None

                if func_name and func_name in defined_names:
                    self.module_level_calls.add(func_name)

        def visit_Assign(self, node):
            if isinstance(node.value, ast.Call):
                func = node.value.func
                if isinstance(func, ast.Name):
                    func_name = func.id
                elif isinstance(func, ast.Attribute):
                    func_name = func.attr
                else:
                    func_name = None

                if func_name and func_name in defined_names:
                    self.module_level_calls.add(func_name)

        def visit_FunctionDef(self, node):
            pass

        def visit_ClassDef(self, node):
            pass

        def visit_With(self, node):
            if isinstance(node, ast.With):
                for item in node.items:
                    context_expr = item.context_expr
                    if isinstance(context_expr, ast.Call):
                        func = context_expr.func
                        if isinstance(func, ast.Name):
                            func_name = func.id
                        elif isinstance(func, ast.Attribute):
                            func_name = func.attr
                        else:
                            func_name = None

                        if func_name and func_name in defined_names:
                            self.module_level_calls.add(func_name)

    class DecoratedUnderscoreFunctionCollector(ast.NodeVisitor):
        def __init__(self):
            self.decorated_underscore_functions = set()

        def visit_Module(self, node):
            for stmt in node.body:
                if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if stmt.name.startswith("_") and stmt.decorator_list:
                        self.decorated_underscore_functions.add(stmt.name)

        def visit_FunctionDef(self, node):
            pass

        def visit_AsyncFunctionDef(self, node):
            pass

        def visit_ClassDef(self, node):
            pass

    defined_names = collect_defined_names(tree)
    call_graph_builder = CallGraphBuilder()
    call_graph_builder.visit(tree)
    call_graph = call_graph_builder.call_graph

    imported_names_graph: Dict[str, Set[str]] = build_imported_names_graph(call_graph, imported_names, defined_names)

    reachable_from_imports = find_reachable_functions(call_graph, imported_names, defined_names)

    module_level_calls = set()

    module_level_collector = ModuleLevelCallCollector()
    module_level_collector.visit(tree)
    module_level_calls = module_level_collector.module_level_calls

    reachable_from_module_level = find_reachable_functions(call_graph, module_level_calls, defined_names)

    reachable_functions = reachable_from_imports.union(reachable_from_module_level)

    decorated_underscore_collector = DecoratedUnderscoreFunctionCollector()
    decorated_underscore_collector.visit(tree)
    decorated_underscore_functions = decorated_underscore_collector.decorated_underscore_functions

    reachable_functions = reachable_functions.union(decorated_underscore_functions)

    used_names = collect_used_names(tree, reachable_functions, alias_mapping, imported_names)

    if should_log:
        log("defined_names")
        log(defined_names)
        log("used_names")
        log(used_names)
        log("reachable_from_imports")
        log(reachable_from_imports)
        log("reachable_from_module_level")
        log(reachable_from_module_level)
        log("reachable_functions")
        log(reachable_functions)
        log("call_graph")
        log(call_graph)
        log("module_level_calls")
        log(module_level_calls)
        log("imported_names")
        log(imported_names)
        log("imported_names_graph")
        log(imported_names_graph)

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
    if file_path.name == "code_analysis.py":
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
