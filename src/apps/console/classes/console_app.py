import importlib
import pkgutil
from typing import Dict, Any
from types import ModuleType

from rich.console import Console
from rich.panel import Panel

from src.apps.console.classes.commands.base import BaseCommand
from src.libs.helpers.console import get_user_input


def load_commands(app: "ConsoleApp") -> Dict[str, BaseCommand]:
    commands: Dict[str, BaseCommand] = {}
    package: ModuleType = importlib.import_module("src.apps.console.classes.commands")
    for _, module_name, _ in pkgutil.iter_modules(package.__path__):
        module: ModuleType = importlib.import_module(f"src.apps.console.classes.commands.{module_name}")
        for item_name in dir(module):
            item: Any = getattr(module, item_name)
            if isinstance(item, type) and issubclass(item, BaseCommand) and item is not BaseCommand:
                command: BaseCommand = item(app)
                commands[command.name] = command
    return commands


class ConsoleApp:
    def __init__(self):
        self.console: Console = Console()
        self.running: bool = True
        self.commands: Dict[str, BaseCommand] = load_commands(self)

    async def run(self) -> None:
        self.console.print(Panel("Welcome to the Console App!", title="Welcome", style="bold green"))
        self.console.print("Type 'help' to see available commands.")

        while self.running:
            try:
                user_input: str = await get_user_input("You: ")
                command: str = user_input.lower().strip()

                if command in self.commands:
                    await self.commands[command].execute()
                elif command == "exit":
                    await self.cmd_exit()
                else:
                    self.console.print(Panel("Unknown command. Type 'help' to see available commands.", title="Error", style="bold red"))
            except KeyboardInterrupt:
                await self.commands["exit"].execute()
            except Exception as e:
                self.console.print(Panel(f"An error occurred: {str(e)}", title="Error", style="bold red"))
