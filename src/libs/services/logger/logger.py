from pathlib import Path
from typing import Any
import json


def log(message: Any) -> None:
    if isinstance(message, str):
        formatted_message = message
    elif hasattr(message, "__dict__"):
        formatted_message = json.dumps(message.__dict__, default=str, indent=2)
    elif hasattr(message, "__str__"):
        formatted_message = str(message)
    else:
        formatted_message = repr(message)

    print(formatted_message)

    with open(Path(__file__).resolve().parents[4] / "raw.log", "a") as log_file:
        log_file.write(formatted_message + "\n")
