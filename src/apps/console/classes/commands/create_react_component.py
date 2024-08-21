from src.apps.console.classes.commands.base import BaseCommand


class CreateReactComponentCommand(BaseCommand):
    name = "create react component"
    description = "Create a new React component"

    async def execute(self, *args, **kwargs):
        self.console.print("Hello World")
