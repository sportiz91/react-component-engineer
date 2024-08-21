from rich.panel import Panel

from src.apps.console.classes.commands.base import BaseCommand


class HelpCommand(BaseCommand):
    name = "help"
    description = "Show available commands"

    async def execute(self, *args, **kwargs):
        help_text = "\n".join([f"- {cmd.name}: {cmd.description}" for cmd in self.app.commands.values()])
        self.console.print(Panel(help_text, title="Available Commands", expand=False))
