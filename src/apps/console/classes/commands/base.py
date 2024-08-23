from abc import ABC, abstractmethod

from rich.console import Console


class BaseCommand(ABC):
    def __init__(self, app):
        self.app = app
        self.console: Console = app.console

    @abstractmethod
    async def execute(self, *args, **kwargs):
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass
