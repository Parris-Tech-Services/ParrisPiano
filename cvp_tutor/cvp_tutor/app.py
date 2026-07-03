from __future__ import annotations

import sys
from loguru import logger
from pathlib import Path

from .ui_main import run


def main() -> None:
    logs = Path("logs")
    logs.mkdir(exist_ok=True)
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    logger.add(logs / "app.log", rotation="1 MB", retention=5, enqueue=True, level="INFO")
    run()


if __name__ == "__main__":  # pragma: no cover
    main()
