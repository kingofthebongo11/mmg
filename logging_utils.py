"""Простой модуль вспомогательного логирования."""
from __future__ import annotations

import logging
from typing import Final

_DEFAULT_LEVEL: Final[int] = logging.INFO


def get_logger(name: str) -> logging.Logger:
    """Возвращает настроенный логгер с базовой конфигурацией."""
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=_DEFAULT_LEVEL,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )
    logger = logging.getLogger(name)
    logger.setLevel(_DEFAULT_LEVEL)
    return logger
