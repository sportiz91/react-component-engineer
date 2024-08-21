import asyncio
import sys
from pathlib import Path


project_root = Path(__file__).resolve().parents[3]
src_path = project_root / "src"

sys.path.append(str(project_root))
sys.path.append(str(src_path))

# flake8: noqa: E402
from src.apps.console.classes.console_app import ConsoleApp


async def main():
    app = ConsoleApp()
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
