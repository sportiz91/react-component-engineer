import os
from pathlib import Path
import re
from typing import Any, Coroutine

from rich.panel import Panel
from rich.progress import Progress

from src.apps.console.classes.commands.base import BaseCommand
from src.libs.helpers.console import get_user_input
from src.libs.utils.constants import CLAUDE_CONTEXT_WINDOW

NAME: str = "context"
DESCRIPTION: str = "Calculate the token ratio of a file or folder against Claude 3.5 Sonnet's context window"
AVOID_FILES: str = [".pyc", ".pyo", ".so", ".o", ".a", ".lib", ".dll", ".exe"]


class ContextCommand(BaseCommand):
    name: str = NAME
    description: str = DESCRIPTION

    async def execute(self, *args: Any, **kwargs: Any) -> Coroutine[Any, Any, None]:
        path_input: str = await get_user_input("Enter the path to a file or folder (e.g., src/apps/console/main.py): ")
        path: Path = Path(path_input)

        if not path.exists():
            self.console.print(Panel(f"The path '{path}' does not exist.", title="Error", style="bold red"))
            return

        if path.is_file():
            token_count = self.count_tokens_in_file(path)
            self.print_result(token_count, "file")
        elif path.is_dir():
            token_count, file_count, skipped_count = self.count_tokens_in_folder(path)
            self.print_result(token_count, "folder", file_count, skipped_count)
        else:
            self.console.print(Panel(f"The path '{path}' is neither a file nor a folder.", title="Error", style="bold red"))

    def count_tokens_in_file(self, file_path: Path) -> int:
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
            return self.estimate_tokens(content)
        except UnicodeDecodeError:
            self.console.print(f"Skipping file {file_path}: Unable to decode as UTF-8", style="yellow")
            return 0

    def count_tokens_in_folder(self, folder_path: Path) -> tuple[int, int, int]:
        total_tokens = 0
        file_count = 0
        skipped_count = 0
        with Progress() as progress:
            task = progress.add_task("[cyan]Processing files...", total=None)
            for root, _, files in os.walk(folder_path):
                for file in files:
                    file_path = Path(root) / file
                    if self.should_process_file(file_path):
                        tokens = self.count_tokens_in_file(file_path)
                        if tokens > 0:
                            total_tokens += tokens
                            file_count += 1
                        else:
                            skipped_count += 1
                    else:
                        skipped_count += 1
                    progress.update(task, advance=1)
        return total_tokens, file_count, skipped_count

    def should_process_file(self, file_path: Path) -> bool:
        if file_path.name.startswith("."):
            return False
        if file_path.suffix.lower() in AVOID_FILES:
            return False
        return True

    def estimate_tokens(self, text: str) -> int:
        tokens = re.findall(r"\w+|[^\w\s]", text)
        whitespace_count = len(re.findall(r"\s+", text))
        return len(tokens) + whitespace_count

    def print_result(self, token_count: int, path_type: str, file_count: int = 1, skipped_count: int = 0) -> None:
        ratio = token_count / CLAUDE_CONTEXT_WINDOW * 100
        result = f"Total tokens in {path_type}: {token_count:,}\n"
        result += f"Ratio to Claude 3.5 Sonnet context window: {ratio:.2f}%\n"
        if path_type == "folder":
            result += f"Files processed: {file_count:,}\n"
            result += f"Files skipped: {skipped_count:,}"
        self.console.print(Panel(result, title="Token Analysis Result", style="bold green"))
