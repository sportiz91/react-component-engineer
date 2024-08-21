from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style

style = Style.from_dict(
    {
        "prompt": "cyan bold",
    }
)
session = PromptSession(style=style)


async def get_user_input(prompt: str = "You: ") -> str:
    return await session.prompt_async(prompt, multiline=False)
