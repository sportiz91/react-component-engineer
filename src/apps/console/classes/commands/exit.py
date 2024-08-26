from typing import Any, Coroutine
from rich.panel import Panel

from src.apps.console.classes.commands.base import BaseCommand


class ExitCommand(BaseCommand):
    name: str = "exit"
    description: str = "Exit the console application"

    async def execute(self, *args: Any, **kwargs: Any) -> Coroutine[Any, Any, None]:
        self.console.print(Panel("Thank you for using the console app. Goodbye!", title="Goodbye", style="bold green"))
        self.app.running = False
