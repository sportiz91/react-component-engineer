from typing import Dict, Optional
import os
from dotenv import load_dotenv

load_dotenv()


def get_config() -> Dict[str, Optional[str]]:
    return {
        "ENVIRONMENT": os.getenv("ENVIRONMENT"),
        "LOGGING_LEVEL": os.getenv("LOGGING_LEVEL"),
        "PROJECT_ROOT_PATH": os.getenv("PROJECT_ROOT_PATH"),
        "PROMPT_ROOT_PATH": os.getenv("PROMPT_ROOT_PATH"),
        "OUTPUT_CODE_FORMAT": os.getenv("OUTPUT_CODE_FORMAT"),
    }


def get_config_value(key: str, default: Optional[str] = None) -> Optional[str]:
    return get_config().get(key, default)
