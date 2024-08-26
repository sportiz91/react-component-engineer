from abc import ABC, abstractmethod
from typing import Any, Coroutine

from rich.console import Console


class BaseCommand(ABC):
    def __init__(self, app: Any) -> None:
        self.app: Any = app
        self.console: Console = app.console

    @abstractmethod
    async def execute(self, *args: Any, **kwargs: Any) -> Coroutine[Any, Any, None]:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass
