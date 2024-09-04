from pathlib import Path
from typing import Any
import json

from src.libs.utils.configuration import get_config_value

LOGGING_LEVEL = get_config_value("LOGGING_LEVEL", "debug")
ENVIRONMENT = get_config_value("ENVIRONMENT", "development")


def log(message: Any) -> None:
    if ENVIRONMENT == "production" or LOGGING_LEVEL == "none":
        return

    if isinstance(message, str):
        formatted_message = message
    elif hasattr(message, "__dict__"):
        formatted_message = json.dumps(message.__dict__, default=str, indent=2)
    elif hasattr(message, "__str__"):
        formatted_message = str(message)
    else:
        formatted_message = repr(message)

    print(formatted_message)

    if LOGGING_LEVEL == "debug":
        with open(Path(__file__).resolve().parents[4] / "raw.log", "a") as log_file:
            log_file.write(formatted_message + "\n")


def delete_raw_log() -> None:
    with open(Path(__file__).resolve().parents[4] / "raw.log", "w") as log_file:
        log_file.write("")
