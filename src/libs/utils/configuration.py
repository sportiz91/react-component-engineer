from typing import Dict, Optional
import os
from dotenv import load_dotenv

load_dotenv()


def get_config() -> Dict[str, Optional[str]]:
    return {
        "ENVIRONMENT": os.getenv("ENVIRONMENT"),
        "LOGGING_LEVEL": os.getenv("LOGGING_LEVEL"),
    }


def get_config_value(key: str, default: Optional[str] = None) -> Optional[str]:
    return get_config().get(key, default)
