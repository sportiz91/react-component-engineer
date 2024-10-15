import ast
from pathlib import Path
from typing import Set, List, Any, Dict, Tuple
import re


from src.apps.console.classes.commands.base import BaseCommand
from src.libs.helpers.console import get_user_input
from src.libs.utils.string import wrap_text, remove_non_printable_characters
from src.libs.utils.constants import CODE_CHANGES, ENTIRE_FILE, DASHED_MARKERS_EXPLANATION, XML_MARKERS_EXPLANATION
from src.libs.utils.prompting import create_dashed_filename_marker, create_dashed_filename_end_marker, update_content_dashed_marker
from src.libs.utils.file_system import (
    copy_to_clipboard,
    get_gitignore_patters_list,
    should_ignore_file,
    is_text_file_mimetype_or_allowed_file,
    read_file_content,
    path_exists,
    is_path_directory,
    get_files_match_pattern,
    read_log_file,
    write_log_file,
    write_log_file_from_start,
)
from src.libs.utils.configuration import get_config_value
from .....libs.utils.code_analysis import (
    get_unused_code_nodes,
    get_local_imports as get_local_imports_from_content,
    remove_blank_lines_from_code_lines,
    get_node_source_code_with_decorators,
)


NAME: str = "prompt"
DESCRIPTION: str = "Construct a prompt log file from given Python files or all files in specified folders"
DEFAULT_PROJECT_ROOT: Path | None = Path(get_config_value("PROJECT_ROOT_PATH", "")) if get_config_value("PROJECT_ROOT_PATH", None) else None
DEFAULT_PROMPT_PATH: Path | None = Path(get_config_value("PROMPT_ROOT_PATH", "")) if get_config_value("PROMPT_ROOT_PATH", None) else None
PROCESSED_FILES: Set[Path] = set()
ALLOWED_FILES: List[str] = [".gitignore", ".env.example", "pyproject.toml", ".flake8"]
PROCESSED_CONTENT: Dict[Path, Set[int]] = {}
ALIAS_MAPPING: Dict[str, str] = {}
DEFAULT_PROMPT_LOG_NAME: str = "prompt.log"
DEFAULT_OUTPUT_FORMAT: str | None = get_config_value("OUTPUT_CODE_FORMAT", None)


class PromptConstructorCommand(BaseCommand):
    name: str = NAME
    description: str = DESCRIPTION
    project_root: Path = DEFAULT_PROJECT_ROOT
    processed_files: Set[Path] = PROCESSED_FILES
    processed_content: Dict[Path, Set[int]] = PROCESSED_CONTENT
    prompt_log_name: str = DEFAULT_PROMPT_LOG_NAME
    processed_alias_mapping: Dict[str, str] = ALIAS_MAPPING
    output_format: str | None = DEFAULT_OUTPUT_FORMAT

    async def execute(self, *args: Any, **kwargs: Any) -> None:
        await self.set_project_root()

        self.console.print(f"You're analyzing: '{self.project_root}' project", style="bold green")

        if not path_exists(self.project_root) or not is_path_directory(self.project_root):
            self.console.print(f"The path '{self.project_root}' is not a valid directory.", style="bold red")
            return

        prompt_log_directory: Path | None = await self.get_prompt_log_path()

        if not path_exists(prompt_log_directory.parent):
            self.console.print(f"The path '{prompt_log_directory.parent}' does not exist.", style="bold red")
            return

        prompt_log: Path = prompt_log_directory / self.prompt_log_name

        self.console.print(f"Prompt.log file is gonna be saved on: '{prompt_log}'", style="bold green")

        self.ignore_patterns: List[str] = get_gitignore_patters_list(self.project_root)

        mode: str = await get_user_input("Enter mode: ", choices=["all", "traverse"], default="all") or "all"
        self.set_mode(mode)

        entire_file_vs_code_differences: str = (
            await get_user_input(
                "Do you want to output the entire file(s) with the change(s) or only the code differences?: ", choices=["entire", "differences"], default="differences"
            )
            or "differences"
        )

        self.output_format = await self.get_output_format()

        with open(prompt_log, "w+") as log_file:
            if mode == "traverse":
                filename: str = await get_user_input("Enter the filename (e.g., src/apps/console/main.py): ")
                start_file: Path = self.project_root / filename

                if not path_exists(start_file):
                    self.console.print(f"File {start_file} does not exist.", style="bold red")
                    return

                traverse_mode: str | None = await get_user_input("Choose traverse mode:", choices=["entire file", "used code only"], default="entire file")

                closing_message: str = await self.get_closing_message()

                if traverse_mode == "entire file":
                    self.process_file(start_file, log_file)
                else:
                    self.process_file_used_code_only(start_file, log_file)

                write_log_file(log_file, "<context>")

                if self.output_format.upper() == "XML":
                    write_log_file(log_file, f"\n{wrap_text(XML_MARKERS_EXPLANATION)}")
                else:
                    write_log_file(log_file, f"\n{wrap_text(DASHED_MARKERS_EXPLANATION)}")

                if closing_message:
                    write_log_file(log_file, f"\n{wrap_text(closing_message)}")

                write_log_file(log_file, "\n</context>\n\n")

                write_log_file(log_file, "<instructions>")

                if entire_file_vs_code_differences == "differences":
                    write_log_file(log_file, f"\n{wrap_text(CODE_CHANGES)}")

                elif entire_file_vs_code_differences == "entire":
                    write_log_file(log_file, f"\n{wrap_text(ENTIRE_FILE)}")

                write_log_file(log_file, "</instructions>")

            elif mode == "all":
                folder_paths = await get_user_input("Enter the folder paths (space-separated, e.g., src/apps/console src/libs): ")
                folders = [self.project_root / folder.strip() for folder in folder_paths.split()]

                closing_message = await self.get_closing_message()

                self.process_multiple_folders(folders, log_file)

                write_log_file(log_file, "<context>")

                if self.output_format.upper() == "XML":
                    write_log_file(log_file, f"\n{wrap_text(XML_MARKERS_EXPLANATION)}")
                else:
                    write_log_file(log_file, f"\n{wrap_text(DASHED_MARKERS_EXPLANATION)}")

                if closing_message:
                    write_log_file(log_file, f"\n{wrap_text(closing_message)}")

                write_log_file(log_file, "\n</context>\n\n")

                write_log_file(log_file, "<instructions>")

                if entire_file_vs_code_differences == "differences":
                    write_log_file(log_file, f"\n{wrap_text(CODE_CHANGES)}")

                elif entire_file_vs_code_differences == "entire":
                    write_log_file(log_file, f"\n{wrap_text(ENTIRE_FILE)}")

                write_log_file(log_file, "</instructions>")

            else:
                self.console.print(f"Invalid mode: {mode}", style="bold red")
                return

        self.format_prompt_log()
        result: dict[str, str] = copy_to_clipboard(prompt_log)

        if result["success"]:
            self.console.print("prompt log has been copied to the clipboard", style="bold green")

        self.console.print(f"prompt log has been written to {prompt_log}", style="bold green")

    async def get_closing_message(self) -> str:
        return await get_user_input("Enter a message to be written at the end of the prompt.log file", multiline=True)

    def should_ignore(self, file_path: Path) -> bool:
        return should_ignore_file(file_path, self.project_root, self.ignore_patterns, ALLOWED_FILES)

    def process_multiple_folders(self, folders: List[Path], log_file) -> None:
        for folder in folders:
            if not path_exists(folder) or not is_path_directory(folder):
                self.console.print(f"Folder {folder} does not exist or is not a directory. Skipping.", style="bold yellow")
                continue
            self.process_folder(folder, log_file)
            write_log_file(log_file, "\n")

    def process_folder(self, folder_path: Path, log_file) -> None:
        for file_path in get_files_match_pattern(folder_path, "*"):
            if file_path.is_file() and not self.should_ignore(file_path):
                self.write_file_content(file_path, log_file)

    def write_file_content(self, file_path: Path, log_file) -> None:
        if not is_text_file_mimetype_or_allowed_file(file_path, ALLOWED_FILES):
            return

        content: str | None = read_file_content(file_path)

        if content is None:
            return

        write_log_file(log_file, create_dashed_filename_marker(file_path, self.project_root))
        write_log_file(log_file, content)
        write_log_file(log_file, create_dashed_filename_end_marker(file_path, self.project_root))
        write_log_file(log_file, "\n\n")

    def process_file(self, file_path: Path, log_file) -> None:
        if file_path in self.processed_files or self.should_ignore(file_path):
            return

        self.processed_files.add(file_path)

        self.write_file_content(file_path, log_file)

        if self.get_mode() == "traverse":
            local_imports, _, alias_mapping = self.get_local_imports(file_path)
            self.processed_alias_mapping.update(alias_mapping)
            for import_path, _ in local_imports.items():
                self.process_file(import_path, log_file)

    def process_file_used_code_only(self, file_path: Path, log_file) -> None:
        if file_path in self.processed_files or self.should_ignore(file_path):
            return

        self.processed_files.add(file_path)

        content: str = read_file_content(file_path)

        write_log_file(log_file, create_dashed_filename_marker(file_path, self.project_root))
        write_log_file(log_file, content)
        write_log_file(log_file, create_dashed_filename_end_marker(file_path, self.project_root))
        write_log_file(log_file, "\n\n")

        imports, programatically_imports, alias_mapping = self.get_local_imports(file_path)
        self.processed_alias_mapping.update(alias_mapping)
        for import_path, imported_names in imports.items():
            self.process_import_file(import_path, imported_names, file_path, log_file, programatically_imports, alias_mapping)

    def process_import_file(
        self,
        import_path: Path,
        imported_names: Set[str],
        importing_file: Path,
        log_file,
        programatically_imports: Dict[Path, Set[str]],
        alias_mapping: Dict[str, str],
    ) -> None:
        if self.should_ignore(import_path):
            return

        content: str = read_file_content(import_path)

        if content is None:
            return

        tree = ast.parse(content, type_comments=True)

        _, used_nodes = get_unused_code_nodes(content, imported_names, import_path, programatically_imports, alias_mapping, tree=tree)

        new_nodes = []
        for node in used_nodes:
            if isinstance(
                node,
                (
                    ast.ClassDef,
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                    ast.Assign,
                    ast.AnnAssign,
                    ast.Import,
                    ast.ImportFrom,
                ),
            ):
                node_representation: str = ast.dump(node)
                if node_representation not in self.processed_content.get(import_path, set()):
                    self.processed_content.setdefault(import_path, set()).add(node_representation)
                    new_nodes.append(node)
            else:
                continue

        if new_nodes:
            import_snippets: List[ast.AST] = []
            non_import_snippets: List[ast.AST] = []
            for node in new_nodes:
                source_segment: str | None = get_node_source_code_with_decorators(content, node)
                if source_segment is None:
                    source_segment = ast.unparse(node)
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    import_snippets.append(source_segment)
                else:
                    non_import_snippets.append(source_segment)

            code_parts = []
            if import_snippets:
                code_parts.append("\n".join(import_snippets))
                code_parts.append("")
            if non_import_snippets:
                code_parts.append("\n\n".join(non_import_snippets))

            code = "\n".join(code_parts)

            log_file_content: str = read_log_file(log_file)
            file_marker: str = create_dashed_filename_marker(import_path, self.project_root, blank_lines=False)
            ending_marker: str = create_dashed_filename_end_marker(import_path, self.project_root, blank_lines=False)
            updated_content: str = update_content_dashed_marker(log_file_content, file_marker, code, ending_marker)
            write_log_file_from_start(log_file, updated_content)

        if import_path not in self.processed_files:
            self.processed_files.add(import_path)
            new_imports, programatically_imports, alias_mapping = self.get_local_imports(import_path)
            self.processed_alias_mapping.update(alias_mapping)
            for new_import_path, new_imported_names in new_imports.items():
                self.process_import_file(
                    new_import_path,
                    new_imported_names,
                    import_path,
                    log_file,
                    programatically_imports,
                    alias_mapping,
                )

    def get_local_imports(self, file_path: Path) -> Tuple[Dict[Path, Set[str]], Dict[Path, Set[str]], Dict[str, str]]:
        content: str | None = read_file_content(file_path)

        if content is None:
            return {}, {}, {}

        return get_local_imports_from_content(content, file_path, self.project_root, self.ignore_patterns, ALLOWED_FILES)

    def format_prompt_log(self):
        prompt_log_path = self.project_root / self.prompt_log_name
        try:
            content: str = read_file_content(prompt_log_path)

            formatted_content: str = remove_non_printable_characters(content)
            lines: list[str] = content.split("\n")
            formatted_content: str = remove_blank_lines_from_code_lines(lines)

            with open(prompt_log_path, "w", encoding="utf-8") as file:
                file.write(formatted_content)

            if self.output_format.upper() == "XML":
                self.transform_prompt_log_to_xml(prompt_log_path)

            self.console.print("Prompt log has been formatted and unexpected characters removed.", style="bold green")

        except Exception as e:
            self.console.print(f"An error occurred while formatting the prompt log: {str(e)}", style="bold red")

    def transform_prompt_log_to_xml(self, prompt_log_path: Path) -> None:
        try:
            content: str = read_file_content(prompt_log_path)
            documents: List[Dict[str, object]] = []
            index: int = 1

            pattern: re.Pattern = re.compile(r"^--- Filename (.*?) ---\n(.*?)^--- End of Filename \1 ---", re.DOTALL | re.MULTILINE)
            matches: List[tuple[str, str]] = pattern.findall(content)

            for match in matches:
                source: str = match[0].strip()
                document_content: str = match[1].rstrip()
                documents.append({"index": index, "source": source, "content": document_content})
                index += 1

            remaining_content = pattern.sub("", content).strip()

            xml_elements: List[str] = ["<documents>"]

            for doc in documents:
                code_lines = doc["content"].splitlines()
                indented_code_lines = ["      " + line for line in code_lines]
                indented_content = "\n".join(indented_code_lines)

                xml_element: str = (
                    f'  <document index="{doc["index"]}">\n'
                    f'    <source>{doc["source"]}</source>\n'
                    f"    <document_content>\n"
                    f"{indented_content}\n"
                    f"    </document_content>\n"
                    f"  </document>"
                )
                xml_elements.append(xml_element)

            xml_elements.append("</documents>")

            xml_content: str = "\n".join(xml_elements)

            if remaining_content:
                final_content = f"{xml_content}\n\n{remaining_content}"
            else:
                final_content = xml_content

            with open(prompt_log_path, "w", encoding="utf-8") as file:
                file.write(final_content)

            self.console.print("Prompt log has been transformed into XML format.", style="bold green")

        except Exception as e:
            self.console.print(f"An error occurred while transforming the prompt log to XML: {str(e)}", style="bold red")

    async def set_project_root(self) -> None:
        if DEFAULT_PROJECT_ROOT:
            self.project_root = DEFAULT_PROJECT_ROOT
            return

        project_root_input: str = await get_user_input("Enter the project root path (leave blank for prompter project): ", default=str(self.project_root))

        if project_root_input:
            self.project_root = Path(project_root_input).resolve()
        else:
            self.project_root = Path(__file__).resolve().parents[5]

    async def get_prompt_log_path(self) -> Path | None:
        if DEFAULT_PROMPT_PATH:
            return DEFAULT_PROMPT_PATH

        output_path_input: str = await get_user_input(
            "Enter the path where to save the prompt.log file (leave blank for default): ", default=str(self.project_root / self.prompt_log_name)
        )

        return Path(output_path_input).resolve()

    async def get_output_format(self) -> str:
        if not self.output_format:
            return await get_user_input("Choose output format:", choices=["Filename", "XML"], default="Filename")

        return self.output_format.strip()

    def get_mode(self) -> str:
        return getattr(self, "_mode", "all")

    def set_mode(self, mode: str) -> None:
        self._mode = mode
