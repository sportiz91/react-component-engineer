from typing import List, Optional

from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.keys import Keys
from rich.console import Console

style: Style = Style.from_dict(
    {
        "prompt": "cyan bold",
    }
)
session: PromptSession[str] = PromptSession(style=style)
console: Console = Console()

kb = KeyBindings()


@kb.add("c-m")
def _(event):
    if event.app.current_buffer.multiline:
        event.app.exit(result=event.app.current_buffer.text)
    else:
        event.current_buffer.insert_text("\n")


@kb.add(Keys.Enter)
def _(event):
    if event.app.current_buffer.multiline():
        event.current_buffer.insert_text("\n")
    else:
        event.app.exit(result=event.app.current_buffer.text)


async def get_user_input(prompt: str, choices: Optional[List[str]] = None, default: Optional[str] = None, multiline: bool = False) -> str:
    global session

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
        if not multiline:
            return await session.prompt_async(prompt, multiline=multiline)

        message = HTML(f"<prompt>{f"{prompt} (ESC + ENTER to submit): "}</prompt>\n")
        return await session.prompt_async(message, multiline=multiline, key_bindings=kb, wrap_lines=True)
