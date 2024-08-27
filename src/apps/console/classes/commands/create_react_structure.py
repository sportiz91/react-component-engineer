from pathlib import Path
from typing import Any


from src.apps.console.classes.commands.base import BaseCommand
from src.libs.utils.types import LanguageOption, StylingOption
from src.libs.helpers.console import get_user_input
from src.libs.helpers.react import create_react_app_structure, run_typescript_checks

DESCRIPTION: str = """Create a new React project structure
with ESLint, Prettier, and TypeScript (optional). Style options include 
CSS Modules, Tailwind, and Material UI."""

NAME: str = "create react structure"

PATH: Path = Path(__file__).resolve().parents[4] / "apps" / "ui"


class CreateReactStructureCommand(BaseCommand):
    name: str = NAME
    description: str = DESCRIPTION
    path: Path = PATH

    async def execute(self, *args: Any, **kwargs: Any) -> None:
        language: LanguageOption = await get_user_input("Do you want to use JavaScript or TypeScript?", choices=["JavaScript", "TypeScript"], default="JavaScript")
        self.console.print(f"You chose: {language}", style="bold green")

        styling: StylingOption = await get_user_input("Which styling option do you prefer?", choices=["CSS Modules", "Tailwind", "Material UI"], default="CSS Modules")
        self.console.print(f"You chose: {styling}", style="bold green")

        launch_browser: str = await get_user_input("Do you want to start the app and open it in the browser after creation?", choices=["Yes", "No"], default="Yes")
        launch_browser: bool = launch_browser.lower() == "yes"

        self.console.print("Creating React app structure...", style="bold green")

        base_path: Path
        success: bool
        message: str
        base_path, success, message = create_react_app_structure(language, styling, launch_browser, self.path)

        self.console.print(f"React app structure created successfully at {base_path}", style="bold green")
        self.console.print("ESLint and Prettier have been run on the generated files.", style="bold green")

        if language == "TypeScript":
            await run_typescript_checks(str(base_path))
            self.console.print("TypeScript compilation check has been run.", style="bold green")
            self.console.print(
                "If you encounter any TypeScript errors, please try closing your editor and opening it again or running 'yarn tsc' in the project directory for more details.",
                style="bold yellow",
            )

        if launch_browser:
            if success:
                self.console.print(message, style="bold green")
                self.console.print("To stop the app, press Ctrl+C in this console.", style="bold green")
            else:
                self.console.print("The React app structure was created, but there was an issue starting the app.", style="bold yellow")
                self.console.print(message, style="bold yellow")
                self.console.print("You can try starting it manually by navigating to the app directory and running 'yarn start'.", style="bold yellow")
        else:
            self.console.print("To start the app later, navigate to the app directory and run 'yarn start'.", style="bold green")

        self.console.print("Command execution completed.", style="bold green")
