from rich.panel import Panel

from src.apps.console.classes.commands.base import BaseCommand


class ExitCommand(BaseCommand):
    name = "exit"
    description = "Exit the console application"

    async def execute(self, *args, **kwargs):
        self.console.print(Panel("Thank you for using the console app. Goodbye!", title="Goodbye", style="bold green"))
        self.app.running = False
