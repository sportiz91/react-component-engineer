from typing import Any, Coroutine, Dict
from rich.panel import Panel

from src.apps.console.classes.commands.base import BaseCommand


class HelpCommand(BaseCommand):
    name: str = "help"
    description: str = "Show available commands"

    async def execute(self, *args: Any, **kwargs: Any) -> Coroutine[Any, Any, None]:
        help_text: str = "\n".join([f"- {cmd.name}: {cmd.description}" for cmd in self.app.commands.values()])
        self.console.print(Panel(help_text, title="Available Commands", expand=False))

    @property
    def app_commands(self) -> Dict[str, BaseCommand]:
        return self.app.commands
