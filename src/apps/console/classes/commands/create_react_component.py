from src.apps.console.classes.commands.base import BaseCommand
from src.libs.helpers.console import get_user_input


class CreateReactComponentCommand(BaseCommand):
    name = "create react component"
    description = "Create a new React component"

    async def execute(self, *args, **kwargs):
        description = await get_user_input("Please enter a description of the component: ")
        self.console.print(f"Component description: {description}", style="bold green")

        language = await get_user_input("Do you want to use JavaScript or TypeScript?", choices=["JavaScript", "TypeScript"], default="JavaScript")
        self.console.print(f"You chose: {language}", style="bold green")

        styling = await get_user_input("Which styling option do you prefer?", choices=["CSS Modules", "Tailwind", "Material UI"], default="CSS Modules")
        self.console.print(f"You chose: {styling}", style="bold green")

        self.console.print("Component creation logic will be implemented in the next step.", style="bold green")
