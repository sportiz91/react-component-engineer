from pathlib import Path
from typing import Set, List, Any, Dict, Tuple


from src.apps.console.classes.commands.base import BaseCommand
from src.libs.helpers.console import get_user_input
from src.libs.utils.string import wrap_text, remove_non_printable_characters
from src.libs.utils.constants import CODE_CHANGES, ENTIRE_FILE
from src.libs.services.logger.logger import log
from src.libs.utils.file_system import (
    copy_to_clipboard,
    get_gitignore_patters_list,
    should_ignore_file,
    is_text_file_mimetype_or_allowed_file,
    read_file_content,
)
from src.libs.utils.code_analysis import (
    get_unused_code_ranges,
    get_local_imports as get_local_imports_from_content,
    remove_blank_lines_from_code_lines,
)

NAME: str = "prompt"
DESCRIPTION: str = "Construct a prompt log file from given Python files or all files in specified folders"
PROJECT_ROOT: Path = Path(__file__).resolve().parents[5]
PROCESSED_FILES: Set[Path] = set()
ALLOWED_FILES: List[str] = [".gitignore", ".env.example", "pyproject.toml", ".flake8"]
PROCESSED_CONTENT: Dict[Path, Set[int]] = {}


class PromptConstructorCommand(BaseCommand):
    name: str = NAME
    description: str = DESCRIPTION
    project_root: Path = PROJECT_ROOT
    processed_files: Set[Path] = PROCESSED_FILES
    processed_content: Dict[Path, Set[int]] = PROCESSED_CONTENT

    async def execute(self, *args: Any, **kwargs: Any) -> None:
        self.ignore_patterns: List[str] = get_gitignore_patters_list(self.project_root)

        mode: str = await get_user_input("Enter mode: ", choices=["all", "traverse"], default="all") or "all"
        self.set_mode(mode)

        entire_file_vs_code_differences: str = (
            await get_user_input(
                "Do you want to output the entire file(s) with the change(s) or only the code differences?: ", choices=["entire", "differences"], default="differences"
            )
            or "differences"
        )

        prompt_log: Path = self.project_root / "prompt.log"

        with open(prompt_log, "w+") as log_file:
            if mode == "traverse":
                filename: str = await get_user_input("Enter the filename (e.g., src/apps/console/main.py): ")
                start_file: Path = self.project_root / filename

                if not start_file.exists():
                    self.console.print(f"File {start_file} does not exist.", style="bold red")
                    return

                traverse_mode: str | None = await get_user_input("Choose traverse mode:", choices=["entire file", "used code only"], default="entire file")

                starting_message: str = await self.get_starting_message()
                closing_message: str = await self.get_closing_message()

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

        self.format_prompt_log()
        result: dict[str, str] = copy_to_clipboard(prompt_log)

        if result["success"]:
            self.console.print("prompt log has been copied to the clipboard", style="bold green")

        self.console.print(f"prompt log has been written to {prompt_log}", style="bold green")

    async def get_starting_message(self) -> str:
        return await get_user_input("Enter a message to be written at the beginning of the prompt.log file", multiline=True)

    async def get_closing_message(self) -> str:
        return await get_user_input("Enter a message to be written at the end of the prompt.log file", multiline=True)

    def should_ignore(self, file_path: Path) -> bool:
        return should_ignore_file(file_path, self.project_root, self.ignore_patterns, ALLOWED_FILES)

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
        if not is_text_file_mimetype_or_allowed_file(file_path, ALLOWED_FILES):
            return

        content: str | None = read_file_content(file_path)

        if content is None:
            return

        log_file.write(f"--- Filename {file_path.relative_to(self.project_root)} ---\n\n")
        log_file.write(content)
        log_file.write("\n\n")

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
            self.processed_content[import_path] = set()

        if self.should_ignore(import_path):
            log(f"Ignoring file: {import_path}")
            return

        with open(import_path, "r", encoding="utf-8") as source_file:
            content = source_file.read()

        unused_ranges = self.get_unused_code(content, imported_names, import_path, programatically_imports)
        log(f"Unused ranges: {unused_ranges}")

        lines: list[str] = content.splitlines(keepends=True)
        log(f"The lines: {lines}")

        lines_to_remove: set = set()
        for start, end in unused_ranges:
            lines_to_remove.update(range(start - 1, end))  # Convert to 0-indexed

        new_lines = []
        new_content = False
        blank_line_count = 0

        for i, line in enumerate(lines):
            if i not in lines_to_remove:
                is_blank_line: bool = line.strip() == ""
                if is_blank_line:
                    if blank_line_count < 2:
                        new_lines.append(line)
                        blank_line_count += 1
                else:
                    new_lines.append(line)
                    blank_line_count = 0

                line_hash = hash(line)
                if line_hash not in self.processed_content[import_path] and not is_blank_line:
                    self.processed_content[import_path].add(line_hash)
                    new_content = True

        final_content = "".join(new_lines)

        if new_content:
            log_file.seek(0)
            content = log_file.read()
            file_marker: str = f"--- Filename {import_path.relative_to(self.project_root)} ---"

            if file_marker in content:
                # Find the position of the next file marker or the end of the file
                start_pos = content.index(file_marker)
                next_marker_pos = content.find("--- Filename", start_pos + len(file_marker))
                if next_marker_pos == -1:
                    next_marker_pos = len(content)

                # Insert the new content just before the next file marker or at the end of the file
                updated_content = content[:next_marker_pos].rstrip() + "\n\n" + final_content + "\n\n" + content[next_marker_pos:]
            else:
                # If the file marker doesn't exist, add it at the end of the file
                updated_content = content.rstrip() + f"\n\n{file_marker}\n\n{final_content}\n\n"

            log_file.seek(0)
            log_file.truncate()
            log_file.write(updated_content)

        if import_path not in self.processed_files:
            self.processed_files.add(import_path)
            new_imports, programatically_imports = self.get_local_imports(import_path)
            for new_import_path, new_imported_names in new_imports.items():
                self.process_import_file(new_import_path, new_imported_names, import_path, log_file, programatically_imports)

        log(f"Added {len(new_lines)} lines from {import_path}")
        log(f"Finished processing {import_path}")

    def get_unused_code(self, content: str, imported_names: Set[str], file_path: Path, programatically_imports: Dict[Path, Set[str]]) -> List[Tuple[int, int]]:
        return get_unused_code_ranges(content, imported_names, file_path, programatically_imports)

    def get_local_imports(self, file_path: Path) -> Tuple[Dict[Path, Set[str]], Dict[Path, Set[str]]]:
        content: str | None = read_file_content(file_path)

        if content is None:
            return {}, {}

        return get_local_imports_from_content(content, self.project_root, self.ignore_patterns, ALLOWED_FILES)

    def format_prompt_log(self):
        prompt_log_path = self.project_root / "prompt.log"
        try:
            with open(prompt_log_path, "r", encoding="utf-8", errors="ignore") as file:
                content = file.read()

            content = remove_non_printable_characters(content)
            lines = content.split("\n")
            formatted_content = remove_blank_lines_from_code_lines(lines)

            with open(prompt_log_path, "w", encoding="utf-8") as file:
                file.write(formatted_content)

            self.console.print("Prompt log has been formatted and unexpected characters removed.", style="bold green")
        except Exception as e:
            self.console.print(f"An error occurred while formatting the prompt log: {str(e)}", style="bold red")

    def get_mode(self) -> str:
        return getattr(self, "_mode", "all")

    def set_mode(self, mode: str) -> None:
        self._mode = mode
