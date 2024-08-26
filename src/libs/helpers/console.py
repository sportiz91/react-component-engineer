from typing import List, Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from rich.console import Console

style: Style = Style.from_dict(
    {
        "prompt": "cyan bold",
    }
)
session: PromptSession[str] = PromptSession(style=style)
console: Console = Console()


async def get_user_input(prompt: str, choices: Optional[List[str]] = None, default: Optional[str] = None, multiline: bool = False) -> str:
    if choices:
        while True:
            console.print(prompt)
            for i, choice in enumerate(choices, 1):
                console.print(f"{i}. {choice}")

            if default:
                default_index: int = choices.index(default) + 1
                user_input: str = await session.prompt_async(f"Enter your choice (1-{len(choices)}) [default: {default_index}]: ", multiline=False)
                if not user_input and default:
                    return default
            else:
                user_input: str = await session.prompt_async(f"Enter your choice (1-{len(choices)}): ", multiline=False)

            try:
                choice_index: int = int(user_input) - 1
                if 0 <= choice_index < len(choices):
                    return choices[choice_index]
                else:
                    console.print("Invalid choice. Please try again.", style="bold red")
            except ValueError:
                console.print("Invalid input. Please enter a number.", style="bold red")
    else:
        return await session.prompt_async(prompt, multiline=multiline)
